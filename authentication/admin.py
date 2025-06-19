from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, StudentProfile, LoginLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """用户管理"""
    
    list_display = ('username', 'email', 'user_type', 'is_active', 'created_at')
    list_filter = ('user_type', 'is_active', 'is_staff', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        (_('扩展信息'), {
            'fields': ('user_type', 'phone', 'avatar', 'is_active_user', 'last_login_ip')
        }),
        (_('时间信息'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login_ip')
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_('扩展信息'), {
            'fields': ('user_type', 'phone', 'email')
        }),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """学生档案管理"""
    
    list_display = ('student_id', 'real_name', 'grade', 'major', 'class_name', 'created_at')
    list_filter = ('grade', 'major', 'gender', 'enrollment_year')
    search_fields = ('student_id', 'real_name', 'user__username')
    ordering = ('-created_at',)
    
    fieldsets = (
        (_('基本信息'), {
            'fields': ('user', 'student_id', 'real_name', 'gender')
        }),
        (_('学籍信息'), {
            'fields': ('grade', 'major', 'class_name', 'enrollment_year', 'graduation_year')
        }),
        (_('档案管理'), {
            'fields': ('tags', 'notes'),
            'classes': ('collapse',)
        }),
        (_('时间信息'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    """登录日志管理"""
    
    list_display = ('user', 'login_time', 'logout_time', 'ip_address', 'login_status')
    list_filter = ('login_status', 'login_time')
    search_fields = ('user__username', 'ip_address')
    ordering = ('-login_time',)
    
    readonly_fields = ('user', 'login_time', 'logout_time', 'ip_address', 'user_agent', 'login_status')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
