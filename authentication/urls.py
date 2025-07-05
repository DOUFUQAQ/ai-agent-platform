from django.urls import path
from . import views, admin_views

app_name = 'authentication'

urlpatterns = [
    # 认证相关
    path('login/', views.login_page, name='login'),
    path('api/login/', views.login_api, name='login_api'),
    path('api/register/', views.register_api, name='register_api'),
    path('logout/', views.logout_view, name='logout'),
    
    # 管理员后台
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', admin_views.user_management, name='user_management'),
    path('admin/users/<int:user_id>/', admin_views.user_detail, name='user_detail'),
    path('admin/logs/login/', admin_views.login_logs, name='login_logs'),
    path('admin/logs/permission/', admin_views.permission_audit_logs, name='permission_audit_logs'),
    path('admin/settings/', admin_views.system_settings, name='system_settings'),
    
    # API接口
    path('api/toggle-user-status/', admin_views.toggle_user_status, name='toggle_user_status'),
    path('api/reset-password/', admin_views.reset_user_password, name='reset_user_password'),
    
    # 用户操作API（前端使用的路径）
    path('admin/users/<int:user_id>/toggle/', admin_views.toggle_user_status, name='user_toggle'),
    path('admin/users/<int:user_id>/reset-password/', admin_views.reset_user_password, name='user_reset_password'),
] 