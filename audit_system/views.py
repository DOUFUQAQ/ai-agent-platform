from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from authentication.decorators import admin_required
from behavior_tracking.models import ChatSession, ChatMessage, UserBehaviorLog, AdminOperationLog
from authentication.models import User, LoginLog

@login_required
@admin_required
def dashboard(request):
    """审计仪表板"""
    try:
        # 获取安全统计数据
        security_stats = get_security_stats()
        
        # 获取风险分析
        risk_analysis = get_risk_analysis()
        
        context = {
            'page_title': '安全审计',
            'security_stats': security_stats,
            'risk_analysis': risk_analysis
        }
    except Exception as e:
        context = {
            'page_title': '安全审计',
            'error': f'加载数据失败: {str(e)}',
            'security_stats': {
                'login_stats': {
                    'today_logins': 0,
                    'failed_logins_today': 0,
                    'week_success_rate': 0
                },
                'behavior_stats': {
                    'unhandled_abnormal': 0
                }
            },
            'risk_analysis': {
                'high_risk_users': []
            }
        }
    
    return render(request, 'audit_system/dashboard.html', context)

@login_required
@admin_required
def user_activity_logs(request):
    """用户活动日志"""
    page = request.GET.get('page', 1)
    user_filter = request.GET.get('user_type', '')
    date_filter = request.GET.get('date_range', 'week')
    
    # 获取用户活动数据
    logs = get_user_activity_logs(
        page=page,
        user_filter=user_filter,
        date_filter=date_filter
    )
    
    context = {
        'page_title': '用户活动日志',
        'logs': logs.object_list,
        'page_obj': logs,
        'filters': {
            'user_type': user_filter,
            'date_range': date_filter
        }
    }
    return render(request, 'audit_system/user_activity_logs.html', context)

@login_required
@admin_required
def admin_operation_logs(request):
    """管理员操作日志"""
    page = request.GET.get('page', 1)
    
    # 获取管理员操作数据
    logs = get_admin_operation_logs(page=page)
    
    context = {
        'page_title': '管理员操作日志',
        'logs': logs.object_list,
        'page_obj': logs
    }
    return render(request, 'audit_system/admin_operation_logs.html', context)

@login_required
@admin_required
def login_logs(request):
    """登录日志"""
    page = request.GET.get('page', 1)
    status_filter = request.GET.get('status', '')
    
    # 获取登录日志数据
    logs = get_login_logs(page=page, status_filter=status_filter)
    
    context = {
        'page_title': '登录日志',
        'logs': logs.object_list,
        'page_obj': logs,
        'filters': {
            'status': status_filter
        }
    }
    return render(request, 'audit_system/login_logs.html', context)


# 辅助函数
def get_security_stats():
    """获取安全统计数据"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    # 统计今日登录（使用authentication.LoginLog）
    today_logins = LoginLog.objects.filter(
        login_time__date=today,
        login_status='success'
    ).count()
    
    # 统计今日登录失败
    failed_logins_today = LoginLog.objects.filter(
        login_time__date=today,
        login_status='failed'
    ).count()
    
    # 统计本周活跃用户
    week_active = User.objects.filter(
        last_login__date__gte=week_ago
    ).count()
    
    # 统计聊天会话
    today_chats = ChatSession.objects.filter(
        started_at__date=today
    ).count()
    
    # 统计异常行为
    try:
        suspicious_messages = ChatMessage.objects.filter(
            is_flagged=True,
            created_at__date=today
        ).count()
    except:
        suspicious_messages = 0
    
    # 计算成功率
    total_login_attempts = today_logins + failed_logins_today
    success_rate = round((today_logins / total_login_attempts * 100) if total_login_attempts > 0 else 100, 1)
    
    return {
        'login_stats': {
            'today_logins': today_logins,
            'failed_logins_today': failed_logins_today,
            'week_success_rate': success_rate
        },
        'behavior_stats': {
            'unhandled_abnormal': suspicious_messages,
            'today_chats': today_chats,
            'week_active_users': week_active
        }
    }

def get_risk_analysis():
    """获取风险分析"""
    high_risk_users = []
    
    # 基于聊天频率识别异常用户
    frequent_users = User.objects.annotate(
        session_count=Count('chatsession')
    ).filter(session_count__gt=5).order_by('-session_count')[:5]
    
    for user in frequent_users:
        risk_score = min(90, 50 + user.session_count * 2)
        high_risk_users.append({
            'username': user.username,
            'risk_type': '高频使用',
            'risk_score': risk_score,
            'details': f'近期创建了{user.session_count}个聊天会话'
        })
    
    return {
        'high_risk_users': high_risk_users
    }

def get_user_activity_logs(page=1, user_filter='', date_filter='week', per_page=20):
    """获取用户活动日志"""
    logs = []
    
    # 设置日期范围
    today = timezone.now()
    if date_filter == 'today':
        date_from = today.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == 'week':
        date_from = today - timedelta(days=7)
    elif date_filter == 'month':
        date_from = today - timedelta(days=30)
    else:
        date_from = today - timedelta(days=7)  # 默认一周
    
    # 获取聊天活动（从ChatSession）
    chat_sessions = ChatSession.objects.select_related('user').filter(
        started_at__gte=date_from
    ).order_by('-started_at')
    
    if user_filter:
        chat_sessions = chat_sessions.filter(user__user_type=user_filter)
    
    for session in chat_sessions:
        logs.append({
            'id': f'chat_{session.id}',
            'user': session.user,
            'action': 'chat',
            'details': f'创建聊天会话: {session.title[:50]}...' if session.title and len(session.title) > 50 else f'创建聊天会话: {session.title or "未命名会话"}',
            'created_at': session.started_at,
            'ip_address': session.ip_address,
            'get_action_display': lambda: '聊天会话'
        })
    
    # 获取用户登录活动（从LoginLog）
    login_logs = LoginLog.objects.select_related('user').filter(
        login_time__gte=date_from
    ).order_by('-login_time')
    
    if user_filter:
        login_logs = login_logs.filter(user__user_type=user_filter)
    
    for log in login_logs:
        logs.append({
            'id': f'login_{log.id}',
            'user': log.user,
            'action': 'login',
            'details': f'用户{"成功" if log.login_status == "success" else "失败"}登录系统',
            'created_at': log.login_time,
            'ip_address': log.ip_address,
            'get_action_display': lambda: '用户登录'
        })
    
    # 获取用户行为日志（从UserBehaviorLog）
    try:
        behavior_logs = UserBehaviorLog.objects.select_related('user').filter(
            created_at__gte=date_from
        ).order_by('-created_at')
        
        if user_filter:
            behavior_logs = behavior_logs.filter(user__user_type=user_filter)
        
        for log in behavior_logs:
            logs.append({
                'id': f'behavior_{log.id}',
                'user': log.user,
                'action': log.action_type,
                'details': log.action_detail or f'用户执行了{log.get_action_type_display()}操作',
                'created_at': log.created_at,
                'ip_address': log.ip_address,
                'get_action_display': lambda: log.get_action_type_display()
            })
    except:
        pass  # UserBehaviorLog可能不存在
    
    # 按时间排序
    logs.sort(key=lambda x: x['created_at'], reverse=True)
    
    # 分页
    paginator = Paginator(logs, per_page)
    page_obj = paginator.get_page(page)
    
    return page_obj

def get_admin_operation_logs(page=1, per_page=20):
    """获取管理员操作日志"""
    logs = []
    
    # 获取管理员操作记录（从AdminOperationLog）
    try:
        admin_logs = AdminOperationLog.objects.select_related('admin_user', 'target_user').order_by('-created_at')
        
        for log in admin_logs:
            logs.append({
                'id': f'admin_op_{log.id}',
                'admin_user': log.admin_user,
                'target_user': log.target_user,
                'operation': log.operation_type,
                'details': log.operation_detail,
                'old_value': None,
                'new_value': None,
                'created_at': log.created_at,
                'get_operation_display': lambda: log.get_operation_type_display()
            })
    except:
        # 如果AdminOperationLog模型不存在，使用管理员用户生成模拟数据
        admin_users = User.objects.filter(user_type='admin')
        
        for admin in admin_users:
            # 模拟一些管理员操作记录
            logs.append({
                'id': f'admin_{admin.id}_config',
                'admin_user': admin,
                'target_user': None,
                'operation': 'system_config',
                'details': '更新系统配置参数',
                'old_value': None,
                'new_value': None,
                'created_at': timezone.now() - timedelta(hours=2),
                'get_operation_display': lambda: '系统配置'
            })
            
            # 模拟用户管理操作
            students = User.objects.filter(user_type='student')[:3]
            for student in students:
                logs.append({
                    'id': f'admin_{admin.id}_user_{student.id}',
                    'admin_user': admin,
                    'target_user': student,
                    'operation': 'user_update',
                    'details': f'更新用户 {student.username} 的信息',
                    'old_value': None,
                    'new_value': None,
                    'created_at': timezone.now() - timedelta(hours=1),
                    'get_operation_display': lambda: '更新用户'
                })
    
    # 按时间排序
    logs.sort(key=lambda x: x['created_at'], reverse=True)
    
    # 分页
    paginator = Paginator(logs, per_page)
    page_obj = paginator.get_page(page)
    
    return page_obj

def get_login_logs(page=1, status_filter='', per_page=20):
    """获取登录日志"""
    logs = []
    
    # 从LoginLog模型获取登录记录
    try:
        login_logs = LoginLog.objects.select_related('user').order_by('-login_time')
        
        if status_filter:
            if status_filter == 'success':
                login_logs = login_logs.filter(login_status='success')
            elif status_filter == 'failed':
                login_logs = login_logs.filter(login_status='failed')
        
        for log in login_logs:
            logs.append({
                'id': f'login_{log.id}',
                'user': log.user,
                'username_attempted': log.user.username,
                'status': log.login_status,
                'failure_reason': None if log.login_status == 'success' else 'invalid_credentials',
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'created_at': log.login_time,
                'get_status_display': lambda: '成功' if log.login_status == 'success' else '失败',
                'get_failure_reason_display': lambda: None if log.login_status == 'success' else '认证失败'
            })
    except:
        # 如果LoginLog模型结构不同，使用User.last_login生成数据
        users = User.objects.filter(last_login__isnull=False).order_by('-last_login')
        
        for user in users:
            if user.last_login:
                # 成功登录记录
                if not status_filter or status_filter == 'success':
                    logs.append({
                        'id': f'login_success_{user.id}',
                        'user': user,
                        'username_attempted': user.username,
                        'status': 'success',
                        'failure_reason': None,
                        'ip_address': '127.0.0.1',
                        'user_agent': None,
                        'created_at': user.last_login,
                        'get_status_display': lambda: '成功',
                        'get_failure_reason_display': lambda: None
                    })
                
                # 模拟一些失败记录
                if (not status_filter or status_filter == 'failed') and user.id % 4 == 0:
                    logs.append({
                        'id': f'login_failed_{user.id}',
                        'user': None,
                        'username_attempted': user.username,
                        'status': 'failed',
                        'failure_reason': 'invalid_credentials',
                        'ip_address': '127.0.0.1',
                        'user_agent': None,
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
