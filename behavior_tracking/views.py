from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
import json

from authentication.decorators import admin_required, require_role
from .models import (
    ChatSession, ChatMessage, UserBehaviorLog,
    SensitiveWordDetection, AbnormalBehaviorDetection,
    FunctionUsageStatistics
)
from .services import (
    BehaviorAnalysisService, AbnormalBehaviorDetector,
    SensitiveContentDetector, StatisticsService
)

User = get_user_model()


@login_required
@require_role('admin', 'teacher')
def behavior_dashboard(request):
    """行为分析仪表板"""
    try:
        from .services import StatisticsService
        from django.utils import timezone
        from datetime import timedelta
        
        # 获取真实的仪表板统计数据
        dashboard_stats = StatisticsService.get_dashboard_stats()
        
        # 获取活跃度趋势（最近7天）
        activity_trend = []
        today = timezone.now().date()
        for i in range(7):
            date = today - timedelta(days=i)
            
            # 当日会话数
            daily_sessions = ChatSession.objects.filter(
                started_at__date=date
            ).count()
            
            # 当日活跃用户数
            daily_users = ChatSession.objects.filter(
                started_at__date=date
            ).values('user').distinct().count()
            
            activity_trend.append({
                'date': date.strftime('%Y-%m-%d'),
                'sessions': daily_sessions,
                'users': daily_users
            })
        
        activity_trend.reverse()  # 按时间正序
        
        # 获取功能使用统计（真实数据）
        from .services import BehaviorAnalysisService
        function_usage = BehaviorAnalysisService.get_function_usage_stats(7)
        
        # 获取最近异常行为
        recent_abnormal = AbnormalBehaviorDetection.objects.filter(
            is_handled=False
        ).select_related('user').order_by('-created_at')[:5]
        
        # 获取最近敏感内容检测
        recent_sensitive = SensitiveWordDetection.objects.filter(
            is_reviewed=False
        ).select_related('message__session__user').order_by('-created_at')[:5]
        
        context = {
            'dashboard_stats': dashboard_stats,
            'activity_trend': json.dumps(activity_trend),
            'function_stats': function_usage,
            'recent_abnormal': recent_abnormal,
            'recent_sensitive': recent_sensitive,
        }
        
        return render(request, 'behavior_tracking/dashboard.html', context)
        
    except Exception as e:
        # 如果服务调用失败，提供基础统计
        today = timezone.now().date()
        
        # 基础统计数据
        basic_stats = {
            'today': {
                'sessions': ChatSession.objects.filter(started_at__date=today).count(),
                'users': ChatSession.objects.filter(started_at__date=today).values('user').distinct().count(),
                'messages': ChatMessage.objects.filter(created_at__date=today, message_type='user').count()
            },
            'week': {
                'users': ChatSession.objects.filter(
                    started_at__date__gte=today - timedelta(days=7)
                ).values('user').distinct().count()
            },
            'alerts': {
                'unhandled_abnormal': AbnormalBehaviorDetection.objects.filter(is_handled=False).count(),
                'unreviewed_sensitive': SensitiveWordDetection.objects.filter(is_reviewed=False).count()
            }
        }
        
        context = {
            'dashboard_stats': basic_stats,
            'activity_trend': json.dumps([]),
            'function_stats': {'functions': []},
            'recent_abnormal': [],
            'recent_sensitive': [],
            'error_message': f'部分功能加载失败: {str(e)}'
        }
        
        return render(request, 'behavior_tracking/dashboard.html', context)


@login_required
@require_role('admin', 'teacher')
def user_behavior_list(request):
    """用户行为列表"""
    # 搜索和筛选参数
    search_query = request.GET.get('search', '')
    user_type_filter = request.GET.get('user_type', '')
    period = request.GET.get('period', 'month')
    
    # 构建查询
    users = User.objects.all()
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if user_type_filter:
        users = users.filter(user_type=user_type_filter)
    
    # 只显示有行为记录的用户
    users_with_activity = users.filter(
        chatsession__isnull=False
    ).distinct().order_by('-last_login')
    
    # 分页
    paginator = Paginator(users_with_activity, 20)
    page = request.GET.get('page')
    users_page = paginator.get_page(page)
    
    # 为每个用户添加统计信息
    users_with_stats = []
    for user in users_page:
        user_stats = StatisticsService.get_user_statistics(user.id, period)
        
        # 获取最近活跃时间
        last_session = ChatSession.objects.filter(user=user).first()
        
        # 检查是否有未处理的异常行为
        has_abnormal = AbnormalBehaviorDetection.objects.filter(
            user=user, is_handled=False
        ).exists()
        
        users_with_stats.append({
            'user': user,
            'stats': user_stats,
            'last_active': last_session.started_at if last_session else None,
            'has_abnormal': has_abnormal
        })
    
    # 用户类型选项
    user_type_choices = User.USER_TYPE_CHOICES
    
    context = {
        'users_page': users_page,
        'users_with_stats': users_with_stats,
        'search_query': search_query,
        'user_type_filter': user_type_filter,
        'period': period,
        'user_type_choices': user_type_choices,
    }
    
    return render(request, 'behavior_tracking/user_list.html', context)


@login_required
@require_role('admin', 'teacher')
def user_behavior_detail(request, user_id):
    """用户行为详情页面"""
    user = get_object_or_404(User, id=user_id)
    
    # 获取用户行为画像
    behavior_profile = BehaviorAnalysisService.get_user_behavior_profile(user_id)
    
    # 获取用户的会话列表（最近50个）
    recent_sessions = ChatSession.objects.filter(
        user=user
    ).order_by('-started_at')[:50]
    
    # 获取异常行为记录
    abnormal_behaviors = AbnormalBehaviorDetection.objects.filter(
        user=user
    ).order_by('-created_at')[:10]
    
    # 获取敏感内容检测记录
    sensitive_detections = SensitiveWordDetection.objects.filter(
        message__session__user=user
    ).order_by('-created_at')[:10]
    
    # 获取使用时间趋势（最近30天）
    time_trend = BehaviorAnalysisService.get_daily_activity_trend(30)
    user_time_trend = []
    for day_data in time_trend:
        day_sessions = ChatSession.objects.filter(
            user=user,
            started_at__date=day_data['date']
        ).count()
        user_time_trend.append({
            'date': day_data['date'],
            'sessions': day_sessions
        })
    
    context = {
        'target_user': user,
        'behavior_profile': behavior_profile,
        'recent_sessions': recent_sessions,
        'abnormal_behaviors': abnormal_behaviors,
        'sensitive_detections': sensitive_detections,
        'time_trend': json.dumps(user_time_trend),
    }
    
    return render(request, 'behavior_tracking/user_detail.html', context)


@login_required
@require_role('admin', 'teacher')
def session_detail(request, session_id):
    """会话详情页面"""
    session = get_object_or_404(ChatSession, session_id=session_id)
    
    # 获取会话消息
    messages = ChatMessage.objects.filter(session=session).order_by('created_at')
    
    # 检查是否有敏感内容检测
    sensitive_detections = SensitiveWordDetection.objects.filter(
        message__session=session
    )
    
    context = {
        'session': session,
        'messages': messages,
        'sensitive_detections': sensitive_detections,
    }
    
    return render(request, 'behavior_tracking/session_detail.html', context)


@login_required
@require_role('admin', 'teacher')
def abnormal_behavior_management(request):
    """异常行为管理页面"""
    # 搜索和筛选参数
    behavior_type = request.GET.get('behavior_type', '')
    status = request.GET.get('status', 'unhandled')
    risk_level = request.GET.get('risk_level', '')
    search_query = request.GET.get('search', '')
    
    # 构建查询
    detections = AbnormalBehaviorDetection.objects.all()
    
    if behavior_type:
        detections = detections.filter(behavior_type=behavior_type)
    
    if status == 'unhandled':
        detections = detections.filter(is_handled=False)
    elif status == 'handled':
        detections = detections.filter(is_handled=True)
    
    if risk_level:
        if risk_level == 'high':
            detections = detections.filter(risk_score__gte=70)
        elif risk_level == 'medium':
            detections = detections.filter(risk_score__gte=40, risk_score__lt=70)
        elif risk_level == 'low':
            detections = detections.filter(risk_score__lt=40)
    
    if search_query:
        detections = detections.filter(
            Q(user__username__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    detections = detections.order_by('-created_at')
    
    # 分页
    paginator = Paginator(detections, 20)
    page = request.GET.get('page')
    detections_page = paginator.get_page(page)
    
    # 统计数据
    total_unhandled = AbnormalBehaviorDetection.objects.filter(is_handled=False).count()
    high_risk_count = AbnormalBehaviorDetection.objects.filter(
        is_handled=False, risk_score__gte=70
    ).count()
    
    context = {
        'detections_page': detections_page,
        'behavior_type': behavior_type,
        'status': status,
        'risk_level': risk_level,
        'search_query': search_query,
        'total_unhandled': total_unhandled,
        'high_risk_count': high_risk_count,
        'behavior_type_choices': AbnormalBehaviorDetection.BEHAVIOR_TYPE_CHOICES,
    }
    
    return render(request, 'behavior_tracking/abnormal_management.html', context)


@login_required
@require_role('admin', 'teacher')
def sensitive_content_management(request):
    """敏感内容管理页面"""
    # 搜索和筛选参数
    detection_type = request.GET.get('detection_type', '')
    severity = request.GET.get('severity', '')
    status = request.GET.get('status', 'unreviewed')
    search_query = request.GET.get('search', '')
    
    # 构建查询
    detections = SensitiveWordDetection.objects.all()
    
    if detection_type:
        detections = detections.filter(detection_type=detection_type)
    
    if severity:
        detections = detections.filter(severity=severity)
    
    if status == 'unreviewed':
        detections = detections.filter(is_reviewed=False)
    elif status == 'reviewed':
        detections = detections.filter(is_reviewed=True)
    
    if search_query:
        detections = detections.filter(
            Q(message__session__user__username__icontains=search_query) |
            Q(context__icontains=search_query)
        )
    
    detections = detections.order_by('-created_at')
    
    # 分页
    paginator = Paginator(detections, 20)
    page = request.GET.get('page')
    detections_page = paginator.get_page(page)
    
    # 统计数据
    total_unreviewed = SensitiveWordDetection.objects.filter(is_reviewed=False).count()
    high_severity_count = SensitiveWordDetection.objects.filter(
        is_reviewed=False, severity='high'
    ).count()
    
    context = {
        'detections_page': detections_page,
        'detection_type': detection_type,
        'severity': severity,
        'status': status,
        'search_query': search_query,
        'total_unreviewed': total_unreviewed,
        'high_severity_count': high_severity_count,
        'detection_type_choices': SensitiveWordDetection.DETECTION_TYPE_CHOICES,
        'severity_choices': SensitiveWordDetection.SEVERITY_CHOICES,
    }
    
    return render(request, 'behavior_tracking/sensitive_management.html', context)


@login_required
@require_role('admin', 'teacher')
def function_usage_analytics(request):
    """功能使用分析页面"""
    period = request.GET.get('period', '30')
    
    try:
        days = int(period)
    except ValueError:
        days = 30
    
    # 获取功能使用统计
    function_stats = BehaviorAnalysisService.get_function_usage_stats(days)
    
    # 获取时间趋势数据
    activity_trend = BehaviorAnalysisService.get_daily_activity_trend(days)
    
    # 获取用户活跃度统计
    activity_stats = BehaviorAnalysisService.get_user_activity_stats(None, days)
    
    context = {
        'function_stats': function_stats,
        'activity_trend': json.dumps(activity_trend),
        'activity_stats': activity_stats,
        'period': period,
    }
    
    return render(request, 'behavior_tracking/function_analytics.html', context)


# API接口
@login_required
@admin_required
@require_http_methods(["POST"])
def handle_abnormal_behavior(request):
    """处理异常行为"""
    try:
        data = json.loads(request.body)
        detection_id = data.get('detection_id')
        action = data.get('action')  # 'confirm', 'dismiss', 'investigate'
        
        detection = get_object_or_404(AbnormalBehaviorDetection, id=detection_id)
        
        if action == 'confirm':
            detection.is_confirmed = True
            detection.is_handled = True
            detection.handled_by = request.user
            detection.handled_at = timezone.now()
            messages.success(request, f'已确认异常行为：{detection.description}')
            
        elif action == 'dismiss':
            detection.is_handled = True
            detection.handled_by = request.user
            detection.handled_at = timezone.now()
            messages.success(request, f'已忽略异常行为：{detection.description}')
            
        elif action == 'investigate':
            # 标记为需要进一步调查
            detection.is_confirmed = True
            messages.info(request, f'已标记为需要调查：{detection.description}')
        
        detection.save()
        
        return JsonResponse({
            'success': True,
            'message': '处理成功'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@admin_required
@require_http_methods(["POST"])
def review_sensitive_content(request):
    """审查敏感内容"""
    try:
        data = json.loads(request.body)
        detection_id = data.get('detection_id')
        action = data.get('action')  # 'approve', 'flag', 'escalate'
        action_note = data.get('action_note', '')
        
        detection = get_object_or_404(SensitiveWordDetection, id=detection_id)
        
        detection.is_reviewed = True
        detection.reviewed_by = request.user
        detection.reviewed_at = timezone.now()
        detection.action_taken = f"{action}: {action_note}"
        
        detection.save()
        
        # 如果是严重违规，可以考虑采取进一步措施
        if action == 'escalate':
            # 这里可以添加通知管理员、记录严重违规等逻辑
            messages.warning(request, f'已上报严重违规内容：{detection.context[:50]}...')
        else:
            messages.success(request, f'已审查敏感内容：{action}')
        
        return JsonResponse({
            'success': True,
            'message': '审查完成'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@admin_required
@require_http_methods(["POST"])
def run_behavior_detection(request):
    """手动运行行为检测"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        
        if user_id:
            # 为特定用户运行检测
            detections = AbnormalBehaviorDetector.run_detection_for_user(user_id)
            message = f'为用户ID {user_id} 运行检测，发现 {len(detections)} 个异常行为'
        else:
            # 为所有活跃用户运行检测
            today = timezone.now().date()
            active_users = ChatSession.objects.filter(
                started_at__date=today
            ).values('user').distinct()
            
            total_detections = 0
            for user_data in active_users:
                detections = AbnormalBehaviorDetector.run_detection_for_user(user_data['user'])
                total_detections += len(detections)
            
            message = f'为 {len(active_users)} 个活跃用户运行检测，发现 {total_detections} 个异常行为'
        
        return JsonResponse({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required
@require_role('admin', 'teacher')
def export_behavior_data(request):
    """导出行为数据"""
    # 这里可以实现数据导出功能
    # 为简化示例，返回JSON响应
    return JsonResponse({
        'success': True,
        'message': '数据导出功能待实现'
    })
