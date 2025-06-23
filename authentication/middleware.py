"""
权限管理中间件
实现登录日志记录、安全检查和权限验证
"""

import json
import logging
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import LoginLog

logger = logging.getLogger(__name__)


class LoginLoggingMiddleware:
    """登录日志中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # 记录登录成功日志
        if (request.path == reverse('authentication:login') and 
            request.method == 'POST' and 
            response.status_code == 302 and  # 重定向表示登录成功
            request.user.is_authenticated):
            
            self._log_login(request, 'success')
        
        # 记录登录失败日志
        elif (request.path == reverse('authentication:login') and 
              request.method == 'POST' and 
              response.status_code == 200):  # 返回登录页面表示失败
            
            self._log_login(request, 'failed')
        
        return response
    
    def _log_login(self, request, status):
        """记录登录日志"""
        try:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            if status == 'success' and request.user.is_authenticated:
                # 更新用户最后登录IP
                request.user.last_login_ip = ip_address
                request.user.save(update_fields=['last_login_ip'])
                
                # 记录登录日志
                LoginLog.objects.create(
                    user=request.user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    login_status=status
                )
            elif status == 'failed':
                # 尝试从POST数据获取用户名
                username = request.POST.get('username', '')
                if username:
                    from .models import User
                    try:
                        user = User.objects.get(username=username)
                        LoginLog.objects.create(
                            user=user,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            login_status=status
                        )
                    except User.DoesNotExist:
                        logger.warning(f"登录失败，用户不存在: {username}, IP: {ip_address}")
        except Exception as e:
            logger.error(f"记录登录日志失败: {e}")
    
    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityMiddleware:
    """安全检查中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # 需要管理员权限的路径前缀
        self.admin_only_paths = [
            '/audit/',
        ]
        # 需要管理员或教师权限的路径前缀
        self.admin_teacher_paths = [
            '/permissions/',
            '/behavior/',
            '/students/',
        ]
        # 需要登录但权限相对宽松的路径
        self.login_required_paths = [
            '/auth/admin/',
            '/ai_agent/',
        ]
    
    def __call__(self, request):
        # 添加调试信息
        if hasattr(request.user, 'username') and request.user.is_authenticated:
            logger.info(f"用户 {request.user.username} (类型: {getattr(request.user, 'user_type', 'unknown')}) 访问: {request.path}")
        
        # 检查是否需要权限验证
        permission_response = self._check_permissions(request)
        if permission_response:
            return permission_response
        
        response = self.get_response(request)
        
        # 添加安全头
        self._add_security_headers(response)
        
        return response
    
    def _check_permissions(self, request):
        """检查用户权限"""
        # 跳过静态文件和API健康检查
        if (request.path.startswith('/static/') or 
            request.path.startswith('/media/') or
            request.path == '/favicon.ico' or
            request.path.startswith('/ai_agent/api/agno/health')):
            return None
        
        # 检查是否需要管理员权限
        if any(request.path.startswith(path) for path in self.admin_only_paths):
            if not request.user.is_authenticated:
                logger.info(f"未登录用户尝试访问管理员页面: {request.path}")
                return redirect('authentication:login')
            if not hasattr(request.user, 'user_type') or request.user.user_type != 'admin':
                logger.info(f"用户 {request.user.username} (类型: {getattr(request.user, 'user_type', 'unknown')}) 权限不足，访问管理员页面: {request.path}")
                return redirect('ai_agent:chat_interface')
        
        # 检查是否需要管理员或教师权限
        elif any(request.path.startswith(path) for path in self.admin_teacher_paths):
            if not request.user.is_authenticated:
                logger.info(f"未登录用户尝试访问管理页面: {request.path}")
                return redirect('authentication:login')
            if not hasattr(request.user, 'user_type') or request.user.user_type not in ['admin', 'teacher']:
                logger.info(f"用户 {request.user.username} (类型: {getattr(request.user, 'user_type', 'unknown')}) 权限不足，访问管理页面: {request.path}")
                return redirect('ai_agent:chat_interface')
        
        # 检查是否需要登录
        elif any(request.path.startswith(path) for path in self.login_required_paths):
            if not request.user.is_authenticated:
                logger.info(f"未登录用户尝试访问需要登录的页面: {request.path}")
                return redirect('authentication:login')
        
        return None
    
    def _add_security_headers(self, response):
        """添加安全头"""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'


class PermissionAuditMiddleware:
    """权限操作审计中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # 需要审计的操作路径
        self.audit_paths = [
            '/permissions/api/',
            '/ai_agent/api/',
        ]
    
    def __call__(self, request):
        # 记录请求开始时间
        start_time = timezone.now()
        
        response = self.get_response(request)
        
        # 审计权限相关操作
        if self._needs_audit(request) and request.user.is_authenticated:
            self._audit_operation(request, response, start_time)
        
        return response
    
    def _needs_audit(self, request):
        """检查是否需要审计"""
        return (any(request.path.startswith(path) for path in self.audit_paths) and
                request.method in ['POST', 'PUT', 'DELETE'])
    
    def _audit_operation(self, request, response, start_time):
        """审计操作"""
        try:
            # 只审计成功的操作
            if response.status_code < 400:
                from permissions.models import PermissionAuditLog
                
                # 解析操作类型
                audit_type = self._get_audit_type(request)
                if audit_type:
                    operation_detail = {
                        'path': request.path,
                        'method': request.method,
                        'status_code': response.status_code,
                        'duration_ms': int((timezone.now() - start_time).total_seconds() * 1000),
                        'data': self._get_request_data(request)
                    }
                    
                    PermissionAuditLog.objects.create(
                        audit_type=audit_type,
                        operation_detail=operation_detail,
                        ip_address=self._get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        operated_by=request.user
                    )
        except Exception as e:
            logger.error(f"权限审计失败: {e}")
    
    def _get_audit_type(self, request):
        """获取审计类型"""
        path_mapping = {
            'toggle-function': 'permission_grant',
            'batch-toggle': 'permission_grant',
            'create-group': 'group_assignment',
        }
        
        for key, audit_type in path_mapping.items():
            if key in request.path:
                return audit_type
        
        return 'permission_grant'  # 默认类型
    
    def _get_request_data(self, request):
        """获取请求数据（安全过滤）"""
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
                # 过滤敏感信息
                filtered_data = {}
                for key, value in data.items():
                    if key.lower() not in ['password', 'token', 'secret']:
                        filtered_data[key] = value
                return filtered_data
            else:
                # 处理表单数据
                filtered_data = {}
                for key, value in request.POST.items():
                    if key.lower() not in ['password', 'token', 'secret']:
                        filtered_data[key] = value
                return filtered_data
        except:
            return {'error': 'Failed to parse request data'}
    
    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip 