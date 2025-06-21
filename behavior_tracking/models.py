from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatSession(models.Model):
    """AI对话会话"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    session_id = models.CharField(max_length=100, unique=True, verbose_name='会话ID')
    title = models.CharField(max_length=200, blank=True, null=True, verbose_name='会话标题')
    function_code = models.CharField(max_length=50, blank=True, null=True, verbose_name='功能代码')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    ended_at = models.DateTimeField(blank=True, null=True, verbose_name='结束时间')
    message_count = models.IntegerField(default=0, verbose_name='消息数量')
    total_tokens = models.IntegerField(default=0, verbose_name='总token数')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')
    user_agent = models.TextField(blank=True, null=True, verbose_name='用户代理')
    
    class Meta:
        verbose_name = 'AI对话会话'
        verbose_name_plural = 'AI对话会话'
        db_table = 'chat_session'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.session_id}"
    
    @property
    def duration(self):
        """会话持续时间（分钟）"""
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at).total_seconds() / 60
        return None


class ChatMessage(models.Model):
    """对话消息记录"""
    
    MESSAGE_TYPE_CHOICES = [
        ('user', '用户消息'),
        ('assistant', 'AI回复'),
        ('system', '系统消息'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, verbose_name='会话')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, verbose_name='消息类型')
    content = models.TextField(verbose_name='消息内容')
    tokens_used = models.IntegerField(default=0, verbose_name='使用token数')
    function_called = models.CharField(max_length=100, blank=True, null=True, verbose_name='调用功能')
    model_type = models.CharField(max_length=50, default='chat', verbose_name='模型类型')
    response_time = models.FloatField(default=0, verbose_name='响应时间(秒)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    # 审计相关字段
    is_flagged = models.BooleanField(default=False, verbose_name='是否标记')
    flag_reason = models.CharField(max_length=200, blank=True, null=True, verbose_name='标记原因')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='reviewed_messages', verbose_name='审核者')
    reviewed_at = models.DateTimeField(blank=True, null=True, verbose_name='审核时间')
    
    class Meta:
        verbose_name = '对话消息'
        verbose_name_plural = '对话消息'
        db_table = 'chat_message'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.session.session_id} - {self.get_message_type_display()}"


class UserBehaviorLog(models.Model):
    """用户行为日志"""
    
    ACTION_TYPE_CHOICES = [
        ('login', '登录'),
        ('logout', '登出'),
        ('chat_start', '开始对话'),
        ('chat_end', '结束对话'),
        ('function_call', '功能调用'),
        ('file_upload', '文件上传'),
        ('data_export', '数据导出'),
        ('permission_change', '权限变更'),
        ('profile_update', '档案更新'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES, verbose_name='行为类型')
    action_detail = models.TextField(blank=True, null=True, verbose_name='行为详情')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')
    user_agent = models.TextField(blank=True, null=True, verbose_name='用户代理')
    session_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='会话ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '用户行为日志'
        verbose_name_plural = '用户行为日志'
        db_table = 'user_behavior_log'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()}"


class AdminOperationLog(models.Model):
    """管理员操作日志"""
    
    OPERATION_TYPE_CHOICES = [
        ('login', '登录登出'),
        ('user_management', '用户管理'),
        ('permission_management', '权限管理'),
        ('function_management', '功能管理'),
        ('data_export', '数据导出'),
        ('system_config', '系统配置'),
        ('audit_review', '审计审查'),
    ]
    
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='管理员')
    operation_type = models.CharField(max_length=30, choices=OPERATION_TYPE_CHOICES, verbose_name='操作类型')
    operation_detail = models.TextField(verbose_name='操作详情')
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='admin_operations', verbose_name='目标用户')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')
    user_agent = models.TextField(blank=True, null=True, verbose_name='用户代理')
    result = models.CharField(max_length=20, default='success', verbose_name='操作结果')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')
    
    class Meta:
        verbose_name = '管理员操作日志'
        verbose_name_plural = '管理员操作日志'
        db_table = 'admin_operation_log'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.admin_user.username} - {self.get_operation_type_display()}"


class SensitiveWordDetection(models.Model):
    """敏感词检测记录"""
    
    DETECTION_TYPE_CHOICES = [
        ('inappropriate', '不当言语'),
        ('cheating', '作弊尝试'),
        ('violation', '违规行为'),
        ('spam', '垃圾信息'),
        ('custom', '自定义规则'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '严重'),
    ]
    
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, verbose_name='相关消息')
    detection_type = models.CharField(max_length=20, choices=DETECTION_TYPE_CHOICES, verbose_name='检测类型')
    matched_words = models.JSONField(verbose_name='匹配的敏感词')  # ["词1", "词2"]
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, verbose_name='严重程度')
    context = models.TextField(verbose_name='上下文内容')
    is_reviewed = models.BooleanField(default=False, verbose_name='是否已审查')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='reviewed_detections', verbose_name='审查者')
    reviewed_at = models.DateTimeField(blank=True, null=True, verbose_name='审查时间')
    action_taken = models.CharField(max_length=200, blank=True, null=True, verbose_name='采取的措施')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='检测时间')
    
    class Meta:
        verbose_name = '敏感词检测'
        verbose_name_plural = '敏感词检测'
        db_table = 'sensitive_word_detection'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.message.session.user.username} - {self.get_detection_type_display()}"


class AbnormalBehaviorDetection(models.Model):
    """异常行为检测记录"""
    
    BEHAVIOR_TYPE_CHOICES = [
        ('high_frequency', '高频调用'),
        ('unusual_time', '异常时段使用'),
        ('suspicious_pattern', '可疑模式'),
        ('resource_abuse', '资源滥用'),
        ('account_sharing', '疑似账号共享'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    behavior_type = models.CharField(max_length=30, choices=BEHAVIOR_TYPE_CHOICES, verbose_name='行为类型')
    description = models.TextField(verbose_name='行为描述')
    detection_data = models.JSONField(verbose_name='检测数据')  # 存储具体的检测指标
    risk_score = models.IntegerField(verbose_name='风险评分')  # 1-100
    is_confirmed = models.BooleanField(default=False, verbose_name='是否确认异常')
    is_handled = models.BooleanField(default=False, verbose_name='是否已处理')
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='handled_behaviors', verbose_name='处理者')
    handled_at = models.DateTimeField(blank=True, null=True, verbose_name='处理时间')
    action_taken = models.TextField(blank=True, null=True, verbose_name='处理措施')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='检测时间')
    
    class Meta:
        verbose_name = '异常行为检测'
        verbose_name_plural = '异常行为检测'
        db_table = 'abnormal_behavior_detection'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_behavior_type_display()}"


class FunctionUsageStatistics(models.Model):
    """功能使用统计"""
    
    PERIOD_TYPE_CHOICES = [
        ('daily', '日统计'),
        ('weekly', '周统计'),
        ('monthly', '月统计'),
    ]
    
    function_code = models.CharField(max_length=50, verbose_name='功能代码')
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPE_CHOICES, verbose_name='统计周期')
    period_start = models.DateTimeField(verbose_name='统计开始时间')
    period_end = models.DateTimeField(verbose_name='统计结束时间')
    total_calls = models.IntegerField(default=0, verbose_name='总调用次数')
    unique_users = models.IntegerField(default=0, verbose_name='独立用户数')
    total_duration = models.IntegerField(default=0, verbose_name='总使用时长(分钟)')
    average_response_time = models.FloatField(default=0, verbose_name='平均响应时间(秒)')
    success_rate = models.FloatField(default=0, verbose_name='成功率')
    user_satisfaction = models.FloatField(default=0, verbose_name='用户满意度')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '功能使用统计'
        verbose_name_plural = '功能使用统计'
        db_table = 'function_usage_statistics'
        unique_together = ['function_code', 'period_type', 'period_start']
        ordering = ['-period_start']
    
    def __str__(self):
        return f"{self.function_code} - {self.get_period_type_display()} - {self.period_start.date()}"
