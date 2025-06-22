"""
功能开关服务
实现动态功能控制、灰度发布和权限管理
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Count
from django.core.cache import cache

from authentication.models import User
from .models import (
    AIFunction, StudentFunctionPermission, GroupFunctionPermission,
    StudentGroup, StudentGroupMembership, FunctionToggleLog,
    GrayReleaseConfig, PermissionAuditLog
)

logger = logging.getLogger(__name__)


class FunctionToggleService:
    """功能开关服务"""
    
    @staticmethod
    def check_user_function_permission(user: User, function_code: str) -> Tuple[bool, str]:
        """
        检查用户是否有特定功能的权限
        
        Args:
            user: 用户对象
            function_code: 功能代码
            
        Returns:
            Tuple[is_allowed, message]: (是否允许, 消息)
        """
        try:
            # 管理员和教师默认有所有权限
            if user.user_type in ['admin', 'teacher']:
                return True, "管理员/教师权限"
            
            # 获取功能
            try:
                function = AIFunction.objects.get(function_code=function_code, is_active=True)
            except AIFunction.DoesNotExist:
                return False, "功能不存在或已禁用"
            
            # 检查灰度发布
            if function.is_beta:
                gray_allowed = FunctionToggleService._check_gray_release_permission(user, function)
                if gray_allowed:
                    return True, "灰度发布权限允许"
                else:
                    return False, "功能正在灰度发布中，您暂无权限访问"
            
            # 检查个人权限
            try:
                permission = StudentFunctionPermission.objects.get(
                    student=user,
                    function=function
                )
                
                if not permission.is_enabled:
                    return False, "功能已被禁用"
                
                # 检查过期时间
                if permission.expires_at and permission.expires_at < timezone.now():
                    return False, "功能权限已过期"
                
                # 检查每日配额
                if permission.daily_quota > 0:
                    today_usage = FunctionToggleService._get_daily_usage(user, function)
                    if today_usage >= permission.daily_quota:
                        return False, f"今日配额已用尽 ({today_usage}/{permission.daily_quota})"
                
                return True, "个人权限允许"
                
            except StudentFunctionPermission.DoesNotExist:
                pass
            
            # 检查群组权限
            user_groups = StudentGroupMembership.objects.filter(
                student=user
            ).select_related('group')
            
            for membership in user_groups:
                try:
                    group_permission = GroupFunctionPermission.objects.get(
                        group=membership.group,
                        function=function,
                        is_enabled=True
                    )
                    
                    # 检查过期时间
                    if group_permission.expires_at and group_permission.expires_at < timezone.now():
                        continue
                    
                    # 检查每日配额
                    if group_permission.daily_quota > 0:
                        today_usage = FunctionToggleService._get_daily_usage(user, function)
                        if today_usage >= group_permission.daily_quota:
                            return False, f"今日配额已用尽 ({today_usage}/{group_permission.daily_quota})"
                    
                    return True, f"群组权限允许 ({membership.group.name})"
                    
                except GroupFunctionPermission.DoesNotExist:
                    continue
            
            # 检查功能默认设置
            if function.is_active and not function.is_beta:
                # 检查默认每日配额
                if function.max_daily_usage > 0:
                    today_usage = FunctionToggleService._get_daily_usage(user, function)
                    if today_usage >= function.max_daily_usage:
                        return False, f"今日配额已用尽 ({today_usage}/{function.max_daily_usage})"
                
                return True, "功能默认开放"
            
            return False, "无权限访问该功能"
            
        except Exception as e:
            logger.error(f"检查用户功能权限失败: {e}")
            return False, "系统错误，请稍后重试"
    
    @staticmethod
    def _check_gray_release_permission(user: User, function: AIFunction) -> bool:
        """检查灰度发布权限"""
        try:
            # 获取活跃的灰度发布配置
            gray_configs = GrayReleaseConfig.objects.filter(
                function=function,
                status='active'
            ).filter(
                Q(start_time__lte=timezone.now()) | Q(start_time__isnull=True)
            )
            
            if not gray_configs.exists():
                return False
            
            for config in gray_configs:
                # 检查白名单
                if config.release_type == 'whitelist':
                    if user in config.whitelist_users.all():
                        return True
                
                # 检查群组发布
                elif config.release_type == 'group_based':
                    user_groups = StudentGroupMembership.objects.filter(
                        student=user
                    ).values_list('group_id', flat=True)
                    
                    if config.target_groups.filter(id__in=user_groups).exists():
                        return True
                
                # 检查按比例发布
                elif config.release_type == 'percentage':
                    # 使用用户ID作为随机种子，确保结果一致
                    random.seed(user.id)
                    user_percentage = random.randint(1, 100)
                    return user_percentage <= config.current_percentage
                
                # 检查逐步发布
                elif config.release_type == 'gradual':
                    # 基于注册时间逐步开放
                    days_since_registration = (timezone.now() - user.date_joined).days
                    required_days = 100 - config.current_percentage  # 简化逻辑
                    return days_since_registration >= required_days
            
            return False
            
        except Exception as e:
            logger.error(f"检查灰度发布权限失败: {e}")
            return False
    
    @staticmethod
    def _get_daily_usage(user: User, function: AIFunction) -> int:
        """获取用户今日使用次数"""
        # 这里需要与实际的使用记录系统集成
        # 暂时返回缓存的使用次数
        cache_key = f"daily_usage_{user.id}_{function.id}_{timezone.now().date()}"
        return cache.get(cache_key, 0)
    
    @staticmethod
    def record_function_usage(user: User, function_code: str):
        """记录功能使用"""
        try:
            function = AIFunction.objects.get(function_code=function_code)
            cache_key = f"daily_usage_{user.id}_{function.id}_{timezone.now().date()}"
            current_usage = cache.get(cache_key, 0)
            cache.set(cache_key, current_usage + 1, 86400)  # 24小时过期
        except Exception as e:
            logger.error(f"记录功能使用失败: {e}")
    
    @staticmethod
    @transaction.atomic
    def toggle_user_function(user_id: int, function_id: int, is_enabled: bool, 
                           operated_by: User, reason: str = "", daily_quota: int = 0,
                           expires_at: Optional[datetime] = None) -> Dict:
        """切换用户功能权限"""
        try:
            user = User.objects.get(id=user_id)
            function = AIFunction.objects.get(id=function_id)
            
            # 获取或创建权限记录
            permission, created = StudentFunctionPermission.objects.get_or_create(
                student=user,
                function=function,
                defaults={
                    'is_enabled': is_enabled,
                    'daily_quota': daily_quota,
                    'granted_by': operated_by,
                    'expires_at': expires_at
                }
            )
            
            # 记录原值
            old_value = {
                'is_enabled': permission.is_enabled,
                'daily_quota': permission.daily_quota,
                'expires_at': permission.expires_at.isoformat() if permission.expires_at else None
            } if not created else None
            
            # 更新权限
            permission.is_enabled = is_enabled
            permission.daily_quota = daily_quota
            permission.expires_at = expires_at
            permission.granted_by = operated_by
            permission.save()
            
            # 记录变更日志
            FunctionToggleLog.objects.create(
                function=function,
                operation_type='enable' if is_enabled else 'disable',
                target_type='user',
                target_user=user,
                old_value=old_value,
                new_value={
                    'is_enabled': is_enabled,
                    'daily_quota': daily_quota,
                    'expires_at': expires_at.isoformat() if expires_at else None
                },
                reason=reason,
                operated_by=operated_by
            )
            
            # 记录权限审计日志
            PermissionAuditLog.objects.create(
                audit_type='permission_grant' if is_enabled else 'permission_revoke',
                target_user=user,
                function=function,
                operation_detail={
                    'action': 'toggle_user_function',
                    'is_enabled': is_enabled,
                    'daily_quota': daily_quota,
                    'reason': reason
                },
                operated_by=operated_by
            )
            
            return {
                'success': True,
                'message': f'用户 {user.username} 的 {function.name} 功能已{"启用" if is_enabled else "禁用"}',
                'created': created
            }
            
        except (User.DoesNotExist, AIFunction.DoesNotExist) as e:
            return {'success': False, 'error': f'目标对象不存在: {e}'}
        except Exception as e:
            logger.error(f"切换用户功能权限失败: {e}")
            return {'success': False, 'error': f'操作失败: {e}'}
    
    @staticmethod
    @transaction.atomic
    def batch_toggle_function(user_ids: List[int], function_id: int, is_enabled: bool,
                            operated_by: User, reason: str = "") -> Dict:
        """批量切换用户功能权限"""
        try:
            function = AIFunction.objects.get(id=function_id)
            success_count = 0
            error_count = 0
            errors = []
            
            for user_id in user_ids:
                result = FunctionToggleService.toggle_user_function(
                    user_id, function_id, is_enabled, operated_by, reason
                )
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"用户ID {user_id}: {result['error']}")
            
            # 记录批量操作日志
            FunctionToggleLog.objects.create(
                function=function,
                operation_type='batch_operation',
                target_type='user',
                old_value=None,
                new_value={
                    'operation': 'batch_toggle',
                    'is_enabled': is_enabled,
                    'target_count': len(user_ids),
                    'success_count': success_count,
                    'error_count': error_count
                },
                reason=reason,
                operated_by=operated_by
            )
            
            return {
                'success': True,
                'message': f'批量操作完成：成功 {success_count} 个，失败 {error_count} 个',
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors
            }
            
        except AIFunction.DoesNotExist:
            return {'success': False, 'error': '功能不存在'}
        except Exception as e:
            logger.error(f"批量切换功能权限失败: {e}")
            return {'success': False, 'error': f'批量操作失败: {e}'}


class GrayReleaseService:
    """灰度发布服务"""
    
    @staticmethod
    @transaction.atomic
    def create_gray_release(function_id: int, release_name: str, release_type: str,
                          target_percentage: int, target_groups: List[int],
                          whitelist_users: List[int], created_by: User,
                          rollback_plan: str = "", success_criteria: Dict = None,
                          monitoring_metrics: Dict = None) -> Dict:
        """创建灰度发布配置"""
        try:
            function = AIFunction.objects.get(id=function_id)
            
            # 创建灰度发布配置
            config = GrayReleaseConfig.objects.create(
                function=function,
                release_name=release_name,
                release_type=release_type,
                target_percentage=target_percentage,
                current_percentage=0,
                rollback_plan=rollback_plan,
                success_criteria=success_criteria or {},
                monitoring_metrics=monitoring_metrics or {},
                created_by=created_by
            )
            
            # 设置目标群组和白名单用户
            if target_groups:
                config.target_groups.set(target_groups)
            if whitelist_users:
                config.whitelist_users.set(whitelist_users)
            
            return {
                'success': True,
                'message': f'灰度发布配置 "{release_name}" 创建成功',
                'config_id': config.id
            }
            
        except AIFunction.DoesNotExist:
            return {'success': False, 'error': '功能不存在'}
        except Exception as e:
            logger.error(f"创建灰度发布配置失败: {e}")
            return {'success': False, 'error': f'创建失败: {e}'}
    
    @staticmethod
    @transaction.atomic
    def update_gray_release_percentage(config_id: int, new_percentage: int,
                                     operated_by: User) -> Dict:
        """更新灰度发布百分比"""
        try:
            config = GrayReleaseConfig.objects.get(id=config_id)
            old_percentage = config.current_percentage
            
            config.current_percentage = new_percentage
            config.save()
            
            # 记录变更日志
            FunctionToggleLog.objects.create(
                function=config.function,
                operation_type='quota_change',
                target_type='global',
                old_value={'percentage': old_percentage},
                new_value={'percentage': new_percentage},
                reason=f'灰度发布进度调整：{old_percentage}% -> {new_percentage}%',
                operated_by=operated_by
            )
            
            return {
                'success': True,
                'message': f'灰度发布进度已更新：{old_percentage}% -> {new_percentage}%'
            }
            
        except GrayReleaseConfig.DoesNotExist:
            return {'success': False, 'error': '灰度发布配置不存在'}
        except Exception as e:
            logger.error(f"更新灰度发布百分比失败: {e}")
            return {'success': False, 'error': f'更新失败: {e}'}
    
    @staticmethod
    def get_function_coverage_stats(function_id: int) -> Dict:
        """获取功能覆盖统计"""
        try:
            function = AIFunction.objects.get(id=function_id)
            
            # 总用户数
            total_users = User.objects.filter(user_type='student', is_active=True).count()
            
            # 有权限的用户数
            permitted_users = User.objects.filter(
                Q(studentfunctionpermission__function=function, 
                  studentfunctionpermission__is_enabled=True) |
                Q(studentgroupmembership__group__groupfunctionpermission__function=function,
                  studentgroupmembership__group__groupfunctionpermission__is_enabled=True),
                user_type='student',
                is_active=True
            ).distinct().count()
            
            # 灰度发布覆盖用户数
            gray_users = 0
            gray_configs = GrayReleaseConfig.objects.filter(
                function=function, 
                status='active'
            )
            
            for config in gray_configs:
                if config.release_type == 'percentage':
                    gray_users += int(total_users * config.current_percentage / 100)
                elif config.release_type == 'whitelist':
                    gray_users += config.whitelist_users.count()
                elif config.release_type == 'group_based':
                    gray_users += User.objects.filter(
                        studentgroupmembership__group__in=config.target_groups.all(),
                        user_type='student',
                        is_active=True
                    ).distinct().count()
            
            coverage_percentage = (permitted_users / total_users * 100) if total_users > 0 else 0
            gray_percentage = (gray_users / total_users * 100) if total_users > 0 else 0
            
            return {
                'total_users': total_users,
                'permitted_users': permitted_users,
                'gray_users': gray_users,
                'coverage_percentage': round(coverage_percentage, 2),
                'gray_percentage': round(gray_percentage, 2)
            }
            
        except Exception as e:
            logger.error(f"获取功能覆盖统计失败: {e}")
            return {
                'total_users': 0,
                'permitted_users': 0,
                'gray_users': 0,
                'coverage_percentage': 0,
                'gray_percentage': 0
            } 