from django.urls import path
from . import views, function_views

app_name = 'permissions'

urlpatterns = [
    # 功能管理
    path('functions/', views.function_management, name='function_management'),
    path('functions/create/', views.create_function, name='create_function'),
    path('functions/<int:function_id>/update/', views.update_function, name='update_function'),
    path('functions/<int:function_id>/toggle/', views.toggle_function_status, name='toggle_function_status'),
    path('functions/<int:function_id>/delete/', views.delete_function, name='delete_function'),
    path('functions/<int:function_id>/permissions/', views.function_permissions_detail, name='function_permissions_detail'),
    
    # 学生权限管理
    path('students/', views.student_permission_management, name='student_permission_management'),
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),
    
    # 群组管理
    path('groups/', views.group_management, name='group_management'),
    
    # 功能开关管理
    path('toggle/', function_views.function_toggle_dashboard, name='function_toggle_dashboard'),
    path('toggle/permissions/', function_views.function_permission_management, name='function_permission_management'),
    
    # API 接口
    path('api/toggle-function/', views.toggle_student_function, name='toggle_student_function'),
    path('api/batch-toggle/', views.batch_toggle_function, name='batch_toggle_function'),
    path('api/create-group/', views.create_student_group, name='create_student_group'),
    
    # 功能开关API
    path('api/toggle-user-function/', function_views.toggle_user_function_api, name='toggle_user_function_api'),
    path('api/create-gray-release/', function_views.create_gray_release_api, name='create_gray_release_api'),
    
    # 数据分析
    path('analytics/', views.usage_analytics, name='usage_analytics'),
] 