from django.contrib import admin
from .models import AIModel, AIFunction, APIUsageLog, UserTokenUsage

@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'model_id', 'provider', 'is_active', 'created_at']
    list_filter = ['provider', 'is_active', 'created_at']
    search_fields = ['name', 'model_id', 'provider']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'model_id', 'provider', 'api_endpoint', 'description')
        }),
        ('配置参数', {
            'fields': ('max_tokens', 'temperature', 'is_active')
        }),
        ('成本配置', {
            'fields': ('cost_per_1k_input_tokens', 'cost_per_1k_output_tokens')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(AIFunction)
class AIFunctionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'function_type', 'is_active', 'requires_permission', 'created_at']
    list_filter = ['function_type', 'is_active', 'requires_permission', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'code', 'function_type', 'description')
        }),
        ('权限配置', {
            'fields': ('is_active', 'requires_permission', 'max_daily_usage')
        }),
        ('模型配置', {
            'fields': ('preferred_model', 'custom_temperature', 'custom_max_tokens'),
            'classes': ('collapse',)
        }),
        ('提示词', {
            'fields': ('prompt_template',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(APIUsageLog)
class APIUsageLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'function', 'model', 'total_tokens', 'cost', 'is_success', 'created_at']
    list_filter = ['is_success', 'model', 'function', 'created_at']
    search_fields = ['user__username', 'session_id']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'model', 'function', 'session_id')
        }),
        ('Token使用', {
            'fields': ('input_tokens', 'output_tokens', 'total_tokens', 'cost')
        }),
        ('执行信息', {
            'fields': ('response_time', 'is_success', 'error_message')
        }),
        ('详细数据', {
            'fields': ('request_data', 'response_data'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at',)
        }),
    )

@admin.register(UserTokenUsage)
class UserTokenUsageAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'total_tokens', 'session_count', 'message_count', 'total_cost']
    list_filter = ['date', 'user__user_type']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'date')
        }),
        ('Token统计', {
            'fields': ('total_tokens', 'input_tokens', 'output_tokens', 'total_cost')
        }),
        ('使用统计', {
            'fields': ('session_count', 'message_count')
        }),
        ('功能使用', {
            'fields': ('function_usage',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    # 添加统计信息
    def changelist_view(self, request, extra_context=None):
        from django.db.models import Sum, Count
        
        # 计算统计信息
        total_records = self.get_queryset(request).count()
        total_tokens = self.get_queryset(request).aggregate(
            total=Sum('total_tokens')
        )['total'] or 0
        total_users = self.get_queryset(request).values('user').distinct().count()
        
        extra_context = extra_context or {}
        extra_context['total_records'] = total_records
        extra_context['total_tokens'] = total_tokens
        extra_context['total_users'] = total_users
        
        return super().changelist_view(request, extra_context=extra_context)
