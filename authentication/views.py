from django.shortcuts import render, redirect
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
import json
import re


def login_page(request):
    """登录页面"""
    if request.user.is_authenticated:
        return redirect('/ai_agent/chat/')
    return render(request, 'authentication/login.html')


@require_http_methods(["POST"])
def login_api(request):
    """登录API - 处理登录请求"""
    username = request.POST.get('username')
    password = request.POST.get('password')
    
    if not username or not password:
        return render(request, 'authentication/login.html', {
            'error': '用户名和密码不能为空'
        })
    
    # 验证用户
    user = authenticate(request, username=username, password=password)
    if user:
        if user.is_active:
            login(request, user)
            
            # 记录登录日志（如果有LoginLog模型）
            try:
                from .models import LoginLog
                LoginLog.objects.create(
                    user=user,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    login_status='success'
                )
            except ImportError:
                pass  # 如果没有LoginLog模型就跳过
            
            # 登录成功，重定向到聊天页面
            return redirect('/ai_agent/chat/')
        else:
            return render(request, 'authentication/login.html', {
                'error': '账户已被禁用'
            })
    else:
        return render(request, 'authentication/login.html', {
            'error': '用户名或密码错误'
        })


@require_http_methods(["POST"])
def register_api(request):
    """注册API - 处理注册请求"""
    from .models import User, StudentProfile
    
    # 获取表单数据
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')
    password_confirm = request.POST.get('password_confirm', '')
    user_type = request.POST.get('user_type', '')
    
    # 学生专用字段
    student_id = request.POST.get('student_id', '').strip()
    real_name = request.POST.get('real_name', '').strip()
    major = request.POST.get('major', '').strip()
    
    # 基础验证
    if not all([username, email, password, password_confirm, user_type]):
        return render(request, 'authentication/login.html', {
            'register_error': '请填写所有必填字段'
        })
    
    # 验证用户名格式
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return render(request, 'authentication/login.html', {
            'register_error': '用户名只能包含字母、数字和下划线，长度3-20位'
        })
    
    # 验证身份类型
    if user_type not in ['student', 'teacher']:
        return render(request, 'authentication/login.html', {
            'register_error': '请选择正确的身份类型（学生或教师）'
        })
    
    # 验证密码
    if password != password_confirm:
        return render(request, 'authentication/login.html', {
            'register_error': '两次输入的密码不一致'
        })
    
    if len(password) < 6:
        return render(request, 'authentication/login.html', {
            'register_error': '密码长度至少6位'
        })
    
    # 如果是学生，验证学生专用字段
    if user_type == 'student':
        if not student_id or not real_name:
            return render(request, 'authentication/login.html', {
                'register_error': '学生用户必须填写学号和真实姓名'
            })
        
        if not re.match(r'^[a-zA-Z0-9]{6,20}$', student_id):
            return render(request, 'authentication/login.html', {
                'register_error': '学号格式不正确，应为6-20位字母数字组合'
            })
    
    # 检查用户名是否已存在
    if User.objects.filter(username=username).exists():
        return render(request, 'authentication/login.html', {
            'register_error': '用户名已存在，请选择其他用户名'
        })
    
    # 检查邮箱是否已存在
    if User.objects.filter(email=email).exists():
        return render(request, 'authentication/login.html', {
            'register_error': '邮箱已被注册，请使用其他邮箱'
        })
    
    # 如果是学生，检查学号是否已存在
    if user_type == 'student' and StudentProfile.objects.filter(student_id=student_id).exists():
        return render(request, 'authentication/login.html', {
            'register_error': '学号已存在，请检查后重新输入'
        })
    
    try:
        with transaction.atomic():
            # 创建用户
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type=user_type,
                is_active=True
            )
            
            # 如果是学生，创建学生档案
            if user_type == 'student':
                StudentProfile.objects.create(
                    user=user,
                    student_id=student_id,
                    real_name=real_name,
                    major=major or ''
                )
            
            # 记录注册日志
            try:
                from .models import LoginLog
                LoginLog.objects.create(
                    user=user,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    login_status='success'
                )
            except ImportError:
                pass
            
            # 注册成功后自动登录
            login(request, user)
            
            return render(request, 'authentication/login.html', {
                'register_success': f'注册成功！欢迎您，{username}！正在跳转...',
                'auto_redirect': True
            })
            
    except Exception as e:
        return render(request, 'authentication/login.html', {
            'register_error': f'注册失败：{str(e)}'
        })


@login_required
def logout_view(request):
    """登出视图"""
    logout(request)
    return redirect('/authentication/login/')


def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
