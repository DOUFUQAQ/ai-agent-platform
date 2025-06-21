from django.contrib import admin
from .models import (
    AIFunction, StudentGroup, StudentGroupMembership, StudentFunctionPermission,
    GroupFunctionPermission, FunctionToggleLog, GrayReleaseConfig, PermissionAuditLog
)


@admin.register(AIFunction)
class AIFunctionAdmin(admin.ModelAdmin):
    list_display = ['function_code', 'name', 'function_type', 'is_active', 'is_beta', 'max_daily_usage']
    list_filter = ['function_type', 'is_active', 'is_beta', 'created_at']
    search_fields = ['function_code', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('function_code', 'name', 'description', 'function_type')
        }),
        ('配置', {
            'fields': ('is_active', 'is_beta', 'max_daily_usage')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StudentGroup)
class StudentGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'group_type', 'is_active', 'created_by', 'created_at']
    list_filter = ['group_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'group_type', 'description', 'is_active')
        }),
        ('创建信息', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StudentGroupMembership)
class StudentGroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['student', 'group', 'joined_at']
    list_filter = ['group', 'joined_at']
    search_fields = ['student__username', 'student__first_name', 'student__last_name', 'group__name']
    readonly_fields = ['joined_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'group')


@admin.register(StudentFunctionPermission)
class StudentFunctionPermissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'function', 'is_enabled', 'daily_quota', 'granted_by', 'expires_at']
    list_filter = ['function', 'is_enabled', 'granted_at', 'expires_at']
    search_fields = ['student__username', 'function__name']
    readonly_fields = ['granted_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('student', 'function', 'is_enabled', 'daily_quota', 'expires_at')
        }),
        ('授权信息', {
            'fields': ('granted_by', 'granted_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'function', 'granted_by')


@admin.register(GroupFunctionPermission)
class GroupFunctionPermissionAdmin(admin.ModelAdmin):
    list_display = ['group', 'function', 'is_enabled', 'daily_quota', 'granted_by', 'expires_at']
    list_filter = ['function', 'is_enabled', 'granted_at', 'expires_at']
    search_fields = ['group__name', 'function__name']
    readonly_fields = ['granted_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('group', 'function', 'is_enabled', 'daily_quota', 'expires_at')
        }),
        ('授权信息', {
            'fields': ('granted_by', 'granted_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('group', 'function', 'granted_by')


@admin.register(FunctionToggleLog)
class FunctionToggleLogAdmin(admin.ModelAdmin):
    list_display = ['function', 'operation_type', 'target_type', 'target_user', 'operated_by', 'operated_at']
    list_filter = ['operation_type', 'target_type', 'operated_at']
    search_fields = ['function__name', 'target_user__username', 'reason']
    readonly_fields = ['operated_at']
    date_hierarchy = 'operated_at'
    
    fieldsets = (
        ('操作信息', {
            'fields': ('function', 'operation_type', 'target_type', 'target_user', 'target_group')
        }),
        ('变更内容', {
            'fields': ('old_value', 'new_value', 'reason')
        }),
        ('操作者信息', {
            'fields': ('operated_by', 'operated_at')
        }),
    )


@admin.register(GrayReleaseConfig)
class GrayReleaseConfigAdmin(admin.ModelAdmin):
    list_display = ['function', 'release_name', 'release_type', 'current_percentage', 'status', 'created_at']
    list_filter = ['release_type', 'status', 'created_at']
    search_fields = ['function__name', 'release_name']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['target_groups', 'whitelist_users']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('function', 'release_name', 'release_type', 'status')
        }),
        ('发布配置', {
            'fields': ('target_percentage', 'current_percentage', 'target_groups', 'whitelist_users')
        }),
        ('时间配置', {
            'fields': ('start_time', 'end_time')
        }),
        ('计划与标准', {
            'fields': ('rollback_plan', 'success_criteria', 'monitoring_metrics'),
            'classes': ('collapse',)
        }),
        ('创建信息', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PermissionAuditLog)
class PermissionAuditLogAdmin(admin.ModelAdmin):
    list_display = ['audit_type', 'operated_by', 'target_user', 'function', 'operated_at']
    list_filter = ['audit_type', 'operated_at']
    search_fields = ['operated_by__username', 'target_user__username', 'function__name']
    readonly_fields = ['operated_at']
    date_hierarchy = 'operated_at'
    
    fieldsets = (
        ('审计信息', {
            'fields': ('audit_type', 'target_user', 'target_group', 'function', 'operation_detail')
        }),
        ('操作者信息', {
            'fields': ('operated_by', 'operated_at')
        }),
        ('技术信息', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
