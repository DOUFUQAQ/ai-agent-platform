"""
API URL路由配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

app_name = 'api'

# REST API路由
urlpatterns = [
    # 用户相关API
    path('users/', api_views.UserListAPI.as_view(), name='user-list'),
    path('users/<int:pk>/', api_views.UserDetailAPI.as_view(), name='user-detail'),
    
    # AI功能相关API
    path('functions/', api_views.AIFunctionListAPI.as_view(), name='function-list'),
    
    # 聊天相关API
    path('chat/sessions/', api_views.ChatSessionListAPI.as_view(), name='session-list'),
    path('chat/sessions/create/', api_views.create_chat_session, name='session-create'),
    path('chat/messages/', api_views.ChatMessageListAPI.as_view(), name='message-list'),
    path('chat/send/', api_views.send_message_api, name='message-send'),
    
    # 统计分析API
    path('statistics/user/', api_views.user_statistics_api, name='user-statistics'),
    path('statistics/dashboard/', api_views.dashboard_stats_api, name='dashboard-stats'),
    
    # 监控API
    path('monitoring/alerts/', api_views.monitoring_alerts_api, name='monitoring-alerts'),
    
    # 权限管理API
    path('permissions/', api_views.StudentFunctionPermissionListAPI.as_view(), name='permission-list'),
    
    # 行为日志API
    path('logs/behavior/', api_views.UserBehaviorLogListAPI.as_view(), name='behavior-log-list'),
    
    # 使用统计API
    path('usage/statistics/', api_views.StudentUsageStatisticsListAPI.as_view(), name='usage-statistics'),
] 