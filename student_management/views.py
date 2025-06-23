from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
import json

from authentication.decorators import admin_required, teacher_or_admin_required
from .services import (
    StudentInfoService, 
    StudentUsageHistoryService, 
    StudentTagService, 
    StudentNoteService, 
    StudentStatisticsService
)
from .models import StudentTag, StudentNote, StudentTagAssignment

User = get_user_model()


@login_required
@teacher_or_admin_required
def dashboard(request):
    """学生管理仪表板"""
    # 获取统计数据
    stats = StudentStatisticsService.get_dashboard_stats()
    
    # 获取活跃度趋势
    activity_trend = StudentStatisticsService.get_student_activity_trend(30)
    
    # 获取最近活跃的学生
    recent_students = User.objects.filter(
        user_type='student',
        is_active=True
    ).order_by('-last_login')[:10]
    
    # 获取常用标签
    popular_tags = StudentTagService.get_all_tags()[:8]
    
    context = {
        'stats': stats,
        'activity_trend': activity_trend,
        'recent_students': recent_students,
        'popular_tags': popular_tags,
        'page_title': '学生管理仪表板'
    }
    
    return render(request, 'student_management/dashboard.html', context)


@login_required
@teacher_or_admin_required
def students_list(request):
    """学生列表页面"""
    search_query = request.GET.get('search', '')
    tag_filter = request.GET.get('tag', '')
    has_notes_filter = request.GET.get('has_notes', '')
    
    # 获取学生用户
    students = User.objects.filter(user_type='student', is_active=True)
    
    # 应用搜索筛选
    if search_query:
        students = students.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    students = students.order_by('username')
    
    # 为每个学生添加详细信息
    students_with_details = []
    for student in students:
        # 获取学生档案
        try:
            profile = student.studentprofile
            student_id = profile.student_id
            class_name = profile.class_name
        except:
            # 如果没有档案，创建默认的
            student_id = f"STU{student.id:04d}"
            class_name = "未分班"
        
        # 获取标签（从StudentTagAssignment获取）
        tags = StudentTagAssignment.objects.filter(
            student=student, tag__is_active=True
        ).values_list('tag__name', flat=True)
        
        # 获取备注数量
        notes_count = StudentNote.objects.filter(student=student).count()
        
        # 获取会话数量
        from behavior_tracking.models import ChatSession
        session_count = ChatSession.objects.filter(user=student).count()
        
        student_data = {
            'id': student.id,
            'username': student.username,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'email': student.email,
            'student_id': student_id,
            'class_name': class_name,
            'last_login': student.last_login,
            'date_joined': student.date_joined,
            'tags': list(tags),
            'notes_count': notes_count,
            'session_count': session_count,
            'is_active': student.is_active
        }
        
        # 应用标签筛选
        if tag_filter and tag_filter not in student_data['tags']:
            continue
            
        # 应用备注筛选
        if has_notes_filter == 'yes' and notes_count == 0:
            continue
        elif has_notes_filter == 'no' and notes_count > 0:
            continue
        
        students_with_details.append(student_data)
    
    # 分页
    paginator = Paginator(students_with_details, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 获取所有标签用于筛选
    all_tags = StudentTag.objects.filter(is_active=True).values('id', 'name', 'color')
    
    context = {
        'page_obj': page_obj,
        'students': page_obj.object_list,
        'total_count': len(students_with_details),
        'filters': {
            'search_query': search_query,
            'tag_filter': tag_filter,
            'has_notes_filter': has_notes_filter
        },
        'all_tags': all_tags,
        'page_title': '学生列表管理'
    }
    
    return render(request, 'student_management/students_list.html', context)


@login_required
@teacher_or_admin_required
def student_detail(request, student_id):
    """学生详情页面"""
    student_info = StudentInfoService.get_student_detail(student_id)
    
    if not student_info:
        messages.error(request, '学生不存在')
        return redirect('student_management:students_list')
    
    # 获取所有可用标签
    all_tags = StudentTagService.get_all_tags()
    
    context = {
        'student': student_info,
        'all_tags': all_tags,
        'page_title': f'学生详情 - {student_info["username"]}'
    }
    
    return render(request, 'student_management/student_detail.html', context)


@login_required
@teacher_or_admin_required
def student_usage_history(request, student_id):
    """学生使用历史页面"""
    days = int(request.GET.get('days', 30))
    
    try:
        student = User.objects.get(id=student_id, user_type='student')
    except User.DoesNotExist:
        messages.error(request, '学生不存在')
        return redirect('student_management:students_list')
    
    # 获取使用历史数据
    usage_history = StudentUsageHistoryService.get_student_usage_detail(student_id, days)
    usage_overview = StudentUsageHistoryService.get_student_usage_overview(student_id)
    
    context = {
        'student': student,
        'usage_history': usage_history,
        'usage_overview': usage_overview,
        'days': days,
        'page_title': f'使用历史 - {student.username}'
    }
    
    return render(request, 'student_management/usage_history.html', context)


@login_required
@admin_required
def tags_management(request):
    """标签管理页面"""
    try:
        # 获取所有标签
        from .models import StudentTag, StudentTagAssignment
        tags = StudentTag.objects.filter(is_active=True).order_by('name')
        
        # 为每个标签添加学生数量
        tags_with_stats = []
        for tag in tags:
            student_count = StudentTagAssignment.objects.filter(tag=tag).count()
            tags_with_stats.append({
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'description': tag.description,
                'student_count': student_count,
                'created_at': tag.created_at,
                'created_by': tag.created_by.username if tag.created_by else 'Unknown'
            })
        
        # 如果没有标签，提供默认标签信息用于创建
        default_tags_info = [
            {
                'name': '优秀学生',
                'color': '#28a745',
                'description': '学习成绩优秀，表现突出的学生'
            },
            {
                'name': '积极参与',
                'color': '#007bff', 
                'description': '课堂参与度高，互动积极的学生'
            },
            {
                'name': '需要关注',
                'color': '#ffc107',
                'description': '需要额外关注和帮助的学生'
            }
        ]
        
        total_assignments = StudentTagAssignment.objects.count()
        
        context = {
            'tags': tags_with_stats,
            'total_tags': len(tags_with_stats),
            'total_assignments': total_assignments,
            'default_tags_info': default_tags_info,
            'page_title': '标签管理'
        }
        
        return render(request, 'student_management/tags_management.html', context)
        
    except Exception as e:
        # 错误处理
        context = {
            'tags': [],
            'total_tags': 0,
            'total_assignments': 0,
            'error_message': f'加载标签数据失败: {str(e)}',
            'page_title': '标签管理'
        }
        return render(request, 'student_management/tags_management.html', context)


# API 视图

@csrf_exempt
@login_required
@teacher_or_admin_required
@require_http_methods(["POST"])
def assign_tag_api(request):
    """分配标签API"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        tag_id = data.get('tag_id')
        
        success = StudentTagService.assign_tag_to_student(
            student_id=student_id,
            tag_id=tag_id,
            assigned_by=request.user
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'message': '标签分配成功'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '标签分配失败，可能已存在或学生/标签不存在'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'操作失败：{str(e)}'
        })


@csrf_exempt
@login_required
@teacher_or_admin_required
@require_http_methods(["POST"])
def remove_tag_api(request):
    """移除标签API"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        tag_id = data.get('tag_id')
        
        success = StudentTagService.remove_tag_from_student(student_id, tag_id)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': '标签移除成功'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '标签移除失败，可能不存在'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'操作失败：{str(e)}'
        })


@csrf_exempt
@login_required
@admin_required
@require_http_methods(["POST"])
def create_tag_api(request):
    """创建标签API"""
    try:
        data = json.loads(request.body)
        name = data.get('name')
        tag_type = data.get('tag_type')
        color = data.get('color', '#007bff')
        description = data.get('description', '')
        
        if not name or not tag_type:
            return JsonResponse({
                'success': False,
                'message': '标签名称和类型不能为空'
            })
        
        tag = StudentTagService.create_tag(
            name=name,
            tag_type=tag_type,
            color=color,
            description=description,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': '标签创建成功',
            'data': {
                'id': tag.id,
                'name': tag.name,
                'tag_type': tag.tag_type,
                'color': tag.color
            }
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'创建失败：{str(e)}'
        })


@csrf_exempt
@login_required
@teacher_or_admin_required
@require_http_methods(["POST"])
def create_note_api(request):
    """创建备注API"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        title = data.get('title')
        content = data.get('content')
        is_important = data.get('is_important', False)
        
        if not student_id or not title or not content:
            return JsonResponse({
                'success': False,
                'message': '学生ID、标题和内容不能为空'
            })
        
        note = StudentNoteService.create_note(
            student_id=student_id,
            title=title,
            content=content,
            is_important=is_important,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': '备注创建成功',
            'data': {
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'is_important': note.is_important,
                'created_at': note.created_at.isoformat()
            }
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'创建失败：{str(e)}'
        })


@csrf_exempt
@login_required
@teacher_or_admin_required
@require_http_methods(["POST"])
def update_note_api(request):
    """更新备注API"""
    try:
        data = json.loads(request.body)
        note_id = data.get('note_id')
        title = data.get('title')
        content = data.get('content')
        is_important = data.get('is_important')
        
        success = StudentNoteService.update_note(
            note_id=note_id,
            title=title,
            content=content,
            is_important=is_important
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'message': '备注更新成功'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '备注更新失败，可能不存在'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'更新失败：{str(e)}'
        })


@csrf_exempt
@login_required
@teacher_or_admin_required
@require_http_methods(["POST"])
def delete_note_api(request):
    """删除备注API"""
    try:
        data = json.loads(request.body)
        note_id = data.get('note_id')
        
        success = StudentNoteService.delete_note(note_id)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': '备注删除成功'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '备注删除失败，可能不存在'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'删除失败：{str(e)}'
        })


@csrf_exempt
@login_required
@teacher_or_admin_required
@require_http_methods(["POST"])
def toggle_student_status_api(request):
    """切换学生账户状态API"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        
        student = get_object_or_404(User, id=student_id, user_type='student')
        student.is_active = not student.is_active
        student.save()
        
        return JsonResponse({
            'success': True,
            'message': f'学生账户已{"启用" if student.is_active else "禁用"}',
            'data': {
                'is_active': student.is_active
            }
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'操作失败：{str(e)}'
        })


@login_required
@teacher_or_admin_required
def export_student_data(request, student_id):
    """导出学生数据"""
    try:
        student_detail = StudentInfoService.get_student_detail(student_id)
        if not student_detail:
            return JsonResponse({
                'success': False,
                'message': '学生不存在'
            })
        
        # 这里可以生成CSV或Excel文件
        # 为了简化，返回JSON数据
        return JsonResponse({
            'success': True,
            'data': student_detail
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'导出失败：{str(e)}'
        })


@login_required
@teacher_or_admin_required
def export_all_students_data(request):
    """导出所有学生数据"""
    try:
        import pandas as pd
        from django.http import HttpResponse
        from io import BytesIO
        
        # 获取所有学生数据
        students = User.objects.filter(user_type='student', is_active=True)
        
        data = []
        for student in students:
            # 获取学生档案
            try:
                profile = student.studentprofile
                student_id = profile.student_id
                class_name = profile.class_name
            except:
                student_id = f"STU{student.id:04d}"
                class_name = "未分班"
            
            # 获取标签
            tags = StudentTagAssignment.objects.filter(
                student=student, tag__is_active=True
            ).values_list('tag__name', flat=True)
            
            # 获取会话统计
            from behavior_tracking.models import ChatSession
            session_count = ChatSession.objects.filter(user=student).count()
            
            data.append({
                '用户名': student.username,
                '学生ID': student_id,
                '姓名': student.get_full_name() or '',
                '邮箱': student.email or '',
                '班级': class_name,
                '注册时间': student.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                '最后登录': student.last_login.strftime('%Y-%m-%d %H:%M:%S') if student.last_login else '从未登录',
                '标签': ', '.join(tags),
                '会话次数': session_count,
                '状态': '活跃' if student.is_active else '禁用'
            })
        
        # 创建Excel文件
        df = pd.DataFrame(data)
        
        # 创建内存中的文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='学生数据', index=False)
        
        output.seek(0)
        
        # 设置响应
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="students_data.xlsx"'
        
        return response
        
    except ImportError:
        # 如果没有pandas，返回CSV格式
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="students_data.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['用户名', '学生ID', '姓名', '邮箱', '班级', '注册时间', '最后登录', '会话次数', '状态'])
        
        students = User.objects.filter(user_type='student', is_active=True)
        for student in students:
            try:
                profile = student.studentprofile
                student_id = profile.student_id
                class_name = profile.class_name
            except:
                student_id = f"STU{student.id:04d}"
                class_name = "未分班"
            
            from behavior_tracking.models import ChatSession
            session_count = ChatSession.objects.filter(user=student).count()
            
            writer.writerow([
                student.username,
                student_id,
                student.get_full_name() or '',
                student.email or '',
                class_name,
                student.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                student.last_login.strftime('%Y-%m-%d %H:%M:%S') if student.last_login else '从未登录',
                session_count,
                '活跃' if student.is_active else '禁用'
            ])
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'导出失败: {str(e)}'
        })


@login_required
@admin_required
@require_http_methods(["POST"])
def create_tag(request):
    """创建标签"""
    try:
        name = request.POST.get('name')
        color = request.POST.get('color', '#007bff')
        description = request.POST.get('description', '')
        
        if not name:
            messages.error(request, '标签名称不能为空')
            return redirect('student_management:tags_management')
        
        # 检查标签是否已存在
        if StudentTag.objects.filter(name=name, is_active=True).exists():
            messages.error(request, f'标签 "{name}" 已存在')
            return redirect('student_management:tags_management')
        
        # 创建标签
        tag = StudentTag.objects.create(
            name=name,
            tag_type='custom',
            color=color,
            description=description,
            created_by=request.user
        )
        
        messages.success(request, f'标签 "{name}" 创建成功')
        return redirect('student_management:tags_management')
        
    except Exception as e:
        messages.error(request, f'创建标签失败：{str(e)}')
        return redirect('student_management:tags_management')


@login_required
@admin_required
@require_http_methods(["POST"])
def update_tag(request, tag_id):
    """更新标签"""
    try:
        tag = get_object_or_404(StudentTag, id=tag_id, is_active=True)
        
        name = request.POST.get('name')
        color = request.POST.get('color')
        description = request.POST.get('description', '')
        
        if not name:
            messages.error(request, '标签名称不能为空')
            return redirect('student_management:tags_management')
        
        # 检查标签名称是否与其他标签冲突
        if StudentTag.objects.filter(name=name, is_active=True).exclude(id=tag_id).exists():
            messages.error(request, f'标签名称 "{name}" 已被使用')
            return redirect('student_management:tags_management')
        
        # 更新标签
        tag.name = name
        tag.color = color
        tag.description = description
        tag.save()
        
        messages.success(request, f'标签 "{name}" 更新成功')
        return redirect('student_management:tags_management')
        
    except Exception as e:
        messages.error(request, f'更新标签失败：{str(e)}')
        return redirect('student_management:tags_management')


@csrf_exempt
@login_required
@admin_required
@require_http_methods(["POST"])
def delete_tag(request, tag_id):
    """删除标签（软删除）"""
    try:
        tag = get_object_or_404(StudentTag, id=tag_id, is_active=True)
        
        # 软删除标签
        tag.is_active = False
        tag.save()
        
        # 移除所有相关的标签分配
        StudentTagAssignment.objects.filter(tag=tag).delete()
        
        return JsonResponse({
            'success': True,
            'message': f'标签 "{tag.name}" 删除成功'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
