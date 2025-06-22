"""
权限检查装饰器
用于在AI功能调用时检查用户权限
"""

from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .function_toggle_service import FunctionToggleService


def check_function_permission(function_code):
    """
    检查用户是否有特定功能的权限
    
    Args:
        function_code: 功能代码
    
    Returns:
        装饰器函数
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # 检查用户权限
            is_allowed, message = FunctionToggleService.check_user_function_permission(
                request.user, function_code
            )
            
            if not is_allowed:
                # 如果是AJAX请求，返回JSON响应
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': f'权限不足: {message}',
                        'permission_denied': True
                    })
                
                # 普通请求，添加消息并重定向
                messages.error(request, f'权限不足: {message}')
                return redirect('index')
            
            # 记录功能使用
            FunctionToggleService.record_function_usage(request.user, function_code)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def api_function_permission(function_code):
    """
    API专用的功能权限检查装饰器
    
    Args:
        function_code: 功能代码
    
    Returns:
        装饰器函数
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # 检查用户权限
            is_allowed, message = FunctionToggleService.check_user_function_permission(
                request.user, function_code
            )
            
            if not is_allowed:
                return JsonResponse({
                    'success': False,
                    'error': f'权限不足: {message}',
                    'permission_denied': True,
                    'function_code': function_code
                }, status=403)
            
            # 记录功能使用
            FunctionToggleService.record_function_usage(request.user, function_code)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def batch_function_permission_check(function_codes):
    """
    批量检查多个功能权限
    
    Args:
        function_codes: 功能代码列表
    
    Returns:
        装饰器函数
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            denied_functions = []
            
            for function_code in function_codes:
                is_allowed, message = FunctionToggleService.check_user_function_permission(
                    request.user, function_code
                )
                if not is_allowed:
                    denied_functions.append({
                        'function_code': function_code,
                        'message': message
                    })
            
            if denied_functions:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': '部分功能权限不足',
                        'denied_functions': denied_functions,
                        'permission_denied': True
                    }, status=403)
                
                error_messages = [f"{item['function_code']}: {item['message']}" for item in denied_functions]
                messages.error(request, '权限不足: ' + '; '.join(error_messages))
                return redirect('index')
            
            # 记录所有功能使用
            for function_code in function_codes:
                FunctionToggleService.record_function_usage(request.user, function_code)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator 