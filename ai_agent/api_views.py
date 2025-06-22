"""
REST API视图
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from django.db.models import Count, Q, Avg, Sum
from django.shortcuts import get_object_or_404

from .serializers import (
    UserSerializer, AIFunctionSerializer, ChatSessionSerializer, 
    ChatMessageSerializer, CreateChatSessionSerializer, SendMessageSerializer,
    StudentFunctionPermissionSerializer, StudentUsageStatisticsSerializer,
    UserBehaviorLogSerializer, DashboardStatsSerializer, MonitoringAlertSerializer
)
from behavior_tracking.models import ChatSession, ChatMessage, UserBehaviorLog
from permissions.models import AIFunction, StudentFunctionPermission
from student_management.models import StudentUsageStatistics
from behavior_tracking.monitoring import monitoring_service
from .services import AIAgentService
from .agno_services import get_ai_service, AGNO_AVAILABLE
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """标准分页"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsOwnerOrAdmin(permissions.BasePermission):
    """只有所有者或管理员可以访问"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'student'):
            return obj.student == request.user
        
        return False


# ==================== 用户相关API ====================

class UserListAPI(generics.ListAPIView):
    """用户列表API"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = User.objects.all()
        user_type = self.request.query_params.get('user_type')
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        return queryset.order_by('-date_joined')


class UserDetailAPI(generics.RetrieveAPIView):
    """用户详情API"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)


# ==================== AI功能相关API ====================

class AIFunctionListAPI(generics.ListAPIView):
    """AI功能列表API"""
    serializer_class = AIFunctionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return AIFunction.objects.all()
        
        # 普通用户只能看到自己有权限的功能
        user_permissions = StudentFunctionPermission.objects.filter(
            student=self.request.user,
            is_enabled=True
        ).values_list('function_id', flat=True)
        
        return AIFunction.objects.filter(
            Q(id__in=user_permissions) | Q(is_active=True)
        ).distinct()


# ==================== 聊天相关API ====================

class ChatSessionListAPI(generics.ListCreateAPIView):
    """聊天会话列表API"""
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = ChatSession.objects.all()
            user_id = self.request.query_params.get('user_id')
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        else:
            queryset = ChatSession.objects.filter(user=self.request.user)
        
        return queryset.order_by('-started_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_available_services(request):
    """获取可用的AI服务"""
    services = []
    
    # 检查Agno是否可用
    if AGNO_AVAILABLE:
        services.append({
            'name': 'agno',
            'display_name': 'Agno智能体框架',
            'description': '支持多智能体、推理、记忆的高级AI框架',
            'agents': [
                {'type': 'chat', 'name': '聊天助手', 'description': '通用对话智能体'},
                {'type': 'reasoning', 'name': '推理专家', 'description': '具有高级推理能力'},
                {'type': 'research', 'name': '研究助手', 'description': '专业研究和信息收集'},
                {'type': 'tutor', 'name': '学习导师', 'description': '个性化学习指导'}
            ]
        })
    
    # DeepSeek服务
    services.append({
        'name': 'deepseek',
        'display_name': 'DeepSeek API',
        'description': '高性能的深度学习推理API',
        'models': [
            {'type': 'chat', 'name': 'DeepSeek聊天', 'model': 'deepseek-chat'},
            {'type': 'reasoning', 'name': 'DeepSeek推理', 'model': 'deepseek-reasoner'}
        ]
    })
    
    return Response({
        'success': True,
        'services': services,
        'default_service': 'agno' if AGNO_AVAILABLE else 'deepseek'
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_chat_session(request):
    """创建新的对话会话"""
    try:
        function_code = request.data.get('function_code')
        service_type = request.data.get('service_type', 'agno' if AGNO_AVAILABLE else 'deepseek')
        
        # 获取AI服务
        if service_type == 'agno' and AGNO_AVAILABLE:
            service = get_ai_service()
        else:
            service = AIAgentService()
        
        session_id = service.create_chat_session(request.user, function_code)
        
        return Response({
            'success': True,
            'session_id': session_id,
            'service_type': service_type,
            'message': '会话创建成功'
        })
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_message_agno(request):
    """使用Agno发送消息"""
    if not AGNO_AVAILABLE:
        return Response({
            'success': False,
            'error': 'Agno框架未安装，请安装后使用'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        session_id = request.data.get('session_id')
        message = request.data.get('message')
        function_code = request.data.get('function_code')
        agent_type = request.data.get('agent_type', 'chat')
        use_team = request.data.get('use_team', False)
        
        if not session_id or not message:
            return Response({
                'success': False,
                'error': '缺少必要参数'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证智能体类型
        valid_types = ['chat', 'reasoning', 'research', 'tutor']
        if agent_type not in valid_types:
            agent_type = 'chat'
        
        # 使用Agno服务
        service = get_ai_service()
        result = service.send_message(
            request.user, session_id, message, function_code, agent_type, use_team
        )
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Agno消息发送失败: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_message_deepseek(request):
    """使用DeepSeek发送消息"""
    try:
        session_id = request.data.get('session_id')
        message = request.data.get('message')
        function_code = request.data.get('function_code')
        model_type = request.data.get('model_type', 'chat')
        
        if not session_id or not message:
            return Response({
                'success': False,
                'error': '缺少必要参数'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证模型类型
        if model_type not in ['chat', 'reasoning']:
            model_type = 'chat'
        
        # 使用DeepSeek服务
        service = AIAgentService()
        result = service.send_message(request.user, session_id, message, function_code, model_type)
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"DeepSeek消息发送失败: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_message_unified(request):
    """统一消息发送接口 - 自动选择最佳服务"""
    try:
        session_id = request.data.get('session_id')
        message = request.data.get('message')
        function_code = request.data.get('function_code')
        service_type = request.data.get('service_type', 'auto')
        
        # 智能体/模型相关参数
        agent_type = request.data.get('agent_type', 'chat')  # for Agno
        model_type = request.data.get('model_type', 'chat')  # for DeepSeek
        use_team = request.data.get('use_team', False)       # for Agno
        
        if not session_id or not message:
            return Response({
                'success': False,
                'error': '缺少必要参数'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 自动选择服务
        if service_type == 'auto':
            service_type = 'agno' if AGNO_AVAILABLE else 'deepseek'
        
        # 根据服务类型调用相应的API
        if service_type == 'agno' and AGNO_AVAILABLE:
            service = get_ai_service()
            result = service.send_message(
                request.user, session_id, message, function_code, agent_type, use_team
            )
        else:
            service = AIAgentService()
            result = service.send_message(
                request.user, session_id, message, function_code, model_type
            )
            # 统一返回格式
            result['agent_type'] = model_type
            result['framework'] = 'deepseek'
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"统一消息发送失败: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_chat_history(request):
    """获取对话历史"""
    try:
        session_id = request.GET.get('session_id')
        limit = int(request.GET.get('limit', 50))
        service_type = request.GET.get('service_type', 'auto')
        
        # 选择服务
        if service_type == 'agno' and AGNO_AVAILABLE:
            service = get_ai_service()
        else:
            service = AIAgentService()
        
        history = service.get_user_chat_history(request.user, session_id, limit)
        
        return Response({
            'success': True,
            'history': history,
            'service_type': service_type
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def end_chat_session(request):
    """结束对话会话"""
    try:
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({
                'success': False,
                'error': '缺少session_id参数'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
        session.ended_at = timezone.now()
        session.save()
        
        return Response({
            'success': True,
            'message': '会话已结束'
        })
        
    except ChatSession.DoesNotExist:
        return Response({
            'success': False,
            'error': '会话不存在或无权限访问'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_message_api(request):
    """发送消息API"""
    serializer = SendMessageSerializer(data=request.data)
    if serializer.is_valid():
        session_id = serializer.validated_data['session_id']
        message = serializer.validated_data['message']
        function_code = serializer.validated_data.get('function_code', 'qa')
        model_type = serializer.validated_data.get('model_type', 'chat')
        
        try:
            session = ChatSession.objects.get(session_id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return Response({
                'success': False,
                'error': '会话不存在或无权限访问'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 使用现有的服务发送消息
        ai_service = AIAgentService()
        response = ai_service.send_message(session_id, message, function_code, model_type)
        
        if response['success']:
            # 获取最新的消息
            latest_messages = ChatMessage.objects.filter(
                session=session
            ).order_by('-created_at')[:2]
            
            return Response({
                'success': True,
                'response': response['response'],
                'messages': ChatMessageSerializer(latest_messages, many=True).data
            })
        else:
            return Response({
                'success': False,
                'error': response['error']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


class ChatMessageListAPI(generics.ListAPIView):
    """聊天消息列表API"""
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        session_id = self.request.query_params.get('session_id')
        if not session_id:
            return ChatMessage.objects.none()
        
        # 验证用户权限
        try:
            session = ChatSession.objects.get(session_id=session_id)
            if not self.request.user.is_staff and session.user != self.request.user:
                return ChatMessage.objects.none()
        except ChatSession.DoesNotExist:
            return ChatMessage.objects.none()
        
        return ChatMessage.objects.filter(
            session__session_id=session_id
        ).order_by('created_at')


# ==================== 统计分析API ====================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_statistics_api(request):
    """用户统计API"""
    user = request.user
    if not user.is_staff:
        # 普通用户只能查看自己的统计
        user_id = user.id
    else:
        # 管理员可以查看指定用户的统计
        user_id = request.GET.get('user_id', user.id)
        user = get_object_or_404(User, id=user_id)
    
    # 基础统计
    total_sessions = ChatSession.objects.filter(user=user).count()
    total_messages = ChatMessage.objects.filter(session__user=user).count()
    
    # 今日统计
    today = timezone.now().date()
    today_sessions = ChatSession.objects.filter(
        user=user, started_at__date=today
    ).count()
    today_messages = ChatMessage.objects.filter(
        session__user=user, created_at__date=today
    ).count()
    
    # 平均会话时长
    avg_duration = ChatSession.objects.filter(
        user=user, ended_at__isnull=False
    ).aggregate(
        avg_duration=Avg('ended_at__timestamp') - Avg('started_at__timestamp')
    )['avg_duration'] or 0
    
    # 最常用功能
    top_functions = ChatMessage.objects.filter(
        session__user=user, function_called__isnull=False
    ).values('function_called').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    return Response({
        'user': UserSerializer(user).data,
        'statistics': {
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'today_sessions': today_sessions,
            'today_messages': today_messages,
            'avg_duration_minutes': round(avg_duration / 60, 2) if avg_duration else 0,
            'top_functions': list(top_functions)
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def dashboard_stats_api(request):
    """仪表板统计API"""
    today = timezone.now().date()
    
    stats = {
        'total_users': User.objects.filter(user_type='student').count(),
        'total_sessions': ChatSession.objects.count(),
        'total_messages': ChatMessage.objects.count(),
        'active_functions': AIFunction.objects.filter(is_active=True).count(),
        'new_users_today': User.objects.filter(
            user_type='student', date_joined__date=today
        ).count(),
        'sessions_today': ChatSession.objects.filter(
            started_at__date=today
        ).count(),
        'messages_today': ChatMessage.objects.filter(
            created_at__date=today
        ).count()
    }
    
    serializer = DashboardStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def monitoring_alerts_api(request):
    """监控警报API"""
    alerts = monitoring_service.alerts_api(request)
    return Response(alerts.content)


# ==================== 权限管理API ====================

class StudentFunctionPermissionListAPI(generics.ListAPIView):
    """学生功能权限列表API"""
    serializer_class = StudentFunctionPermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = StudentFunctionPermission.objects.all()
            student_id = self.request.query_params.get('student_id')
            if student_id:
                queryset = queryset.filter(student_id=student_id)
        else:
            queryset = StudentFunctionPermission.objects.filter(
                student=self.request.user
            )
        
        return queryset.order_by('-granted_at')


# ==================== 行为日志API ====================

class UserBehaviorLogListAPI(generics.ListAPIView):
    """用户行为日志列表API"""
    serializer_class = UserBehaviorLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = UserBehaviorLog.objects.all()
            user_id = self.request.query_params.get('user_id')
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        else:
            queryset = UserBehaviorLog.objects.filter(user=self.request.user)
        
        return queryset.order_by('-created_at')


# ==================== 使用统计API ====================

class StudentUsageStatisticsListAPI(generics.ListAPIView):
    """学生使用统计列表API"""
    serializer_class = StudentUsageStatisticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = StudentUsageStatistics.objects.all()
            student_id = self.request.query_params.get('student_id')
            if student_id:
                queryset = queryset.filter(student_id=student_id)
        else:
            queryset = StudentUsageStatistics.objects.filter(student=self.request.user)
        
        # 日期范围筛选
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by('-date') 