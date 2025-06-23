"""
管理员后台视图
实现用户管理、权限管理和系统监控
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
import json

from .decorators import admin_required, teacher_or_admin_required
from .models import User, StudentProfile, LoginLog
from permissions.models import AIFunction, StudentFunctionPermission, StudentGroup, PermissionAuditLog
from behavior_tracking.models import ChatSession, ChatMessage


@admin_required
def admin_dashboard(request):
    """管理员仪表板"""
    # 统计数据
    stats = {
        'total_users': User.objects.count(),
        'total_students': User.objects.filter(user_type='student').count(),
        'total_teachers': User.objects.filter(user_type='teacher').count(),
        'total_admins': User.objects.filter(user_type='admin').count(),
        'active_users_today': User.objects.filter(
            last_login__date=timezone.now().date()
        ).count(),
        'total_sessions': ChatSession.objects.count(),
        'total_messages': ChatMessage.objects.count(),
        'total_functions': AIFunction.objects.count(),
        'active_functions': AIFunction.objects.filter(is_active=True).count(),
    }
    
    # 近7天登录统计
    seven_days_ago = timezone.now() - timedelta(days=7)
    daily_logins = []
    for i in range(7):
        date = (timezone.now() - timedelta(days=i)).date()
        count = LoginLog.objects.filter(
            login_time__date=date,
            login_status='success'
        ).count()
        daily_logins.append({
            'date': date.strftime('%m-%d'),
            'count': count
        })
    daily_logins.reverse()
    
    # 最近的权限操作
    recent_audits = PermissionAuditLog.objects.select_related(
        'operated_by', 'target_user', 'function'
    ).order_by('-operated_at')[:10]
    
    # 最近登录失败记录
    failed_logins = LoginLog.objects.filter(
        login_status='failed',
        login_time__gte=seven_days_ago
    ).select_related('user').order_by('-login_time')[:10]
    
    context = {
        'stats': stats,
        'daily_logins': daily_logins,
        'recent_audits': recent_audits,
        'failed_logins': failed_logins,
        'page_title': '管理员仪表板'
    }
    
    return render(request, 'authentication/admin_dashboard.html', context)


@teacher_or_admin_required
def user_management(request):
    """用户管理"""
    # 搜索和筛选
    search_query = request.GET.get('search', '')
    user_type_filter = request.GET.get('user_type', '')
    is_active_filter = request.GET.get('is_active', '')
    
    users = User.objects.all()
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if user_type_filter:
        users = users.filter(user_type=user_type_filter)
    
    if is_active_filter:
        users = users.filter(is_active=is_active_filter == 'true')
    
    users = users.order_by('-date_joined')
    
    # 分页
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 统计数据
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    admin_users = User.objects.filter(user_type='admin').count()
    student_users = User.objects.filter(user_type='student').count()
    
    context = {
        'users': page_obj.object_list,
        'page_obj': page_obj,
        'search_query': search_query,
        'user_type_filter': user_type_filter,
        'is_active_filter': is_active_filter,
        'user_type_choices': User.USER_TYPE_CHOICES,
        'total_users': total_users,
        'active_users': active_users,
        'admin_users': admin_users,
        'student_users': student_users,
        'page_title': '用户管理'
    }
    
    return render(request, 'authentication/user_management.html', context)


@teacher_or_admin_required
def user_detail(request, user_id):
    """用户详情"""
    user = get_object_or_404(User, id=user_id)
    
    # 获取学生档案（如果是学生）
    student_profile = None
    if user.user_type == 'student':
        try:
            student_profile = user.studentprofile
        except StudentProfile.DoesNotExist:
            pass
    
    # 获取权限信息
    permissions = StudentFunctionPermission.objects.filter(
        student=user
    ).select_related('function', 'granted_by').order_by('-granted_at')
    
    # 获取登录历史
    login_history = LoginLog.objects.filter(
        user=user
    ).order_by('-login_time')[:20]
    
    # 获取使用统计
    total_sessions = ChatSession.objects.filter(user=user).count()
    total_messages = ChatMessage.objects.filter(session__user=user).count()
    
    # 最近30天活跃度
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_sessions = ChatSession.objects.filter(
        user=user,
        started_at__gte=thirty_days_ago
    ).count()
    
    context = {
        'user_obj': user,  # 避免与request.user冲突
        'student_profile': student_profile,
        'permissions': permissions,
        'login_history': login_history,
        'stats': {
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'recent_sessions': recent_sessions,
        },
        'page_title': f'用户详情 - {user.username}'
    }
    
    return render(request, 'authentication/user_detail.html', context)


@admin_required
@require_http_methods(["POST"])
def toggle_user_status(request, user_id=None):
    """切换用户状态（启用/禁用）"""
    try:
        # 支持两种方式：URL参数或请求体中的user_id
        if user_id is None:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            is_active = data.get('is_active')
        else:
            # 从URL参数获取user_id，从请求体获取is_active
            if request.body:
                try:
                    data = json.loads(request.body)
                    is_active = data.get('is_active')
                except json.JSONDecodeError:
                    return JsonResponse({
                        'success': False,
                        'error': '无效的JSON数据'
                    }, status=400)
            else:
                return JsonResponse({
                    'success': False,
                    'error': '缺少请求数据'
                }, status=400)
        
        if is_active is None:
            return JsonResponse({
                'success': False,
                'error': '缺少is_active参数'
            }, status=400)
        
        user = get_object_or_404(User, id=user_id)
        
        # 不能禁用自己
        if user == request.user:
            return JsonResponse({
                'success': False,
                'error': '不能禁用自己的账户'
            })
        
        user.is_active = is_active
        user.save()
        
        # 记录操作日志
        PermissionAuditLog.objects.create(
            audit_type='permission_grant',
            target_user=user,
            operation_detail={
                'action': 'toggle_user_status',
                'is_active': is_active,
                'user_id': user_id
            },
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            operated_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': f'用户已{"启用" if is_active else "禁用"}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@admin_required
@require_http_methods(["POST"])
def reset_user_password(request, user_id=None):
    """重置用户密码"""
    try:
        # 支持两种方式：URL参数或请求体中的user_id
        if user_id is None:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            new_password = data.get('new_password')
        else:
            # 从URL参数获取user_id，从请求体获取new_password
            if request.body:
                try:
                    data = json.loads(request.body)
                    new_password = data.get('new_password', 'password123')  # 默认密码
                except json.JSONDecodeError:
                    return JsonResponse({
                        'success': False,
                        'error': '无效的JSON数据'
                    }, status=400)
            else:
                new_password = 'password123'  # 默认密码
        
        user = get_object_or_404(User, id=user_id)
        user.set_password(new_password)
        user.save()
        
        # 记录操作日志
        PermissionAuditLog.objects.create(
            audit_type='permission_grant',
            target_user=user,
            operation_detail={
                'action': 'reset_password',
                'user_id': user_id
            },
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            operated_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': '密码重置成功',
            'new_password': new_password
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@teacher_or_admin_required
def login_logs(request):
    """登录日志"""
    # 筛选条件
    username_filter = request.GET.get('username', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    logs = LoginLog.objects.select_related('user').all()
    
    if username_filter:
        logs = logs.filter(user__username__icontains=username_filter)
    
    if status_filter:
        logs = logs.filter(login_status=status_filter)
    
    if date_from:
        logs = logs.filter(login_time__date__gte=date_from)
    
    if date_to:
        logs = logs.filter(login_time__date__lte=date_to)
    
    logs = logs.order_by('-login_time')
    
    # 分页
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 统计数据
    total_logins = LoginLog.objects.count()
    successful_logins = LoginLog.objects.filter(login_status='success').count()
    failed_logins = LoginLog.objects.filter(login_status='failed').count()
    today_logins = LoginLog.objects.filter(
        login_time__date=timezone.now().date()
    ).count()
    
    context = {
        'logs': page_obj.object_list,
        'page_obj': page_obj,
        'username_filter': username_filter,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_logins': total_logins,
        'successful_logins': successful_logins,
        'failed_logins': failed_logins,
        'today_logins': today_logins,
        'page_title': '登录日志'
    }
    failed_logins = LoginLog.objects.filter(login_status='failed').count()
    today_logins = LoginLog.objects.filter(
        login_time__date=timezone.now().date()
    ).count()
    
    context = {
        'logs': page_obj.object_list,
        'page_obj': page_obj,
        'username_filter': username_filter,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_logins': total_logins,
        'successful_logins': successful_logins,
        'failed_logins': failed_logins,
        'today_logins': today_logins,
        'page_title': '登录日志'
    }
    
    return render(request, 'authentication/login_logs.html', context)


@teacher_or_admin_required
def permission_audit_logs(request):
    """权限审计日志"""
    # 筛选条件
    audit_type_filter = request.GET.get('audit_type', '')
    operator_filter = request.GET.get('operator', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    logs = PermissionAuditLog.objects.select_related(
        'operated_by', 'target_user', 'function'
    ).all()
    
    if audit_type_filter:
        logs = logs.filter(audit_type=audit_type_filter)
    
    if operator_filter:
        logs = logs.filter(operated_by__username__icontains=operator_filter)
    
    if date_from:
        logs = logs.filter(operated_at__date__gte=date_from)
    
    if date_to:
        logs = logs.filter(operated_at__date__lte=date_to)
    
    logs = logs.order_by('-operated_at')
    
    # 分页
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'audit_type_filter': audit_type_filter,
        'operator_filter': operator_filter,
        'date_from': date_from,
        'date_to': date_to,
        'audit_type_choices': PermissionAuditLog.AUDIT_TYPE_CHOICES,
        'page_title': '权限审计日志'
    }
    
    return render(request, 'authentication/permission_audit_logs.html', context)


@admin_required
def system_settings(request):
    """系统设置"""
    if request.method == 'POST':
        # 处理系统设置更新
        try:
            # 这里可以添加系统配置的保存逻辑
            messages.success(request, '系统设置已更新')
            return redirect('authentication:system_settings')
        except Exception as e:
            messages.error(request, f'更新失败: {str(e)}')
    
    context = {
        'page_title': '系统设置'
    }
    
    return render(request, 'authentication/system_settings.html', context) 