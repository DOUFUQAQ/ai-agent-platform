from django.urls import path
from . import views

app_name = 'student_management'

urlpatterns = [
    # 主要页面
    path('', views.dashboard, name='dashboard'),
    path('students/', views.students_list, name='students_list'),
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),
    path('students/<int:student_id>/history/', views.student_usage_history, name='student_usage_history'),
    path('tags/', views.tags_management, name='tags_management'),
    
    # 标签管理API
    path('tags/create/', views.create_tag, name='create_tag'),
    path('tags/<int:tag_id>/update/', views.update_tag, name='update_tag'),
    path('tags/<int:tag_id>/delete/', views.delete_tag, name='delete_tag'),
    
    # API接口
    path('api/assign-tag/', views.assign_tag_api, name='assign_tag_api'),
    path('api/remove-tag/', views.remove_tag_api, name='remove_tag_api'),
    path('api/create-tag/', views.create_tag_api, name='create_tag_api'),
    path('api/create-note/', views.create_note_api, name='create_note_api'),
    path('api/update-note/', views.update_note_api, name='update_note_api'),
    path('api/delete-note/', views.delete_note_api, name='delete_note_api'),
    path('api/toggle-student-status/', views.toggle_student_status_api, name='toggle_student_status_api'),
    path('api/export-student-data/<int:student_id>/', views.export_student_data, name='export_student_data'),
    path('api/export-all/', views.export_all_students_data, name='export_all_students_data'),
] 