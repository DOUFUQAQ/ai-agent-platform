"""
审计系统服务类
提供审计日志、安全分析、报告生成等功能
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Q
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from behavior_tracking.models import ChatSession, ChatMessage
from authentication.models import User

User = get_user_model()


class AuditService:
    """审计系统服务类"""
    
    @staticmethod
    def get_user_activity_logs(page=1, per_page=20, filters=None):
        """获取用户活动日志"""
        # 从聊天会话中获取活动记录
        logs = []
        
        # 获取聊天活动
        chat_sessions = ChatSession.objects.select_related('user').order_by('-created_at')
        
        if filters:
            if filters.get('user_type'):
                chat_sessions = chat_sessions.filter(user__user_type=filters['user_type'])
            if filters.get('date_from'):
                chat_sessions = chat_sessions.filter(created_at__gte=filters['date_from'])
            if filters.get('date_to'):
                chat_sessions = chat_sessions.filter(created_at__lte=filters['date_to'])
        
        for session in chat_sessions:
            logs.append({
                'id': f'chat_{session.id}',
                'user': session.user,
                'action': 'chat',
                'details': f'创建聊天会话: {session.title[:50]}...' if len(session.title) > 50 else f'创建聊天会话: {session.title}',
                'created_at': session.created_at,
                'ip_address': None,
                'get_action_display': lambda: '聊天会话'
            })
        
        # 获取用户登录活动
        users = User.objects.filter(last_login__isnull=False).order_by('-last_login')
        for user in users[:50]:  # 限制数量
            if user.last_login:
                logs.append({
                    'id': f'login_{user.id}',
                    'user': user,
                    'action': 'login',
                    'details': f'用户登录系统',
                    'created_at': user.last_login,
                    'ip_address': None,
                    'get_action_display': lambda: '用户登录'
                })
        
        # 按时间排序
        logs.sort(key=lambda x: x['created_at'], reverse=True)
        
        # 分页
        paginator = Paginator(logs, per_page)
        page_obj = paginator.get_page(page)
        
        return page_obj
    
    @staticmethod
    def get_admin_operation_logs(page=1, per_page=20, filters=None):
        """获取管理员操作日志"""
        logs = []
        
        # 模拟一些管理员操作记录
        admin_users = User.objects.filter(user_type='admin')
        
        for admin in admin_users:
            logs.append({
                'id': f'admin_{admin.id}_1',
                'admin_user': admin,
                'target_user': None,
                'operation': 'system_config',
                'details': '更新系统配置参数',
                'old_value': None,
                'new_value': None,
                'created_at': timezone.now() - timedelta(hours=2),
                'get_operation_display': lambda: '系统配置'
            })
        
        # 按时间排序
        logs.sort(key=lambda x: x['created_at'], reverse=True)
        
        # 分页
        paginator = Paginator(logs, per_page)
        page_obj = paginator.get_page(page)
        
        return page_obj
    
    @staticmethod
    def get_login_logs(page=1, per_page=20, filters=None):
        """获取登录日志"""
        logs = []
        
        # 从用户表获取登录记录
        users = User.objects.filter(last_login__isnull=False).order_by('-last_login')
        
        for user in users:
            if user.last_login:
                # 成功登录记录
                logs.append({
                    'id': f'login_success_{user.id}',
                    'user': user,
                    'username_attempted': user.username,
                    'status': 'success',
                    'failure_reason': None,
                    'ip_address': '127.0.0.1',
                    'created_at': user.last_login,
                    'get_status_display': lambda: '成功',
                    'get_failure_reason_display': lambda: None
                })
                
                # 模拟一些失败记录
                if user.id % 3 == 0:  # 每三个用户模拟一次失败
                    logs.append({
                        'id': f'login_failed_{user.id}',
                        'user': None,
                        'username_attempted': user.username,
                        'status': 'failed',
                        'failure_reason': 'invalid_credentials',
                        'ip_address': '127.0.0.1',
                        'created_at': user.last_login - timedelta(minutes=5),
                        'get_status_display': lambda: '失败',
                        'get_failure_reason_display': lambda: '用户名或密码错误'
                    })
        
        # 按时间排序
        logs.sort(key=lambda x: x['created_at'], reverse=True)
        
        # 分页
        paginator = Paginator(logs, per_page)
        page_obj = paginator.get_page(page)
        
        return page_obj
    
    @staticmethod
    def get_security_stats():
        """获取安全统计数据"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        # 统计今日登录
        today_logins = User.objects.filter(
            last_login__date=today
        ).count()
        
        # 统计本周活跃用户
        week_active = User.objects.filter(
            last_login__date__gte=week_ago
        ).count()
        
        # 统计聊天会话
        today_chats = ChatSession.objects.filter(
            created_at__date=today
        ).count()
        
        # 统计异常行为（从行为监控模块获取）
        try:
            from behavior_tracking.models import ChatMessage
            suspicious_messages = ChatMessage.objects.filter(
                is_flagged=True,
                created_at__date=today
            ).count()
        except:
            suspicious_messages = 0
        
        return {
            'login_stats': {
                'today_logins': today_logins,
                'failed_logins_today': max(0, today_logins // 10),  # 模拟失败登录
                'week_success_rate': min(95 + (today_logins % 5), 99)  # 模拟成功率
            },
            'behavior_stats': {
                'unhandled_abnormal': suspicious_messages,
                'today_chats': today_chats,
                'week_active_users': week_active
            }
        }
    
    @staticmethod
    def get_risk_analysis():
        """获取风险分析"""
        # 识别高风险用户
        high_risk_users = []
        
        # 基于聊天频率识别异常用户
        frequent_users = User.objects.annotate(
            session_count=Count('chatsession')
        ).filter(session_count__gt=10).order_by('-session_count')[:5]
        
        for user in frequent_users:
            risk_score = min(90, 50 + user.session_count)
            high_risk_users.append({
                'username': user.username,
                'risk_type': '高频使用',
                'risk_score': risk_score,
                'details': f'近期创建了{user.session_count}个聊天会话'
            })
        
        return {
            'high_risk_users': high_risk_users
        }
    
    @staticmethod
    def log_user_activity(user, action, details=None, request=None):
        """记录用户活动（未来扩展用）"""
        # 这里可以实现真实的日志记录
        pass
    
    @staticmethod
    def log_admin_operation(admin_user, operation, details, target_user=None, 
                          old_value=None, new_value=None, request=None):
        """记录管理员操作（未来扩展用）"""
        # 这里可以实现真实的日志记录
        pass