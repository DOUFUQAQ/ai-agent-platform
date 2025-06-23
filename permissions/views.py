from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
import json

from .models import AIFunction, StudentFunctionPermission, StudentGroup, StudentGroupMembership
from authentication.models import User, StudentProfile
from ai_agent.models import APIUsageLog


def is_admin_or_teacher(user):
    """检查用户是否为管理员或教师"""
    return user.is_authenticated and user.user_type in ['admin', 'teacher']


@login_required
@user_passes_test(is_admin_or_teacher)
def function_management(request):
    """AI功能管理页面"""
    # 获取所有功能
    functions = AIFunction.objects.all().order_by('name')
    
    # 为每个功能添加统计信息
    for function in functions:
        # 权限分配数量
        function.permission_count = StudentFunctionPermission.objects.filter(
            function=function, is_enabled=True
        ).count()
        
        # 使用次数（从聊天会话中统计）
        from behavior_tracking.models import ChatSession
        function.usage_count = ChatSession.objects.filter(
            function_code=function.function_code
        ).count()
    
    # 统计数据
    total_functions = functions.count()
    active_functions = functions.filter(is_active=True).count()
    total_permissions = StudentFunctionPermission.objects.filter(is_enabled=True).count()
    
    # 计算使用率
    total_sessions = ChatSession.objects.count()
    usage_rate = round((total_sessions / max(total_functions, 1)) * 100, 1) if total_sessions > 0 else 0
    
    context = {
        'functions': functions,
        'total_functions': total_functions,
        'active_functions': active_functions,
        'total_permissions': total_permissions,
        'usage_rate': usage_rate,
        'page_title': 'AI功能管理'
    }
    
    return render(request, 'permissions/function_management.html', context)


@login_required
@user_passes_test(is_admin_or_teacher)
def student_permission_management(request):
    """学生权限管理页面"""
    # 搜索和筛选
    search_query = request.GET.get('search', '')
    permission_level = request.GET.get('permission_level', '')
    function_filter = request.GET.get('function_filter', '')
    
    # 获取所有学生
    students = User.objects.filter(user_type='student', is_active=True)
    
    if search_query:
        students = students.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    students = students.order_by('username')
    
    # 为每个学生添加权限信息
    students_with_permissions = []
    for student in students:
        # 获取学生权限
        permissions = StudentFunctionPermission.objects.filter(
            student=student, is_enabled=True
        ).select_related('function', 'granted_by')
        
        # 获取学生档案
        try:
            profile = student.studentprofile
            student_id = profile.student_id
            class_name = profile.class_name
        except:
            student_id = None
            class_name = None
        
        # 计算权限级别
        permission_count = permissions.count()
        if permission_count >= 10:
            level = 'advanced'
        elif permission_count >= 5:
            level = 'intermediate'
        elif permission_count > 0:
            level = 'basic'
        else:
            level = 'none'
        
        # 权限级别筛选
        if permission_level and permission_level != level:
            continue
        
        # 功能筛选
        if function_filter:
            has_function = permissions.filter(function_id=function_filter).exists()
            if not has_function:
                continue
        
        # 最后权限更新时间
        last_permission_update = permissions.order_by('-granted_at').first()
        
        students_with_permissions.append({
            'id': student.id,
            'username': student.username,
            'email': student.email,
            'student_id': student_id,
            'class_name': class_name,
            'permissions': permissions,
            'permission_count': permission_count,
            'permission_level': level,
            'last_permission_update': last_permission_update.granted_at if last_permission_update else None,
            'is_active': student.is_active
        })
    
    # 分页
    paginator = Paginator(students_with_permissions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 获取可选功能列表
    available_function_list = AIFunction.objects.filter(is_active=True).order_by('name')
    
    # 统计数据
    total_students = User.objects.filter(user_type='student', is_active=True).count()
    students_with_permissions_count = StudentFunctionPermission.objects.filter(
        is_enabled=True
    ).values('student').distinct().count()
    
    context = {
        'students': page_obj.object_list,
        'page_obj': page_obj,
        'available_function_list': available_function_list,
        'total_students': total_students,
        'students_with_permissions': students_with_permissions_count,
        'search_query': search_query,
        'permission_level': permission_level,
        'function_filter': function_filter,
        'is_paginated': page_obj.has_other_pages(),
        'page_title': '学生权限管理'
    }
    
    return render(request, 'permissions/student_permission_management.html', context)


@login_required
@user_passes_test(is_admin_or_teacher)
def group_management(request):
    """学生群组管理页面"""
    # 获取所有群组
    groups = StudentGroup.objects.filter(is_active=True).order_by('name')
    
    # 为每个群组添加成员数量
    for group in groups:
        group.member_count = StudentGroupMembership.objects.filter(group=group).count()
        group.permission_count = GroupFunctionPermission.objects.filter(
            group=group, is_enabled=True
        ).count()
    
    context = {
        'groups': groups,
        'page_title': '学生群组管理'
    }
    
    return render(request, 'permissions/group_management.html', context)


@login_required
@user_passes_test(is_admin_or_teacher)
@require_http_methods(["POST"])
def toggle_student_function(request):
    """切换学生功能权限"""
    return JsonResponse({'success': True})


@login_required
@user_passes_test(is_admin_or_teacher)
@require_http_methods(["POST"])
def batch_toggle_function(request):
    """批量设置功能权限"""
    return JsonResponse({'success': True})


@login_required
@user_passes_test(is_admin_or_teacher)
@require_http_methods(["POST"])
def create_student_group(request):
    """创建学生群组"""
    return JsonResponse({'success': True})


@login_required
@user_passes_test(is_admin_or_teacher)
def student_detail(request, student_id):
    """学生详情页面"""
    return render(request, 'permissions/student_detail.html')


@login_required
@user_passes_test(is_admin_or_teacher)
def usage_analytics(request):
    """使用分析页面"""
    return render(request, 'permissions/usage_analytics.html')


@login_required
@user_passes_test(is_admin_or_teacher)
@require_http_methods(["POST"])
def toggle_function_status(request, function_id):
    """切换功能状态API"""
    try:
        function = get_object_or_404(AIFunction, id=function_id)
        function.is_active = not function.is_active
        function.save()
        
        return JsonResponse({
            'success': True,
            'message': f'功能已{"启用" if function.is_active else "禁用"}',
            'is_active': function.is_active
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@user_passes_test(is_admin_or_teacher)
@require_http_methods(["DELETE"])
def delete_function(request, function_id):
    """删除功能API"""
    try:
        function = get_object_or_404(AIFunction, id=function_id)
        function_name = function.name
        function.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'功能 "{function_name}" 已删除'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@user_passes_test(is_admin_or_teacher)
def function_permissions_detail(request, function_id):
    """功能权限详情页面"""
    function = get_object_or_404(AIFunction, id=function_id)
    permissions = StudentFunctionPermission.objects.filter(
        function=function, is_enabled=True
    ).select_related('student', 'granted_by')
    
    context = {
        'function': function,
        'permissions': permissions,
        'page_title': f'{function.name} - 权限详情'
    }
    
    return render(request, 'permissions/function_permissions_detail.html', context)


@login_required
@user_passes_test(is_admin_or_teacher)
@require_http_methods(["POST"])
def create_function(request):
    """创建AI功能API"""
    try:
        data = json.loads(request.body)
        
        # 验证必需字段
        required_fields = ['name', 'function_code', 'function_type']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'error': f'缺少必需字段: {field}'
                })
        
        # 检查功能代码是否唯一
        if AIFunction.objects.filter(function_code=data['function_code']).exists():
            return JsonResponse({
                'success': False,
                'error': '功能代码已存在，请使用不同的代码'
            })
        
        # 创建新功能
        function = AIFunction.objects.create(
            name=data['name'],
            function_code=data['function_code'],
            function_type=data['function_type'],
            description=data.get('description', ''),
            max_daily_usage=int(data.get('max_daily_usage', 0)),
            is_active=data.get('is_active', True),
            is_beta=data.get('is_beta', False)
        )
        
        return JsonResponse({
            'success': True,
            'message': f'功能 "{function.name}" 创建成功',
            'function_id': function.id
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'创建失败: {str(e)}'
        })


@login_required
@user_passes_test(is_admin_or_teacher)
@require_http_methods(["POST"])
def update_function(request, function_id):
    """更新AI功能API"""
    try:
        function = get_object_or_404(AIFunction, id=function_id)
        data = json.loads(request.body)
        
        # 验证必需字段
        required_fields = ['name', 'function_code', 'function_type']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'error': f'缺少必需字段: {field}'
                })
        
        # 检查功能代码是否唯一（排除当前功能）
        if AIFunction.objects.filter(function_code=data['function_code']).exclude(id=function_id).exists():
            return JsonResponse({
                'success': False,
                'error': '功能代码已存在，请使用不同的代码'
            })
        
        # 更新功能
        function.name = data['name']
        function.function_code = data['function_code']
        function.function_type = data['function_type']
        function.description = data.get('description', '')
        function.max_daily_usage = int(data.get('max_daily_usage', 0))
        function.is_active = data.get('is_active', True)
        function.is_beta = data.get('is_beta', False)
        function.save()
        
        return JsonResponse({
            'success': True,
            'message': f'功能 "{function.name}" 更新成功'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'更新失败: {str(e)}'
        }) 