from django.db.models import Count, Sum, Avg, Q
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from collections import defaultdict
from typing import Dict, List, Any

from .models import StudentTag, StudentTagAssignment, StudentNote, StudentUsageStatistics
from behavior_tracking.models import ChatSession, ChatMessage
from permissions.models import AIFunction

User = get_user_model()


class StudentInfoService:
    """学生信息管理服务"""
    
    @staticmethod
    def get_students_list(search_query: str = "", user_type_filter: str = "", 
                         tag_filter: str = "", has_notes_filter: bool = None,
                         page_size: int = 20) -> Dict[str, Any]:
        """获取学生列表"""
        students = User.objects.filter(user_type='student')
        
        # 搜索筛选
        if search_query:
            students = students.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        # 标签筛选
        if tag_filter:
            students = students.filter(tag_assignments__tag__name=tag_filter)
        
        # 备注筛选
        if has_notes_filter is not None:
            if has_notes_filter:
                students = students.filter(student_notes__isnull=False)
            else:
                students = students.filter(student_notes__isnull=True)
        
        students = students.distinct().order_by('-date_joined')
        
        # 为每个学生添加扩展信息
        students_with_info = []
        for student in students:
            student_info = StudentInfoService.get_student_basic_info(student.id)
            students_with_info.append(student_info)
        
        return {
            'students': students_with_info,
            'total_count': students.count(),
            'filters': {
                'search_query': search_query,
                'tag_filter': tag_filter,
                'has_notes_filter': has_notes_filter
            }
        }
    
    @staticmethod
    def get_student_basic_info(student_id: int) -> Dict[str, Any]:
        """获取学生基本信息"""
        try:
            student = User.objects.get(id=student_id, user_type='student')
        except User.DoesNotExist:
            return None
        
        # 基本信息
        basic_info = {
            'id': student.id,
            'username': student.username,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'email': student.email,
            'date_joined': student.date_joined,
            'last_login': student.last_login,
            'is_active': student.is_active,
        }
        
        # 获取标签
        tags = StudentTagAssignment.objects.filter(
            student=student
        ).select_related('tag')
        student_tags = [
            {
                'id': tag.tag.id,
                'name': tag.tag.name,
                'color': tag.tag.color,
                'tag_type': tag.tag.tag_type,
                'assigned_at': tag.assigned_at
            }
            for tag in tags
        ]
        
        # 获取备注数量
        notes_count = StudentNote.objects.filter(student=student).count()
        
        # 获取最近的重要备注
        recent_important_note = StudentNote.objects.filter(
            student=student, is_important=True
        ).first()
        
        # 获取使用统计概览
        usage_stats = StudentUsageHistoryService.get_student_usage_overview(student_id)
        
        return {
            **basic_info,
            'tags': student_tags,
            'notes_count': notes_count,
            'recent_important_note': recent_important_note,
            'usage_overview': usage_stats
        }
    
    @staticmethod
    def get_student_detail(student_id: int) -> Dict[str, Any]:
        """获取学生详细信息"""
        basic_info = StudentInfoService.get_student_basic_info(student_id)
        if not basic_info:
            return None
        
        student = User.objects.get(id=student_id)
        
        # 获取所有备注
        notes = StudentNote.objects.filter(student=student).order_by('-created_at')[:10]
        notes_data = [
            {
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'is_important': note.is_important,
                'created_by': note.created_by.username,
                'created_at': note.created_at,
                'updated_at': note.updated_at
            }
            for note in notes
        ]
        
        # 获取详细使用历史
        usage_history = StudentUsageHistoryService.get_student_usage_detail(student_id)
        
        # 获取最近会话
        recent_sessions = ChatSession.objects.filter(
            user=student
        ).order_by('-started_at')[:10]
        
        sessions_data = [
            {
                'id': session.id,
                'session_id': session.session_id,
                'title': session.title,
                'function_code': session.function_code,
                'started_at': session.started_at,
                'ended_at': session.ended_at,
                'message_count': session.message_count,
                'total_tokens': session.total_tokens
            }
            for session in recent_sessions
        ]
        
        return {
            **basic_info,
            'notes': notes_data,
            'usage_history': usage_history,
            'recent_sessions': sessions_data
        }


class StudentUsageHistoryService:
    """学生使用历史分析服务"""
    
    @staticmethod
    def get_student_usage_overview(student_id: int) -> Dict[str, Any]:
        """获取学生使用概览"""
        student = User.objects.get(id=student_id)
        
        # 总会话数
        total_sessions = ChatSession.objects.filter(user=student).count()
        
        # 总消息数
        total_messages = ChatMessage.objects.filter(
            session__user=student,
            message_type='user'
        ).count()
        
        # 最近30天活跃度
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        recent_sessions = ChatSession.objects.filter(
            user=student,
            started_at__date__gte=thirty_days_ago
        ).count()
        
        # 平均会话时长
        completed_sessions = ChatSession.objects.filter(
            user=student,
            ended_at__isnull=False
        )
        
        avg_duration_minutes = 0
        if completed_sessions.exists():
            total_duration = sum([
                (session.ended_at - session.started_at).total_seconds() / 60
                for session in completed_sessions
            ])
            avg_duration_minutes = round(total_duration / completed_sessions.count(), 2)
        
        # 常用功能Top3
        function_usage = ChatSession.objects.filter(
            user=student,
            function_code__isnull=False
        ).values('function_code').annotate(
            count=Count('id')
        ).order_by('-count')[:3]
        
        top_functions = []
        for func in function_usage:
            try:
                function = AIFunction.objects.get(function_code=func['function_code'])
                top_functions.append({
                    'function_code': func['function_code'],
                    'function_name': function.name,
                    'usage_count': func['count']
                })
            except AIFunction.DoesNotExist:
                top_functions.append({
                    'function_code': func['function_code'],
                    'function_name': func['function_code'],
                    'usage_count': func['count']
                })
        
        # 最后活跃时间
        last_session = ChatSession.objects.filter(user=student).first()
        last_active = last_session.started_at if last_session else None
        
        return {
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'recent_sessions_30d': recent_sessions,
            'avg_duration_minutes': avg_duration_minutes,
            'top_functions': top_functions,
            'last_active': last_active
        }
    
    @staticmethod
    def get_student_usage_detail(student_id: int, days: int = 30) -> Dict[str, Any]:
        """获取学生详细使用历史"""
        student = User.objects.get(id=student_id)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # 每日使用趋势
        daily_stats = []
        current_date = start_date
        
        while current_date <= end_date:
            day_sessions = ChatSession.objects.filter(
                user=student,
                started_at__date=current_date
            )
            
            day_messages = ChatMessage.objects.filter(
                session__user=student,
                session__started_at__date=current_date,
                message_type='user'
            ).count()
            
            daily_stats.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'sessions': day_sessions.count(),
                'messages': day_messages
            })
            
            current_date += timedelta(days=1)
        
        # 功能使用分布
        function_stats = ChatSession.objects.filter(
            user=student,
            started_at__date__gte=start_date,
            function_code__isnull=False
        ).values('function_code').annotate(
            usage_count=Count('id'),
            total_messages=Sum('message_count')
        ).order_by('-usage_count')
        
        function_distribution = []
        for func in function_stats:
            try:
                function = AIFunction.objects.get(function_code=func['function_code'])
                function_distribution.append({
                    'function_code': func['function_code'],
                    'function_name': function.name,
                    'usage_count': func['usage_count'],
                    'total_messages': func['total_messages'] or 0
                })
            except AIFunction.DoesNotExist:
                function_distribution.append({
                    'function_code': func['function_code'],
                    'function_name': func['function_code'],
                    'usage_count': func['usage_count'],
                    'total_messages': func['total_messages'] or 0
                })
        
        # 使用时间分布
        hour_distribution = ChatSession.objects.filter(
            user=student,
            started_at__date__gte=start_date
        ).extra(
            select={'hour': "CAST(strftime('%%H', started_at) AS INTEGER)"}
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        return {
            'period_stats': {
                'start_date': start_date,
                'end_date': end_date,
                'total_sessions': ChatSession.objects.filter(
                    user=student,
                    started_at__date__gte=start_date
                ).count(),
                'total_messages': ChatMessage.objects.filter(
                    session__user=student,
                    session__started_at__date__gte=start_date,
                    message_type='user'
                ).count()
            },
            'daily_trend': daily_stats,
            'function_distribution': function_distribution,
            'hour_distribution': list(hour_distribution)
        }


class StudentTagService:
    """学生标签管理服务"""
    
    @staticmethod
    def get_all_tags() -> List[Dict[str, Any]]:
        """获取所有可用标签"""
        tags = StudentTag.objects.filter(is_active=True).order_by('tag_type', 'name')
        return [
            {
                'id': tag.id,
                'name': tag.name,
                'tag_type': tag.tag_type,
                'color': tag.color,
                'description': tag.description,
                'created_by': tag.created_by.username,
                'created_at': tag.created_at,
                'usage_count': StudentTagAssignment.objects.filter(tag=tag).count()
            }
            for tag in tags
        ]
    
    @staticmethod
    def create_tag(name: str, tag_type: str, color: str, description: str, created_by: User) -> StudentTag:
        """创建新标签"""
        tag = StudentTag.objects.create(
            name=name,
            tag_type=tag_type,
            color=color,
            description=description,
            created_by=created_by
        )
        return tag
    
    @staticmethod
    def assign_tag_to_student(student_id: int, tag_id: int, assigned_by: User) -> bool:
        """为学生分配标签"""
        try:
            student = User.objects.get(id=student_id, user_type='student')
            tag = StudentTag.objects.get(id=tag_id, is_active=True)
            
            assignment, created = StudentTagAssignment.objects.get_or_create(
                student=student,
                tag=tag,
                defaults={'assigned_by': assigned_by}
            )
            return created
        except (User.DoesNotExist, StudentTag.DoesNotExist):
            return False
    
    @staticmethod
    def remove_tag_from_student(student_id: int, tag_id: int) -> bool:
        """移除学生标签"""
        try:
            assignment = StudentTagAssignment.objects.get(
                student_id=student_id,
                tag_id=tag_id
            )
            assignment.delete()
            return True
        except StudentTagAssignment.DoesNotExist:
            return False
    
    @staticmethod
    def get_students_by_tag(tag_id: int) -> List[Dict[str, Any]]:
        """获取拥有特定标签的学生"""
        assignments = StudentTagAssignment.objects.filter(
            tag_id=tag_id
        ).select_related('student', 'assigned_by')
        
        return [
            {
                'student': StudentInfoService.get_student_basic_info(assignment.student.id),
                'assigned_by': assignment.assigned_by.username,
                'assigned_at': assignment.assigned_at
            }
            for assignment in assignments
        ]


class StudentNoteService:
    """学生备注管理服务"""
    
    @staticmethod
    def create_note(student_id: int, title: str, content: str, 
                   is_important: bool, created_by: User) -> StudentNote:
        """创建学生备注"""
        student = User.objects.get(id=student_id, user_type='student')
        note = StudentNote.objects.create(
            student=student,
            title=title,
            content=content,
            is_important=is_important,
            created_by=created_by
        )
        return note
    
    @staticmethod
    def update_note(note_id: int, title: str = None, content: str = None, 
                   is_important: bool = None) -> bool:
        """更新学生备注"""
        try:
            note = StudentNote.objects.get(id=note_id)
            if title is not None:
                note.title = title
            if content is not None:
                note.content = content
            if is_important is not None:
                note.is_important = is_important
            note.save()
            return True
        except StudentNote.DoesNotExist:
            return False
    
    @staticmethod
    def delete_note(note_id: int) -> bool:
        """删除学生备注"""
        try:
            note = StudentNote.objects.get(id=note_id)
            note.delete()
            return True
        except StudentNote.DoesNotExist:
            return False
    
    @staticmethod
    def get_student_notes(student_id: int) -> List[Dict[str, Any]]:
        """获取学生的所有备注"""
        notes = StudentNote.objects.filter(
            student_id=student_id
        ).order_by('-is_important', '-created_at')
        
        return [
            {
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'is_important': note.is_important,
                'created_by': note.created_by.username,
                'created_at': note.created_at,
                'updated_at': note.updated_at
            }
            for note in notes
        ]


class StudentStatisticsService:
    """学生统计服务"""
    
    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """获取学生管理仪表板统计数据"""
        total_students = User.objects.filter(user_type='student').count()
        active_students = User.objects.filter(
            user_type='student',
            is_active=True
        ).count()
        
        # 本周新注册学生
        week_ago = timezone.now() - timedelta(days=7)
        new_students_week = User.objects.filter(
            user_type='student',
            date_joined__gte=week_ago
        ).count()
        
        # 今日活跃学生
        today = timezone.now().date()
        active_today = ChatSession.objects.filter(
            user__user_type='student',
            started_at__date=today
        ).values('user').distinct().count()
        
        # 标签统计
        total_tags = StudentTag.objects.filter(is_active=True).count()
        tagged_students = StudentTagAssignment.objects.values('student').distinct().count()
        
        # 备注统计
        total_notes = StudentNote.objects.count()
        students_with_notes = StudentNote.objects.values('student').distinct().count()
        important_notes = StudentNote.objects.filter(is_important=True).count()
        
        return {
            'students': {
                'total': total_students,
                'active': active_students,
                'new_week': new_students_week,
                'active_today': active_today
            },
            'tags': {
                'total': total_tags,
                'tagged_students': tagged_students
            },
            'notes': {
                'total': total_notes,
                'students_with_notes': students_with_notes,
                'important': important_notes
            }
        }
    
    @staticmethod
    def get_student_activity_trend(days: int = 30) -> List[Dict[str, Any]]:
        """获取学生活跃度趋势"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        daily_stats = []
        current_date = start_date
        
        while current_date <= end_date:
            # 当日活跃学生数
            active_students = ChatSession.objects.filter(
                user__user_type='student',
                started_at__date=current_date
            ).values('user').distinct().count()
            
            # 当日新注册学生数
            new_students = User.objects.filter(
                user_type='student',
                date_joined__date=current_date
            ).count()
            
            daily_stats.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'active_students': active_students,
                'new_students': new_students
            })
            
            current_date += timedelta(days=1)
        
        return daily_stats 