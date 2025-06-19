from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """扩展用户模型"""
    
    USER_TYPE_CHOICES = [
        ('admin', '管理员'),
        ('teacher', '教师'),
        ('student', '学生'),
    ]
    
    user_type = models.CharField(
        max_length=10, 
        choices=USER_TYPE_CHOICES, 
        default='student',
        verbose_name='用户类型'
    )
    phone = models.CharField(max_length=11, blank=True, null=True, verbose_name='手机号')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='头像')
    is_active_user = models.BooleanField(default=True, verbose_name='是否活跃用户')
    last_login_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name='最后登录IP')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        db_table = 'auth_user_extended'
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"


class StudentProfile(models.Model):
    """学生档案信息"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户')
    student_id = models.CharField(max_length=20, unique=True, verbose_name='学号')
    real_name = models.CharField(max_length=50, verbose_name='真实姓名')
    gender = models.CharField(
        max_length=10, 
        choices=[('M', '男'), ('F', '女')], 
        blank=True, 
        null=True,
        verbose_name='性别'
    )
    grade = models.CharField(max_length=10, blank=True, null=True, verbose_name='年级')
    major = models.CharField(max_length=100, blank=True, null=True, verbose_name='专业')
    class_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='班级')
    enrollment_year = models.IntegerField(blank=True, null=True, verbose_name='入学年份')
    graduation_year = models.IntegerField(blank=True, null=True, verbose_name='毕业年份')
    
    # 档案管理字段
    tags = models.TextField(blank=True, null=True, verbose_name='标签（JSON格式）')
    notes = models.TextField(blank=True, null=True, verbose_name='备注')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '学生档案'
        verbose_name_plural = '学生档案'
        db_table = 'student_profile'
    
    def __str__(self):
        return f"{self.real_name} ({self.student_id})"


class LoginLog(models.Model):
    """登录日志"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    login_time = models.DateTimeField(auto_now_add=True, verbose_name='登录时间')
    logout_time = models.DateTimeField(blank=True, null=True, verbose_name='登出时间')
    ip_address = models.GenericIPAddressField(verbose_name='IP地址')
    user_agent = models.TextField(blank=True, null=True, verbose_name='用户代理')
    login_status = models.CharField(
        max_length=10,
        choices=[('success', '成功'), ('failed', '失败')],
        default='success',
        verbose_name='登录状态'
    )
    
    class Meta:
        verbose_name = '登录日志'
        verbose_name_plural = '登录日志'
        db_table = 'login_log'
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"
