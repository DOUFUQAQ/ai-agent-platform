from django.urls import path
from . import views

app_name = 'audit_system'

urlpatterns = [
    # 主要页面
    path('', views.dashboard, name='dashboard'),
    path('user-activity/', views.user_activity_logs, name='user_activity_logs'),
    path('admin-operations/', views.admin_operation_logs, name='admin_operation_logs'),
    path('login-logs/', views.login_logs, name='login_logs'),
]
