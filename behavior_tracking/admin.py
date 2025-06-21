from django.contrib import admin
from .models import (
    ChatSession, ChatMessage, UserBehaviorLog, AdminOperationLog,
    SensitiveWordDetection, AbnormalBehaviorDetection, FunctionUsageStatistics
)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'function_code', 'message_count', 'started_at', 'is_active']
    list_filter = ['function_code', 'is_active', 'started_at']
    search_fields = ['session_id', 'user__username', 'title']
    readonly_fields = ['session_id', 'started_at', 'duration']
    date_hierarchy = 'started_at'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('session_id', 'user', 'title', 'function_code')
        }),
        ('统计信息', {
            'fields': ('message_count', 'total_tokens', 'is_active')
        }),
        ('时间信息', {
            'fields': ('started_at', 'ended_at', 'duration')
        }),
        ('技术信息', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'message_type', 'function_called', 'tokens_used', 'is_flagged', 'created_at']
    list_filter = ['message_type', 'function_called', 'model_type', 'is_flagged', 'created_at']
    search_fields = ['session__session_id', 'content', 'session__user__username']
    readonly_fields = ['created_at', 'response_time']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('session', 'message_type', 'content')
        }),
        ('功能信息', {
            'fields': ('function_called', 'model_type', 'tokens_used', 'response_time')
        }),
        ('审计信息', {
            'fields': ('is_flagged', 'flag_reason', 'reviewed_by', 'reviewed_at'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at',)
        }),
    )


@admin.register(UserBehaviorLog)
class UserBehaviorLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action_type', 'session_id', 'ip_address', 'created_at']
    list_filter = ['action_type', 'created_at']
    search_fields = ['user__username', 'action_detail', 'session_id']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(AdminOperationLog)
class AdminOperationLogAdmin(admin.ModelAdmin):
    list_display = ['admin_user', 'operation_type', 'target_user', 'result', 'created_at']
    list_filter = ['operation_type', 'result', 'created_at']
    search_fields = ['admin_user__username', 'target_user__username', 'operation_detail']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('操作信息', {
            'fields': ('admin_user', 'operation_type', 'operation_detail', 'target_user', 'result')
        }),
        ('技术信息', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at',)
        }),
    )


@admin.register(SensitiveWordDetection)
class SensitiveWordDetectionAdmin(admin.ModelAdmin):
    list_display = ['message', 'detection_type', 'severity', 'is_reviewed', 'created_at']
    list_filter = ['detection_type', 'severity', 'is_reviewed', 'created_at']
    search_fields = ['message__content', 'context', 'matched_words']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('检测信息', {
            'fields': ('message', 'detection_type', 'matched_words', 'severity', 'context')
        }),
        ('审查信息', {
            'fields': ('is_reviewed', 'reviewed_by', 'reviewed_at', 'action_taken')
        }),
        ('时间信息', {
            'fields': ('created_at',)
        }),
    )


@admin.register(AbnormalBehaviorDetection)
class AbnormalBehaviorDetectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'behavior_type', 'risk_score', 'is_confirmed', 'is_handled', 'created_at']
    list_filter = ['behavior_type', 'is_confirmed', 'is_handled', 'created_at']
    search_fields = ['user__username', 'description']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('检测信息', {
            'fields': ('user', 'behavior_type', 'description', 'detection_data', 'risk_score')
        }),
        ('处理信息', {
            'fields': ('is_confirmed', 'is_handled', 'handled_by', 'handled_at', 'action_taken')
        }),
        ('时间信息', {
            'fields': ('created_at',)
        }),
    )


@admin.register(FunctionUsageStatistics)
class FunctionUsageStatisticsAdmin(admin.ModelAdmin):
    list_display = ['function_code', 'period_type', 'period_start', 'total_calls', 'unique_users', 'success_rate']
    list_filter = ['function_code', 'period_type', 'period_start']
    search_fields = ['function_code']
    readonly_fields = ['created_at']
    date_hierarchy = 'period_start'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('function_code', 'period_type', 'period_start', 'period_end')
        }),
        ('使用统计', {
            'fields': ('total_calls', 'unique_users', 'total_duration', 'average_response_time')
        }),
        ('质量指标', {
            'fields': ('success_rate', 'user_satisfaction')
        }),
        ('时间信息', {
            'fields': ('created_at',)
        }),
    )
