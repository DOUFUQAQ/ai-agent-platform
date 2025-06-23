"""
权限装饰器
实现基于角色的访问控制(RBAC)
"""

from functools import wraps
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
import json


def require_role(*allowed_roles):
    """
    角色权限装饰器
    
    Args:
        allowed_roles: 允许的角色列表，如 'admin', 'teacher', 'student'
    
    Usage:
        @require_role('admin')
        @require_role('admin', 'teacher')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request.user, 'user_type'):
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({
                        'success': False,
                        'error': '用户角色信息缺失'
                    }, status=403)
                messages.error(request, '用户角色信息缺失')
                return redirect('authentication:login')
            
            if request.user.user_type not in allowed_roles:
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({
                        'success': False,
                        'error': f'权限不足，需要角色: {", ".join(allowed_roles)}'
                    }, status=403)
                messages.error(request, f'权限不足，需要{", ".join([dict([("admin", "管理员"), ("teacher", "教师"), ("student", "学生")]).get(role, role) for role in allowed_roles])}权限')
                return redirect('ai_agent:chat_interface')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def admin_required(view_func):
    """管理员权限装饰器"""
    return require_role('admin')(view_func)


def teacher_or_admin_required(view_func):
    """教师或管理员权限装饰器"""
    return require_role('admin', 'teacher')(view_func)


def student_required(view_func):
    """学生权限装饰器"""
    return require_role('student')(view_func)


def check_function_permission(function_code):
    """
    检查用户是否有特定功能的权限
    
    Args:
        function_code: 功能代码
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # 管理员和教师默认有所有权限
            if request.user.user_type in ['admin', 'teacher']:
                return view_func(request, *args, **kwargs)
            
            # 学生需要检查具体权限
            if request.user.user_type == 'student':
                from permissions.models import StudentFunctionPermission, AIFunction
                from django.utils import timezone
                
                try:
                    function = AIFunction.objects.get(code=function_code, is_active=True)
                    permission = StudentFunctionPermission.objects.get(
                        student=request.user,
                        function=function,
                        is_enabled=True
                    )
                    
                    # 检查是否过期
                    if permission.expires_at and permission.expires_at < timezone.now():
                        if request.headers.get('Content-Type') == 'application/json':
                            return JsonResponse({
                                'success': False,
                                'error': '功能权限已过期'
                            }, status=403)
                        messages.error(request, '功能权限已过期')
                        return redirect('ai_agent:chat_interface')
                    
                except (AIFunction.DoesNotExist, StudentFunctionPermission.DoesNotExist):
                    if request.headers.get('Content-Type') == 'application/json':
                        return JsonResponse({
                            'success': False,
                            'error': f'无权限访问功能: {function_code}'
                        }, status=403)
                    messages.error(request, f'无权限访问该功能')
                    return redirect('ai_agent:chat_interface')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def api_permission_required(permission_check):
    """
    API权限装饰器
    
    Args:
        permission_check: 权限检查函数，接收(user, request)参数，返回(is_allowed, error_message)
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': '需要登录'
                }, status=401)
            
            is_allowed, error_message = permission_check(request.user, request)
            if not is_allowed:
                return JsonResponse({
                    'success': False,
                    'error': error_message
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# 预定义的权限检查函数
def admin_permission_check(user, request):
    """管理员权限检查"""
    if user.user_type == 'admin':
        return True, None
    return False, '需要管理员权限'


def teacher_or_admin_permission_check(user, request):
    """教师或管理员权限检查"""
    if user.user_type in ['admin', 'teacher']:
        return True, None
    return False, '需要教师或管理员权限'


def student_permission_check(user, request):
    """学生权限检查"""
    if user.user_type == 'student':
        return True, None
    return False, '需要学生权限' 