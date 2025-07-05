from django.urls import path
from . import views
from . import agno_views

app_name = 'ai_agent'

urlpatterns = [
    # API端点
    path('api/chat/create/', views.create_chat_session, name='create_chat_session'),
    path('api/chat/send/', views.send_message, name='send_message'),
    path('api/chat/end/', views.end_chat_session, name='end_chat_session'),
    path('api/chat/history/', views.get_chat_history, name='get_chat_history'),
    
    # Agno智能体API
    path('api/agno/chat/', agno_views.agno_chat_api, name='agno_chat_api'),
    path('api/agno/health/', agno_views.agno_health_check, name='agno_health_check'),
    path('api/agno/reset/', agno_views.agno_reset_agent, name='agno_reset_agent'),
    
    # 用户认证API
    path('api/auth/login/', views.user_login, name='user_login'),
    path('api/auth/logout/', views.user_logout, name='user_logout'),
    path('api/auth/profile/', views.user_profile, name='user_profile'),
    
    # 前端页面
    path('chat/', views.chat_interface, name='chat_interface'),
    path('agno/', agno_views.agno_chat_page, name='agno_chat_page'),
    path('login/', views.login_page, name='login_page'),
    path('tokens/', views.user_token_dashboard, name='user_token_dashboard'),
    
    # 管理员仪表板
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('admin/api/alerts/', views.alerts_api, name='alerts_api'),
] 