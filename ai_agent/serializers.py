"""
API序列化器
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from behavior_tracking.models import ChatSession, ChatMessage, UserBehaviorLog
from permissions.models import AIFunction, StudentFunctionPermission
from student_management.models import StudentUsageStatistics, StudentTag

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'user_type', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class AIFunctionSerializer(serializers.ModelSerializer):
    """AI功能序列化器"""
    class Meta:
        model = AIFunction
        fields = ['id', 'function_code', 'name', 'description', 'function_type', 'is_active', 'is_beta']


class ChatSessionSerializer(serializers.ModelSerializer):
    """聊天会话序列化器"""
    user = UserSerializer(read_only=True)
    duration = serializers.ReadOnlyField()
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'session_id', 'user', 'title', 'function_code', 
            'started_at', 'ended_at', 'message_count', 'total_tokens', 
            'is_active', 'duration'
        ]
        read_only_fields = ['id', 'session_id', 'started_at', 'message_count', 'total_tokens']


class ChatMessageSerializer(serializers.ModelSerializer):
    """聊天消息序列化器"""
    session = ChatSessionSerializer(read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'session', 'message_type', 'content', 'tokens_used',
            'function_called', 'model_type', 'response_time', 'created_at'
        ]
        read_only_fields = ['id', 'tokens_used', 'response_time', 'created_at']


class CreateChatSessionSerializer(serializers.Serializer):
    """创建聊天会话序列化器"""
    function_code = serializers.CharField(max_length=50, required=False)
    title = serializers.CharField(max_length=200, required=False)


class SendMessageSerializer(serializers.Serializer):
    """发送消息序列化器"""
    session_id = serializers.CharField(max_length=100)
    message = serializers.CharField()
    function_code = serializers.CharField(max_length=50, required=False)
    model_type = serializers.CharField(max_length=50, default='chat')


class StudentFunctionPermissionSerializer(serializers.ModelSerializer):
    """学生功能权限序列化器"""
    student = UserSerializer(read_only=True)
    function = AIFunctionSerializer(read_only=True)
    
    class Meta:
        model = StudentFunctionPermission
        fields = [
            'id', 'student', 'function', 'is_enabled', 'daily_quota',
            'granted_at', 'expires_at'
        ]


class StudentUsageStatisticsSerializer(serializers.ModelSerializer):
    """学生使用统计序列化器"""
    student = UserSerializer(read_only=True)
    
    class Meta:
        model = StudentUsageStatistics
        fields = [
            'id', 'student', 'date', 'total_sessions', 'total_messages',
            'total_duration_minutes', 'functions_used'
        ]


class UserBehaviorLogSerializer(serializers.ModelSerializer):
    """用户行为日志序列化器"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserBehaviorLog
        fields = [
            'id', 'user', 'action_type', 'action_detail', 'ip_address',
            'session_id', 'created_at'
        ]


class StudentTagSerializer(serializers.ModelSerializer):
    """学生标签序列化器"""
    class Meta:
        model = StudentTag
        fields = ['id', 'name', 'tag_type', 'color', 'description', 'is_active']


class DashboardStatsSerializer(serializers.Serializer):
    """仪表板统计序列化器"""
    total_users = serializers.IntegerField()
    total_sessions = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    active_functions = serializers.IntegerField()
    new_users_today = serializers.IntegerField()
    sessions_today = serializers.IntegerField()
    messages_today = serializers.IntegerField()


class MonitoringAlertSerializer(serializers.Serializer):
    """监控警报序列化器"""
    title = serializers.CharField()
    message = serializers.CharField()
    severity = serializers.ChoiceField(choices=['low', 'medium', 'high'])
    time = serializers.CharField()
    type = serializers.CharField() 