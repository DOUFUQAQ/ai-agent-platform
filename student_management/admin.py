from django.contrib import admin
from .models import StudentTag, StudentTagAssignment, StudentNote, StudentUsageStatistics


@admin.register(StudentTag)
class StudentTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'tag_type', 'color', 'is_active', 'created_by', 'created_at']
    list_filter = ['tag_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'tag_type', 'color', 'description')
        }),
        ('状态', {
            'fields': ('is_active',)
        }),
        ('创建信息', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StudentTagAssignment)
class StudentTagAssignmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'tag', 'assigned_by', 'assigned_at']
    list_filter = ['tag', 'assigned_at', 'assigned_by']
    search_fields = ['student__username', 'student__first_name', 'student__last_name', 'tag__name']
    readonly_fields = ['assigned_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'tag', 'assigned_by')


@admin.register(StudentNote)
class StudentNoteAdmin(admin.ModelAdmin):
    list_display = ['student', 'title', 'is_important', 'created_by', 'created_at']
    list_filter = ['is_important', 'created_at', 'created_by']
    search_fields = ['student__username', 'title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('student', 'title', 'content', 'is_important')
        }),
        ('创建信息', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'created_by')


@admin.register(StudentUsageStatistics)
class StudentUsageStatisticsAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'total_sessions', 'total_messages', 'total_duration_minutes']
    list_filter = ['date', 'created_at']
    search_fields = ['student__username', 'student__first_name', 'student__last_name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('student', 'date')
        }),
        ('使用统计', {
            'fields': ('total_sessions', 'total_messages', 'total_duration_minutes', 'functions_used')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student')
