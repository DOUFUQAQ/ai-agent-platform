"""
功能开关管理视图
实现功能权限配置、灰度发布和批量操作
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime

from authentication.decorators import teacher_or_admin_required, admin_required
from authentication.models import User
from .models import (
    AIFunction, StudentFunctionPermission, GroupFunctionPermission,
    StudentGroup, StudentGroupMembership, FunctionToggleLog,
    GrayReleaseConfig
)
from .function_toggle_service import FunctionToggleService, GrayReleaseService


@teacher_or_admin_required
def function_toggle_dashboard(request):
    """功能开关仪表板"""
    # 获取统计数据
    stats = {
        'total_functions': AIFunction.objects.count(),
        'active_functions': AIFunction.objects.filter(is_active=True).count(),
        'beta_functions': AIFunction.objects.filter(is_beta=True).count(),
        'gray_releases': GrayReleaseConfig.objects.filter(status='active').count(),
        'total_permissions': StudentFunctionPermission.objects.count(),
        'enabled_permissions': StudentFunctionPermission.objects.filter(is_enabled=True).count(),
        'group_permissions': GroupFunctionPermission.objects.count(),
        'total_toggles_today': FunctionToggleLog.objects.filter(
            operated_at__date=timezone.now().date()
        ).count(),
    }
    
    # 最近的功能开关操作
    recent_toggles = FunctionToggleLog.objects.select_related(
        'function', 'operated_by', 'target_user', 'target_group'
    ).order_by('-operated_at')[:10]
    
    # 活跃的灰度发布
    active_gray_releases = GrayReleaseConfig.objects.filter(
        status='active'
    ).select_related('function', 'created_by')[:5]
    
    # 功能使用统计
    function_stats = []
    for function in AIFunction.objects.filter(is_active=True)[:10]:
        coverage = GrayReleaseService.get_function_coverage_stats(function.id)
        function_stats.append({
            'function': function,
            'coverage': coverage
        })
    
    context = {
        'stats': stats,
        'recent_toggles': recent_toggles,
        'active_gray_releases': active_gray_releases,
        'function_stats': function_stats,
        'page_title': '功能开关仪表板'
    }
    
    return render(request, 'permissions/function_toggle_dashboard.html', context)


@teacher_or_admin_required
def function_permission_management(request):
    """功能权限管理"""
    # 搜索和筛选
    search_query = request.GET.get('search', '')
    function_filter = request.GET.get('function', '')
    status_filter = request.GET.get('status', '')
    
    permissions = StudentFunctionPermission.objects.select_related(
        'student', 'function', 'granted_by'
    ).all()
    
    if search_query:
        permissions = permissions.filter(
            Q(student__username__icontains=search_query) |
            Q(function__name__icontains=search_query)
        )
    
    if function_filter:
        permissions = permissions.filter(function_id=function_filter)
    
    if status_filter == 'enabled':
        permissions = permissions.filter(is_enabled=True)
    elif status_filter == 'disabled':
        permissions = permissions.filter(is_enabled=False)
    
    permissions = permissions.order_by('-granted_at')
    
    # 分页
    paginator = Paginator(permissions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 获取可选的功能列表
    functions = AIFunction.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'functions': functions,
        'search_query': search_query,
        'function_filter': function_filter,
        'status_filter': status_filter,
        'page_title': '功能权限管理'
    }
    
    return render(request, 'permissions/function_permission_management.html', context)


@teacher_or_admin_required
def group_permission_management(request):
    """群组权限管理"""
    # 搜索和筛选
    search_query = request.GET.get('search', '')
    function_filter = request.GET.get('function', '')
    
    permissions = GroupFunctionPermission.objects.select_related(
        'group', 'function', 'granted_by'
    ).all()
    
    if search_query:
        permissions = permissions.filter(
            Q(group__name__icontains=search_query) |
            Q(function__name__icontains=search_query)
        )
    
    if function_filter:
        permissions = permissions.filter(function_id=function_filter)
    
    permissions = permissions.order_by('-granted_at')
    
    # 分页
    paginator = Paginator(permissions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 获取可选的功能和群组列表
    functions = AIFunction.objects.filter(is_active=True).order_by('name')
    groups = StudentGroup.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'functions': functions,
        'groups': groups,
        'search_query': search_query,
        'function_filter': function_filter,
        'page_title': '群组权限管理'
    }
    
    return render(request, 'permissions/group_permission_management.html', context)


@teacher_or_admin_required
def gray_release_management(request):
    """灰度发布管理"""
    # 搜索和筛选
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    release_type_filter = request.GET.get('release_type', '')
    
    configs = GrayReleaseConfig.objects.select_related(
        'function', 'created_by'
    ).all()
    
    if search_query:
        configs = configs.filter(
            Q(release_name__icontains=search_query) |
            Q(function__name__icontains=search_query)
        )
    
    if status_filter:
        configs = configs.filter(status=status_filter)
    
    if release_type_filter:
        configs = configs.filter(release_type=release_type_filter)
    
    configs = configs.order_by('-created_at')
    
    # 分页
    paginator = Paginator(configs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 获取可选的功能列表
    functions = AIFunction.objects.filter(is_active=True, is_beta=True).order_by('name')
    groups = StudentGroup.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'functions': functions,
        'groups': groups,
        'search_query': search_query,
        'status_filter': status_filter,
        'release_type_filter': release_type_filter,
        'page_title': '灰度发布管理'
    }
    
    return render(request, 'permissions/gray_release_management.html', context)


@teacher_or_admin_required
def function_toggle_logs(request):
    """功能开关日志"""
    # 搜索和筛选
    search_query = request.GET.get('search', '')
    operation_filter = request.GET.get('operation', '')
    target_filter = request.GET.get('target', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    logs = FunctionToggleLog.objects.select_related(
        'function', 'operated_by', 'target_user', 'target_group'
    ).all()
    
    if search_query:
        logs = logs.filter(
            Q(function__name__icontains=search_query) |
            Q(operated_by__username__icontains=search_query) |
            Q(target_user__username__icontains=search_query) |
            Q(target_group__name__icontains=search_query)
        )
    
    if operation_filter:
        logs = logs.filter(operation_type=operation_filter)
    
    if target_filter:
        logs = logs.filter(target_type=target_filter)
    
    if date_from:
        logs = logs.filter(operated_at__date__gte=date_from)
    
    if date_to:
        logs = logs.filter(operated_at__date__lte=date_to)
    
    logs = logs.order_by('-operated_at')
    
    # 分页
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'operation_filter': operation_filter,
        'target_filter': target_filter,
        'date_from': date_from,
        'date_to': date_to,
        'operation_choices': FunctionToggleLog.OPERATION_TYPE_CHOICES,
        'target_choices': FunctionToggleLog.TARGET_TYPE_CHOICES,
        'page_title': '功能开关日志'
    }
    
    return render(request, 'permissions/function_toggle_logs.html', context)


# API 接口
@teacher_or_admin_required
@require_http_methods(["POST"])
def toggle_user_function_api(request):
    """切换用户功能权限API"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        function_id = data.get('function_id')
        is_enabled = data.get('is_enabled')
        reason = data.get('reason', '')
        daily_quota = data.get('daily_quota', 0)
        
        result = FunctionToggleService.toggle_user_function(
            user_id=user_id,
            function_id=function_id,
            is_enabled=is_enabled,
            operated_by=request.user,
            reason=reason,
            daily_quota=daily_quota
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'操作失败: {str(e)}'
        })


@teacher_or_admin_required
@require_http_methods(["POST"])
def batch_toggle_function_api(request):
    """批量切换功能权限API"""
    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        function_id = data.get('function_id')
        is_enabled = data.get('is_enabled')
        reason = data.get('reason', '')
        
        if not user_ids:
            return JsonResponse({
                'success': False,
                'error': '请选择至少一个用户'
            })
        
        result = FunctionToggleService.batch_toggle_function(
            user_ids=user_ids,
            function_id=function_id,
            is_enabled=is_enabled,
            operated_by=request.user,
            reason=reason
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'批量操作失败: {str(e)}'
        })


@admin_required
@require_http_methods(["POST"])
def create_gray_release_api(request):
    """创建灰度发布API"""
    try:
        data = json.loads(request.body)
        function_id = data.get('function_id')
        release_name = data.get('release_name')
        release_type = data.get('release_type')
        target_percentage = data.get('target_percentage', 0)
        target_groups = data.get('target_groups', [])
        whitelist_users = data.get('whitelist_users', [])
        
        if not release_name:
            return JsonResponse({
                'success': False,
                'error': '请填写发布名称'
            })
        
        result = GrayReleaseService.create_gray_release(
            function_id=function_id,
            release_name=release_name,
            release_type=release_type,
            target_percentage=target_percentage,
            target_groups=target_groups,
            whitelist_users=whitelist_users,
            created_by=request.user
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'创建失败: {str(e)}'
        })


@admin_required
@require_http_methods(["POST"])
def update_gray_release_progress_api(request):
    """更新灰度发布进度API"""
    try:
        data = json.loads(request.body)
        config_id = data.get('config_id')
        new_percentage = data.get('new_percentage')
        
        if new_percentage is None or not (0 <= new_percentage <= 100):
            return JsonResponse({
                'success': False,
                'error': '百分比必须在0-100之间'
            })
        
        result = GrayReleaseService.update_gray_release_percentage(
            config_id=config_id,
            new_percentage=new_percentage,
            operated_by=request.user
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'更新失败: {str(e)}'
        })


@teacher_or_admin_required
@require_http_methods(["GET"])
def function_coverage_stats_api(request, function_id):
    """获取功能覆盖统计API"""
    try:
        stats = GrayReleaseService.get_function_coverage_stats(function_id)
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'获取统计失败: {str(e)}'
        })


@teacher_or_admin_required
@require_http_methods(["POST"])
def update_gray_release_status_api(request):
    """更新灰度发布状态API"""
    try:
        data = json.loads(request.body)
        config_id = data.get('config_id')
        new_status = data.get('status')
        
        config = get_object_or_404(GrayReleaseConfig, id=config_id)
        old_status = config.status
        config.status = new_status
        
        # 设置开始/结束时间
        if new_status == 'active' and not config.start_time:
            config.start_time = timezone.now()
        elif new_status in ['completed', 'rollback']:
            config.end_time = timezone.now()
        
        config.save()
        
        # 记录状态变更日志
        FunctionToggleLog.objects.create(
            function=config.function,
            operation_type='quota_change',
            target_type='global',
            old_value={'status': old_status},
            new_value={'status': new_status},
            reason=f'灰度发布状态变更：{old_status} -> {new_status}',
            operated_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': f'灰度发布状态已更新为：{config.get_status_display()}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'状态更新失败: {str(e)}'
        }) 