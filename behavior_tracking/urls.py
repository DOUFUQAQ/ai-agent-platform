from django.urls import path
from . import views

app_name = 'behavior_tracking'
 
urlpatterns = [
    # 主要页面
    path('', views.behavior_dashboard, name='dashboard'),
    path('dashboard/', views.behavior_dashboard, name='dashboard'),
    
    # 用户行为相关
    path('users/', views.user_behavior_list, name='user_list'),
    path('users/<int:user_id>/', views.user_behavior_detail, name='user_detail'),
    
    # 会话详情
    path('sessions/<str:session_id>/', views.session_detail, name='session_detail'),
    
    # 异常行为管理
    path('abnormal/', views.abnormal_behavior_management, name='abnormal_management'),
    
    # 敏感内容管理
    path('sensitive/', views.sensitive_content_management, name='sensitive_management'),
    
    # 功能使用分析
    path('analytics/', views.function_usage_analytics, name='function_analytics'),
    
    # API接口
    path('api/handle-abnormal/', views.handle_abnormal_behavior, name='handle_abnormal'),
    path('api/review-sensitive/', views.review_sensitive_content, name='review_sensitive'),
    path('api/run-detection/', views.run_behavior_detection, name='run_detection'),
    
    # 数据导出
    path('export/', views.export_behavior_data, name='export_data'),
] 