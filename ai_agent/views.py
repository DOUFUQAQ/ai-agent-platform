from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, get_user_model
from .services import AIAgentService
import json
import logging
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from datetime import datetime, timedelta
from django.db.models import Count, Q, Sum
from django.utils import timezone
from permissions.models import AIFunction, StudentFunctionPermission
from student_management.models import StudentUsageStatistics, StudentTag
from behavior_tracking.models import (
    ChatSession, ChatMessage, UserBehaviorLog, SensitiveWordDetection, 
    AbnormalBehaviorDetection
)
import random
import uuid
from .serializers import SendMessageSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
    """创建新的对话会话"""
    try:
        function_code = request.data.get('function_code')
        service = AIAgentService()
        session_id = service.create_chat_session(request.user, function_code)
        
        return Response({
            'success': True,
            'session_id': session_id,
            'message': '会话创建成功'
        })
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """发送消息并处理敏感词检测"""
    try:
        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': '数据验证失败',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取验证后的数据
        message_content = serializer.validated_data['message']
        session_id = serializer.validated_data.get('session_id')
        model_type = serializer.validated_data.get('model_type', 'chat')
        function_code = serializer.validated_data.get('function_code', 'qa')
        
        # 获取或创建会话
        if session_id:
            session = get_object_or_404(ChatSession, session_id=session_id, user=request.user)
        else:
            session = ChatSession.objects.create(
                user=request.user,
                session_id=str(uuid.uuid4()),
                title=message_content[:30] + "..." if len(message_content) > 30 else message_content,
                started_at=timezone.now(),
                is_active=True
            )
        
        # 实时敏感词检测（先创建临时消息对象用于检测）
        from behavior_tracking.monitoring import MonitoringService
        monitoring_service = MonitoringService()
        
        # 创建临时用户消息用于敏感词检测
        temp_user_message = ChatMessage(
            session=session,
            message_type='user',
            content=message_content,
            tokens_used=len(message_content) // 4,  # 简单估算
            created_at=timezone.now()
        )
        
        # 处理敏感词检测
        detection_result = monitoring_service.process_new_message(temp_user_message)
        
        # 检查是否包含敏感内容
        if detection_result.get('sensitive_word', {}).get('detected', False):
            severity = detection_result['sensitive_word']['severity']
            words = detection_result['sensitive_word']['words']
            
            # 如果是高风险内容，直接拒绝处理
            if severity == 'high':
                return Response({
                    'success': False,
                    'error': '消息包含不当内容，请修改后重试',
                    'sensitive_detected': True,
                    'severity': severity
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 中低风险内容给出警告但继续处理
            elif severity in ['medium', 'low']:
                logger.warning(f"用户 {request.user.username} 发送了包含敏感词的消息: {words}")
        
        # 处理AI响应 - 使用真正的DeepSeek API
        try:
            # 使用AIAgentService调用DeepSeek API
            ai_service = AIAgentService()
            result = ai_service.send_message(
                user=request.user,
                session_id=session.session_id,
                message=message_content,
                function_code=function_code,
                model_type=model_type
            )
            
            if result['success']:
                response_data = {
                    'success': True,
                    'response': result['response'],
                    'tokens_used': result['tokens_used'],
                    'response_time': result['response_time'],
                    'model': result['model'],
                    'session_id': session.session_id
                }
            else:
                # API调用失败时的备用回复
                mock_responses = {
                    'chat': f"我理解您提到的问题。关于「{message_content[:20]}...」，我来为您详细解答...",
                    'reasoning': f"让我来分析您的问题：{message_content[:30]}... 基于逻辑推理，我认为...",
                    'tutor': f"作为您的学习助手，关于「{message_content[:25]}...」这个问题，让我来帮您理解..."
                }
                
                mock_response = mock_responses.get(model_type, mock_responses['chat'])
                
                # 创建AI回复消息
                ai_message = ChatMessage.objects.create(
                    session=session,
                    message_type='assistant',
                    content=mock_response,
                    tokens_used=len(mock_response) // 4,
                    response_time=random.uniform(0.5, 2.0),
                    created_at=timezone.now()
                )
                
                # 更新会话信息
                session.message_count = session.message_count + 2
                session.total_tokens = session.total_tokens + temp_user_message.tokens_used + ai_message.tokens_used
                session.last_message_at = timezone.now()
                session.save()
                
                response_data = {
                    'success': True,
                    'response': mock_response,
                    'tokens_used': ai_message.tokens_used,
                    'response_time': ai_message.response_time,
                    'model': f'deepseek-{model_type}',
                    'session_id': session.session_id,
                    'note': 'DeepSeek API暂时不可用，这是一个模拟回复'
                }
            
            # 如果检测到敏感内容，在响应中包含警告
            if detection_result.get('sensitive_word', {}).get('detected', False):
                response_data['sensitive_warning'] = {
                    'detected': True,
                    'severity': detection_result['sensitive_word']['severity'],
                    'message': '您的消息包含敏感内容，已记录并将进行审查'
                }
            
            return Response(response_data)
            
        except Exception as ai_error:
            logger.error(f"AI服务调用失败: {str(ai_error)}")
            
            # AI服务失败时的备用回复
            try:
                fallback_response = f"抱歉，我暂时无法处理您的请求。您提到的「{message_content[:30]}...」是一个很好的问题，请稍后再试。"
                
                ai_message = ChatMessage.objects.create(
                    session=session,
                    message_type='assistant',
                    content=fallback_response,
                    tokens_used=len(fallback_response) // 4,
                    response_time=0.1,
                    created_at=timezone.now()
                )
                
                session.message_count += 2
                session.save()
                
                return Response({
                    'success': True,
                    'response': fallback_response,
                    'tokens_used': 0,
                    'response_time': 0.1,
                    'model': f'deepseek-{model_type}',
                    'note': 'DeepSeek API暂时不可用，这是一个模拟回复'
                })
                
            except Exception as fallback_error:
                logger.error(f"模拟回复创建失败: {str(fallback_error)}")
                return Response({
                    'success': False,
                    'error': f'消息处理失败: {str(ai_error)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"发送消息失败: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def end_chat_session(request):
    """结束对话会话"""
    try:
        session_id = request.data.get('session_id')
        delete_session = request.data.get('delete_session', False)  # 新增删除参数
        
        if not session_id:
            return Response({
                'success': False,
                'error': '缺少会话ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        service = AIAgentService()
        service.end_chat_session(request.user, session_id, delete_session=delete_session)
        
        message = '会话已删除' if delete_session else '会话已结束'
        return Response({
            'success': True,
            'message': message
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_history(request):
    """获取对话历史"""
    try:
        session_id = request.GET.get('session_id')
        limit = int(request.GET.get('limit', 50))
        
        service = AIAgentService()
        history = service.get_user_chat_history(request.user, session_id, limit)
        
        return Response({
            'success': True,
            'history': history
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# 用户认证API
@api_view(['POST'])
def user_login(request):
    """用户登录"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                'success': False,
                'error': '用户名和密码不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            
            # 记录登录日志
            from authentication.models import LoginLog
            LoginLog.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                login_status='success'
            )
            
            return Response({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'user_type': user.user_type,
                    'email': user.email
                },
                'message': '登录成功'
            })
        else:
            return Response({
                'success': False,
                'error': '用户名或密码错误'
            }, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_logout(request):
    """用户登出"""
    try:
        # 更新登录日志
        from authentication.models import LoginLog
        from django.utils import timezone
        
        latest_log = LoginLog.objects.filter(
            user=request.user,
            logout_time__isnull=True
        ).order_by('-login_time').first()
        
        if latest_log:
            latest_log.logout_time = timezone.now()
            latest_log.save()
        
        logout(request)
        
        return Response({
            'success': True,
            'message': '登出成功'
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """获取用户信息"""
    try:
        user = request.user
        profile_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'user_type': user.user_type,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        }
        
        return Response({
            'success': True,
            'user': profile_data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# 页面视图
@login_required
def chat_interface(request):
    """聊天界面"""
    return render(request, 'ai_agent/chat.html')


def login_page(request):
    """登录页面"""
    if request.user.is_authenticated:
        return redirect('/ai_agent/chat/')
    return render(request, 'authentication/login.html')


def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@staff_member_required
def admin_dashboard(request):
    """管理员仪表板"""
    
    # 基础统计数据
    total_users = User.objects.filter(user_type='student').count()
    total_sessions = ChatSession.objects.count()
    total_messages = ChatMessage.objects.count()
    active_functions = AIFunction.objects.filter(is_active=True).count()
    beta_functions = AIFunction.objects.filter(is_beta=True).count()
    
    # 今日数据
    today = timezone.now().date()
    new_users_today = User.objects.filter(
        user_type='student',
        date_joined__date=today
    ).count()
    
    sessions_today = ChatSession.objects.filter(
        started_at__date=today
    ).count()
    
    messages_today = ChatMessage.objects.filter(
        created_at__date=today
    ).count()
    
    # 最近7天的活跃度数据
    activity_dates = []
    daily_active_users = []
    daily_new_users = []
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        activity_dates.append(date.strftime('%m/%d'))
        
        # 当日活跃用户（有会话的用户）
        active_count = ChatSession.objects.filter(
            started_at__date=date
        ).values('user').distinct().count()
        daily_active_users.append(active_count)
        
        # 当日新用户
        new_count = User.objects.filter(
            user_type='student',
            date_joined__date=date
        ).count()
        daily_new_users.append(new_count)
    
    # 功能使用分布
    function_usage = ChatMessage.objects.filter(
        function_called__isnull=False
    ).values('function_called').annotate(
        count=Count('id')
    ).order_by('-count')[:6]
    
    function_names = []
    function_usage_data = []
    for usage in function_usage:
        try:
            func = AIFunction.objects.get(function_code=usage['function_called'])
            function_names.append(func.name)
        except AIFunction.DoesNotExist:
            function_names.append(usage['function_called'])
        function_usage_data.append(usage['count'])
    
    context = {
        'total_users': total_users,
        'total_sessions': total_sessions,
        'total_messages': total_messages,
        'active_functions': active_functions,
        'beta_functions': beta_functions,
        'new_users_today': new_users_today,
        'sessions_today': sessions_today,
        'messages_today': messages_today,
        'activity_dates': json.dumps(activity_dates),
        'daily_active_users': json.dumps(daily_active_users),
        'daily_new_users': json.dumps(daily_new_users),
        'function_names': json.dumps(function_names),
        'function_usage_data': json.dumps(function_usage_data),
    }
    
    return render(request, 'admin_dashboard.html', context)


@staff_member_required
def dashboard_stats_api(request):
    """仪表板统计数据API"""
    
    total_users = User.objects.filter(user_type='student').count()
    total_sessions = ChatSession.objects.count()
    total_messages = ChatMessage.objects.count()
    active_functions = AIFunction.objects.filter(is_active=True).count()
    
    return JsonResponse({
        'total_users': total_users,
        'total_sessions': total_sessions,
        'total_messages': total_messages,
        'active_functions': active_functions,
    })


@staff_member_required
def alerts_api(request):
    """实时警报API"""
    
    alerts = []
    
    try:
        # 检查异常行为（如果模型存在）
        from behavior_tracking.models import AbnormalBehaviorDetection
        recent_abnormal = AbnormalBehaviorDetection.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24),
            is_handled=False
        ).order_by('-created_at')[:5]
        
        for abnormal in recent_abnormal:
            severity = 'high' if abnormal.risk_score >= 80 else 'medium' if abnormal.risk_score >= 50 else 'low'
            alerts.append({
                'title': f'异常行为检测: {abnormal.get_behavior_type_display()}',
                'message': f'用户 {abnormal.user.username} - 风险评分: {abnormal.risk_score}',
                'severity': severity,
                'time': abnormal.created_at.strftime('%H:%M')
            })
    except (ImportError, Exception):
        pass
    
    try:
        # 检查敏感词检测（如果模型存在）
        from behavior_tracking.models import SensitiveWordDetection
        recent_sensitive = SensitiveWordDetection.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24),
            is_reviewed=False
        ).order_by('-created_at')[:5]
        
        for sensitive in recent_sensitive:
            alerts.append({
                'title': f'敏感词检测: {sensitive.get_detection_type_display()}',
                'message': f'用户 {sensitive.message.session.user.username} - 严重程度: {sensitive.get_severity_display()}',
                'severity': sensitive.severity,
                'time': sensitive.created_at.strftime('%H:%M')
            })
    except (ImportError, Exception):
        pass
    
    # 检查系统负载（使用现有的模型）
    try:
        high_usage_users = ChatSession.objects.filter(
            started_at__gte=timezone.now() - timedelta(hours=1)
        ).values('user').annotate(
            session_count=Count('id')
        ).filter(session_count__gte=10)
        
        for user_data in high_usage_users:
            user = User.objects.get(id=user_data['user'])
            alerts.append({
                'title': '高频使用检测',
                'message': f'用户 {user.username} 在过去1小时内创建了 {user_data["session_count"]} 个会话',
                'severity': 'medium',
                'time': timezone.now().strftime('%H:%M')
            })
    except Exception:
        pass
    
    # 如果没有警报，添加一个系统正常的消息
    if not alerts:
        alerts.append({
            'title': '系统状态正常',
            'message': '暂无安全警报，系统运行正常',
            'severity': 'low',
            'time': timezone.now().strftime('%H:%M')
        })
    
    # 按严重程度排序
    severity_order = {'high': 3, 'medium': 2, 'low': 1}
    alerts.sort(key=lambda x: severity_order.get(x['severity'], 0), reverse=True)
    
    return JsonResponse({
        'alerts': alerts[:10]  # 最多返回10个警报
    })


@login_required
def user_token_dashboard(request):
    """用户个人Token统计仪表板"""
    user = request.user
    
    # 使用新的Token统计服务
    from ai_agent.services import UserTokenService
    from datetime import datetime, timedelta
    
    # 获取30天的Token使用统计
    token_stats = UserTokenService.get_user_token_stats(user, days=30)
    
    # 获取用户排名
    user_ranking = UserTokenService.get_user_ranking(user)
    
    # 今日Token使用 - 统计所有消息的Token（用户输入+AI回复）
    today = timezone.now().date()
    today_tokens = ChatMessage.objects.filter(
        session__user=user,
        created_at__date=today
    ).aggregate(total=Sum('tokens_used'))['total'] or 0
    
    # 本月Token使用 - 统计所有消息的Token
    month_start = today.replace(day=1)
    month_tokens = ChatMessage.objects.filter(
        session__user=user,
        created_at__date__gte=month_start
    ).aggregate(total=Sum('tokens_used'))['total'] or 0
    
    # 按功能分组的Token使用 - 统计所有消息（包括用户输入）
    function_tokens = ChatMessage.objects.filter(
        session__user=user,
        function_called__isnull=False
    ).values('function_called').annotate(
        total_tokens=Sum('tokens_used'),
        count=Count('id')
    ).order_by('-total_tokens')[:10]
    
    # 获取功能名称和计算百分比
    function_stats = []
    total_function_tokens = sum(func['total_tokens'] for func in function_tokens)
    
    for func in function_tokens:
        try:
            from ai_agent.models import AIFunction
            function = AIFunction.objects.get(function_code=func['function_called'])
            function_name = function.name
        except:
            function_name = func['function_called']
        
        # 计算百分比
        percentage = (func['total_tokens'] / max(total_function_tokens, 1)) * 100
        
        function_stats.append({
            'function_code': func['function_called'],
            'function_name': function_name,
            'total_tokens': func['total_tokens'],
            'count': func['count'],
            'percentage': round(percentage, 1)
        })
    
    # 最近7天的使用情况
    week_ago = today - timedelta(days=7)
    recent_sessions = ChatSession.objects.filter(
        user=user,
        started_at__date__gte=week_ago
    ).order_by('-started_at')[:10]
    
    context = {
        'user': user,
        'stats': {
            'today_tokens': today_tokens,
            'month_tokens': month_tokens,
            'total_tokens': token_stats['total_tokens'],
            'user_rank': user_ranking['rank'],
        },
        'daily_tokens': token_stats['daily_data'],
        'function_stats': function_stats,
        'recent_sessions': recent_sessions,
        'page_title': 'Token使用统计'
    }
    
    return render(request, 'ai_agent/user_token_dashboard.html', context)
