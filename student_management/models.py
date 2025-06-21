from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class StudentTag(models.Model):
    """学生标签"""
    
    TAG_TYPE_CHOICES = [
        ('attention', '需要关注'),
        ('active', '高活跃'),
        ('feedback', '反馈频繁'),
        ('excellent', '优秀学生'),
        ('custom', '自定义'),
    ]
    
    name = models.CharField(max_length=50, unique=True, verbose_name='标签名称')
    tag_type = models.CharField(max_length=20, choices=TAG_TYPE_CHOICES, verbose_name='标签类型')
    color = models.CharField(max_length=7, default='#007bff', verbose_name='标签颜色')
    description = models.TextField(blank=True, null=True, verbose_name='标签描述')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tags', verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '学生标签'
        verbose_name_plural = '学生标签'
        db_table = 'student_tag'
    
    def __str__(self):
        return self.name


class StudentTagAssignment(models.Model):
    """学生标签分配"""
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tag_assignments', verbose_name='学生')
    tag = models.ForeignKey(StudentTag, on_delete=models.CASCADE, verbose_name='标签')
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_tags', verbose_name='分配者')
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='分配时间')
    
    class Meta:
        verbose_name = '学生标签分配'
        verbose_name_plural = '学生标签分配'
        db_table = 'student_tag_assignment'
        unique_together = ['student', 'tag']
    
    def __str__(self):
        return f"{self.student.username} - {self.tag.name}"


class StudentNote(models.Model):
    """学生备注"""
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_notes', verbose_name='学生')
    title = models.CharField(max_length=200, verbose_name='备注标题')
    content = models.TextField(verbose_name='备注内容')
    is_important = models.BooleanField(default=False, verbose_name='是否重要')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_notes', verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '学生备注'
        verbose_name_plural = '学生备注'
        db_table = 'student_note'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.title}"


class StudentUsageStatistics(models.Model):
    """学生使用统计"""
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usage_statistics', verbose_name='学生')
    date = models.DateField(verbose_name='统计日期')
    total_sessions = models.IntegerField(default=0, verbose_name='总会话数')
    total_messages = models.IntegerField(default=0, verbose_name='总消息数')
    total_duration_minutes = models.IntegerField(default=0, verbose_name='总使用时长(分钟)')
    functions_used = models.JSONField(default=dict, verbose_name='使用的功能统计')  # {"qa": 10, "calendar": 5}
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '学生使用统计'
        verbose_name_plural = '学生使用统计'
        db_table = 'student_usage_statistics'
        unique_together = ['student', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.student.username} - {self.date}"
