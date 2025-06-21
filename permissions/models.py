from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AIFunction(models.Model):
    """AI功能定义"""
    
    FUNCTION_TYPE_CHOICES = [
        ('qa', '通用问答'),
        ('course_selection', '选课助手'),
        ('calendar', '日历助手'),
        ('email', '邮件助手'),
        ('study_plan', '学业规划'),
        ('document', '文档助手'),
        ('translation', '翻译助手'),
    ]
    
    function_code = models.CharField(max_length=50, unique=True, verbose_name='功能代码')
    name = models.CharField(max_length=100, verbose_name='功能名称')
    description = models.TextField(blank=True, null=True, verbose_name='功能描述')
    function_type = models.CharField(max_length=20, choices=FUNCTION_TYPE_CHOICES, verbose_name='功能类型')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    is_beta = models.BooleanField(default=False, verbose_name='是否为测试功能')
    max_daily_usage = models.IntegerField(default=0, verbose_name='每日最大使用次数(0表示无限制)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = 'AI功能'
        verbose_name_plural = 'AI功能'
        db_table = 'permissions_ai_function'
    
    def __str__(self):
        return self.name


class StudentGroup(models.Model):
    """学生群组"""
    
    GROUP_TYPE_CHOICES = [
        ('grade', '年级'),
        ('class', '班级'),
        ('major', '专业'),
        ('custom', '自定义'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='群组名称')
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES, verbose_name='群组类型')
    description = models.TextField(blank=True, null=True, verbose_name='群组描述')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '学生群组'
        verbose_name_plural = '学生群组'
        db_table = 'student_group'
    
    def __str__(self):
        return f"{self.name} ({self.get_group_type_display()})"


class StudentGroupMembership(models.Model):
    """学生群组成员关系"""
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='学生')
    group = models.ForeignKey(StudentGroup, on_delete=models.CASCADE, verbose_name='群组')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='加入时间')
    
    class Meta:
        verbose_name = '群组成员'
        verbose_name_plural = '群组成员'
        db_table = 'student_group_membership'
        unique_together = ['student', 'group']
    
    def __str__(self):
        return f"{self.student.username} - {self.group.name}"


class StudentFunctionPermission(models.Model):
    """学生功能权限"""
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='学生')
    function = models.ForeignKey(AIFunction, on_delete=models.CASCADE, verbose_name='AI功能')
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    daily_quota = models.IntegerField(default=0, verbose_name='每日配额(0表示使用默认配额)')
    granted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='granted_permissions', verbose_name='授权者')
    granted_at = models.DateTimeField(auto_now_add=True, verbose_name='授权时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    expires_at = models.DateTimeField(blank=True, null=True, verbose_name='过期时间')
    
    class Meta:
        verbose_name = '学生功能权限'
        verbose_name_plural = '学生功能权限'
        db_table = 'student_function_permission'
        unique_together = ['student', 'function']
    
    def __str__(self):
        return f"{self.student.username} - {self.function.name} ({'启用' if self.is_enabled else '禁用'})"


class GroupFunctionPermission(models.Model):
    """群组功能权限"""
    
    group = models.ForeignKey(StudentGroup, on_delete=models.CASCADE, verbose_name='学生群组')
    function = models.ForeignKey(AIFunction, on_delete=models.CASCADE, verbose_name='AI功能')
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    daily_quota = models.IntegerField(default=0, verbose_name='每日配额(0表示使用默认配额)')
    granted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='granted_group_permissions', verbose_name='授权者')
    granted_at = models.DateTimeField(auto_now_add=True, verbose_name='授权时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    expires_at = models.DateTimeField(blank=True, null=True, verbose_name='过期时间')
    
    class Meta:
        verbose_name = '群组功能权限'
        verbose_name_plural = '群组功能权限'
        db_table = 'group_function_permission'
        unique_together = ['group', 'function']
    
    def __str__(self):
        return f"{self.group.name} - {self.function.name} ({'启用' if self.is_enabled else '禁用'})"


class FunctionToggleLog(models.Model):
    """功能开关变动日志"""
    
    OPERATION_TYPE_CHOICES = [
        ('enable', '启用'),
        ('disable', '禁用'),
        ('quota_change', '配额变更'),
        ('expire_set', '设置过期时间'),
        ('batch_operation', '批量操作'),
    ]
    
    TARGET_TYPE_CHOICES = [
        ('user', '单个用户'),
        ('group', '用户群组'),
        ('global', '全局设置'),
    ]
    
    function = models.ForeignKey(AIFunction, on_delete=models.CASCADE, verbose_name='AI功能')
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPE_CHOICES, verbose_name='操作类型')
    target_type = models.CharField(max_length=10, choices=TARGET_TYPE_CHOICES, verbose_name='目标类型')
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='function_changes', verbose_name='目标用户')
    target_group = models.ForeignKey(StudentGroup, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='目标群组')
    old_value = models.JSONField(blank=True, null=True, verbose_name='原值')
    new_value = models.JSONField(verbose_name='新值')
    reason = models.TextField(blank=True, null=True, verbose_name='变更原因')
    operated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='function_operations', verbose_name='操作者')
    operated_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')
    
    class Meta:
        verbose_name = '功能开关日志'
        verbose_name_plural = '功能开关日志'
        db_table = 'function_toggle_log'
        ordering = ['-operated_at']
    
    def __str__(self):
        return f"{self.function.name} - {self.get_operation_type_display()} - {self.operated_at.date()}"


class GrayReleaseConfig(models.Model):
    """灰度发布配置"""
    
    RELEASE_TYPE_CHOICES = [
        ('percentage', '按比例发布'),
        ('whitelist', '白名单发布'),
        ('group_based', '基于群组发布'),
        ('gradual', '逐步发布'),
    ]
    
    STATUS_CHOICES = [
        ('preparing', '准备中'),
        ('active', '进行中'),
        ('paused', '已暂停'),
        ('completed', '已完成'),
        ('rollback', '已回滚'),
    ]
    
    function = models.ForeignKey(AIFunction, on_delete=models.CASCADE, verbose_name='AI功能')
    release_name = models.CharField(max_length=100, verbose_name='发布名称')
    release_type = models.CharField(max_length=20, choices=RELEASE_TYPE_CHOICES, verbose_name='发布类型')
    target_percentage = models.IntegerField(default=0, verbose_name='目标百分比')
    current_percentage = models.IntegerField(default=0, verbose_name='当前百分比')
    target_groups = models.ManyToManyField(StudentGroup, blank=True, verbose_name='目标群组')
    whitelist_users = models.ManyToManyField(User, blank=True, related_name='gray_release_whitelist', verbose_name='白名单用户')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='preparing', verbose_name='状态')
    start_time = models.DateTimeField(blank=True, null=True, verbose_name='开始时间')
    end_time = models.DateTimeField(blank=True, null=True, verbose_name='结束时间')
    rollback_plan = models.TextField(blank=True, null=True, verbose_name='回滚计划')
    success_criteria = models.JSONField(default=dict, verbose_name='成功标准')
    monitoring_metrics = models.JSONField(default=dict, verbose_name='监控指标')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_gray_releases', verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '灰度发布配置'
        verbose_name_plural = '灰度发布配置'
        db_table = 'gray_release_config'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.function.name} - {self.release_name}"


class PermissionAuditLog(models.Model):
    """权限审计日志"""
    
    AUDIT_TYPE_CHOICES = [
        ('permission_grant', '权限授予'),
        ('permission_revoke', '权限撤销'),
        ('group_assignment', '群组分配'),
        ('group_removal', '群组移除'),
        ('quota_adjustment', '配额调整'),
        ('gray_release', '灰度发布'),
    ]
    
    audit_type = models.CharField(max_length=30, choices=AUDIT_TYPE_CHOICES, verbose_name='审计类型')
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='permission_audits', verbose_name='目标用户')
    target_group = models.ForeignKey(StudentGroup, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='目标群组')
    function = models.ForeignKey(AIFunction, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='相关功能')
    operation_detail = models.JSONField(verbose_name='操作详情')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')
    user_agent = models.TextField(blank=True, null=True, verbose_name='用户代理')
    operated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permission_operations', verbose_name='操作者')
    operated_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')
    
    class Meta:
        verbose_name = '权限审计日志'
        verbose_name_plural = '权限审计日志'
        db_table = 'permission_audit_log'
        ordering = ['-operated_at']
    
    def __str__(self):
        return f"{self.get_audit_type_display()} - {self.operated_by.username} - {self.operated_at.date()}"
