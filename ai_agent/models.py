from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AIModel(models.Model):
    """AI模型配置"""
    
    name = models.CharField(max_length=100, verbose_name='模型名称')
    model_id = models.CharField(max_length=100, unique=True, verbose_name='模型ID')
    provider = models.CharField(max_length=50, verbose_name='提供商')
    api_endpoint = models.URLField(verbose_name='API端点')
    max_tokens = models.IntegerField(default=4096, verbose_name='最大token数')
    temperature = models.FloatField(default=0.7, verbose_name='温度参数')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    cost_per_1k_input_tokens = models.DecimalField(
        max_digits=10, 
        decimal_places=6, 
        default=0,
        verbose_name='输入token成本（每1K）'
    )
    cost_per_1k_output_tokens = models.DecimalField(
        max_digits=10, 
        decimal_places=6, 
        default=0,
        verbose_name='输出token成本（每1K）'
    )
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = 'AI模型'
        verbose_name_plural = 'AI模型'
        db_table = 'ai_model'
    
    def __str__(self):
        return f"{self.name} ({self.provider})"


class AIFunction(models.Model):
    """AI功能定义"""
    
    FUNCTION_TYPE_CHOICES = [
        ('course_selection', '选课助手'),
        ('calendar', 'AI日历'),
        ('email', '邮件助手'),
        ('study_plan', '学业规划'),
        ('qa', '问答助手'),
        ('document', '文档处理'),
        ('translation', '翻译助手'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='功能名称')
    code = models.CharField(max_length=50, unique=True, verbose_name='功能代码')
    function_type = models.CharField(max_length=20, choices=FUNCTION_TYPE_CHOICES, verbose_name='功能类型')
    description = models.TextField(verbose_name='功能描述')
    prompt_template = models.TextField(verbose_name='提示词模板')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    requires_permission = models.BooleanField(default=True, verbose_name='是否需要权限')
    max_daily_usage = models.IntegerField(default=0, verbose_name='每日最大使用次数（0表示无限制）')
    
    # 模型配置
    preferred_model = models.ForeignKey(
        AIModel, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        verbose_name='首选模型'
    )
    custom_temperature = models.FloatField(blank=True, null=True, verbose_name='自定义温度参数')
    custom_max_tokens = models.IntegerField(blank=True, null=True, verbose_name='自定义最大token数')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = 'AI功能'
        verbose_name_plural = 'AI功能'
        db_table = 'ai_function'
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class APIUsageLog(models.Model):
    """API使用日志"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    model = models.ForeignKey(AIModel, on_delete=models.CASCADE, verbose_name='使用模型')
    function = models.ForeignKey(AIFunction, on_delete=models.CASCADE, verbose_name='使用功能')
    session_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='会话ID')
    
    # API调用信息
    input_tokens = models.IntegerField(verbose_name='输入token数')
    output_tokens = models.IntegerField(verbose_name='输出token数')
    total_tokens = models.IntegerField(verbose_name='总token数')
    response_time = models.FloatField(verbose_name='响应时间（秒）')
    cost = models.DecimalField(max_digits=10, decimal_places=6, verbose_name='费用')
    
    # 状态信息
    is_success = models.BooleanField(verbose_name='是否成功')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    
    # 请求信息
    request_data = models.TextField(blank=True, null=True, verbose_name='请求数据（JSON）')
    response_data = models.TextField(blank=True, null=True, verbose_name='响应数据（JSON）')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = 'API使用日志'
        verbose_name_plural = 'API使用日志'
        db_table = 'api_usage_log'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.function.name} - {self.created_at}"


class UserTokenUsage(models.Model):
    """用户Token使用统计"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    date = models.DateField(verbose_name='日期')
    
    # Token使用统计
    total_tokens = models.IntegerField(default=0, verbose_name='总Token数')
    input_tokens = models.IntegerField(default=0, verbose_name='输入Token数')
    output_tokens = models.IntegerField(default=0, verbose_name='输出Token数')
    
    # 使用次数统计
    session_count = models.IntegerField(default=0, verbose_name='会话数')
    message_count = models.IntegerField(default=0, verbose_name='消息数')
    
    # 成本统计
    total_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0, verbose_name='总成本')
    
    # 功能使用统计（JSON格式存储）
    function_usage = models.JSONField(default=dict, blank=True, verbose_name='功能使用统计')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户Token使用统计'
        verbose_name_plural = '用户Token使用统计'
        db_table = 'user_token_usage'
        unique_together = ['user', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.total_tokens} tokens"
