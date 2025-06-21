#!/usr/bin/env python
"""
创建扩展演示数据脚本
"""

import os
import sys
import django
from datetime import datetime, timedelta, date
import json

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_agent_platform.settings')
django.setup()

from django.contrib.auth import get_user_model
from permissions.models import AIFunction, StudentGroup, StudentGroupMembership, StudentFunctionPermission
from student_management.models import StudentTag, StudentTagAssignment, StudentNote, StudentUsageStatistics
from behavior_tracking.models import ChatSession, ChatMessage, UserBehaviorLog

User = get_user_model()


def create_ai_functions():
    """创建AI功能定义"""
    functions = [
        {
            'function_code': 'qa',
            'name': '通用问答',
            'description': '提供各种问题的智能回答',
            'function_type': 'qa',
            'is_active': True,
            'max_daily_usage': 50
        },
        {
            'function_code': 'course_selection',
            'name': '选课助手',
            'description': '帮助学生选择合适的课程',
            'function_type': 'course_selection',
            'is_active': True,
            'max_daily_usage': 10
        },
        {
            'function_code': 'calendar',
            'name': 'AI日历',
            'description': '智能日程安排和提醒',
            'function_type': 'calendar',
            'is_active': True,
            'max_daily_usage': 20
        },
        {
            'function_code': 'email',
            'name': '邮件助手',
            'description': '协助撰写和管理邮件',
            'function_type': 'email',
            'is_active': True,
            'max_daily_usage': 15
        },
        {
            'function_code': 'study_plan',
            'name': '学业规划助手',
            'description': '制定个性化学习计划',
            'function_type': 'study_plan',
            'is_active': True,
            'max_daily_usage': 5
        },
        {
            'function_code': 'document',
            'name': '文档助手',
            'description': '文档编写和格式化',
            'function_type': 'document',
            'is_active': True,
            'is_beta': True,  # 测试功能
            'max_daily_usage': 8
        }
    ]
    
    print("创建AI功能...")
    for func_data in functions:
        function, created = AIFunction.objects.get_or_create(
            function_code=func_data['function_code'],
            defaults=func_data
        )
        if created:
            print(f"  ✓ 创建功能: {function.name}")
        else:
            print(f"  - 功能已存在: {function.name}")


def create_student_groups():
    """创建学生群组"""
    admin_user = User.objects.filter(user_type='admin').first()
    if not admin_user:
        print("警告: 没有找到管理员用户，跳过群组创建")
        return
    
    groups = [
        {
            'name': '2023级计算机科学与技术',
            'group_type': 'class',
            'description': '2023级计算机科学与技术专业学生'
        },
        {
            'name': '2022级软件工程',
            'group_type': 'class',
            'description': '2022级软件工程专业学生'
        },
        {
            'name': '信息学院',
            'group_type': 'major',
            'description': '信息学院所有学生'
        },
        {
            'name': 'AI课程试点班',
            'group_type': 'custom',
            'description': 'AI相关课程的试点学生群组'
        }
    ]
    
    print("创建学生群组...")
    created_groups = []
    for group_data in groups:
        group_data['created_by'] = admin_user
        group, created = StudentGroup.objects.get_or_create(
            name=group_data['name'],
            defaults=group_data
        )
        if created:
            print(f"  ✓ 创建群组: {group.name}")
            created_groups.append(group)
        else:
            print(f"  - 群组已存在: {group.name}")
            created_groups.append(group)
    
    return created_groups


def create_student_tags():
    """创建学生标签"""
    admin_user = User.objects.filter(user_type='admin').first()
    if not admin_user:
        print("警告: 没有找到管理员用户，跳过标签创建")
        return
    
    tags = [
        {
            'name': '需要关注',
            'tag_type': 'attention',
            'color': '#dc3545',
            'description': '需要特别关注的学生'
        },
        {
            'name': '高活跃用户',
            'tag_type': 'active',
            'color': '#28a745',
            'description': '使用频率很高的学生'
        },
        {
            'name': '反馈积极',
            'tag_type': 'feedback',
            'color': '#007bff',
            'description': '经常提供反馈的学生'
        },
        {
            'name': '优秀学生',
            'tag_type': 'excellent',
            'color': '#ffc107',
            'description': '表现优秀的学生'
        },
        {
            'name': 'AI爱好者',
            'tag_type': 'custom',
            'color': '#6f42c1',
            'description': '对AI技术特别感兴趣的学生'
        }
    ]
    
    print("创建学生标签...")
    created_tags = []
    for tag_data in tags:
        tag_data['created_by'] = admin_user
        tag, created = StudentTag.objects.get_or_create(
            name=tag_data['name'],
            defaults=tag_data
        )
        if created:
            print(f"  ✓ 创建标签: {tag.name}")
            created_tags.append(tag)
        else:
            print(f"  - 标签已存在: {tag.name}")
            created_tags.append(tag)
    
    return created_tags


def assign_permissions_and_tags():
    """分配权限和标签"""
    admin_user = User.objects.filter(user_type='admin').first()
    students = User.objects.filter(user_type='student')[:10]  # 取前10个学生
    functions = AIFunction.objects.all()
    tags = StudentTag.objects.all()
    
    if not admin_user or not students.exists():
        print("警告: 没有找到管理员或学生用户，跳过权限分配")
        return
    
    print("分配功能权限...")
    for i, student in enumerate(students):
        # 为每个学生分配不同的功能权限
        student_functions = functions[:3 + (i % 3)]  # 每个学生3-5个功能
        
        for function in student_functions:
            permission, created = StudentFunctionPermission.objects.get_or_create(
                student=student,
                function=function,
                defaults={
                    'is_enabled': True,
                    'daily_quota': function.max_daily_usage,
                    'granted_by': admin_user
                }
            )
            if created:
                print(f"  ✓ {student.username} -> {function.name}")
    
    print("分配学生标签...")
    for i, student in enumerate(students):
        # 为每个学生分配1-2个标签
        student_tags = [tags[i % len(tags)]]
        if i % 3 == 0:  # 每三个学生中有一个获得第二个标签
            student_tags.append(tags[(i + 1) % len(tags)])
        
        for tag in student_tags:
            assignment, created = StudentTagAssignment.objects.get_or_create(
                student=student,
                tag=tag,
                defaults={'assigned_by': admin_user}
            )
            if created:
                print(f"  ✓ {student.username} -> {tag.name}")


def create_student_notes():
    """创建学生备注"""
    admin_user = User.objects.filter(user_type='admin').first()
    students = User.objects.filter(user_type='student')[:5]  # 为前5个学生创建备注
    
    if not admin_user or not students.exists():
        print("警告: 没有找到管理员或学生用户，跳过备注创建")
        return
    
    notes_templates = [
        {
            'title': '学习表现优秀',
            'content': '该学生在AI课程中表现出色，积极参与讨论，作业质量很高。',
            'is_important': True
        },
        {
            'title': '需要额外指导',
            'content': '该学生在某些概念理解上有困难，建议提供额外的学习资源。',
            'is_important': True
        },
        {
            'title': '积极反馈',
            'content': '该学生经常提供有价值的反馈，帮助改进课程内容。',
            'is_important': False
        },
        {
            'title': '技术兴趣浓厚',
            'content': '对深度学习和机器学习表现出浓厚兴趣，可考虑推荐高级课程。',
            'is_important': False
        },
        {
            'title': '团队协作能力强',
            'content': '在小组项目中表现出色的领导力和协作能力。',
            'is_important': False
        }
    ]
    
    print("创建学生备注...")
    for i, student in enumerate(students):
        note_data = notes_templates[i % len(notes_templates)]
        note = StudentNote.objects.create(
            student=student,
            title=note_data['title'],
            content=note_data['content'],
            is_important=note_data['is_important'],
            created_by=admin_user
        )
        print(f"  ✓ 为 {student.username} 创建备注: {note.title}")


def create_usage_statistics():
    """创建使用统计数据"""
    students = User.objects.filter(user_type='student')[:8]
    
    if not students.exists():
        print("警告: 没有找到学生用户，跳过统计数据创建")
        return
    
    print("创建使用统计数据...")
    # 创建最近7天的统计数据
    for i in range(7):
        stat_date = date.today() - timedelta(days=i)
        
        for j, student in enumerate(students):
            # 模拟不同学生的使用模式
            base_sessions = 2 + (j % 5)  # 2-6个会话
            base_messages = base_sessions * (5 + (j % 10))  # 每会话5-14条消息
            base_duration = base_sessions * (10 + (j % 20))  # 每会话10-29分钟
            
            # 添加一些随机性
            daily_factor = 0.7 + (i % 3) * 0.15  # 0.7-1.0的因子
            
            functions_used = {
                'qa': int(base_sessions * 0.6 * daily_factor),
                'calendar': int(base_sessions * 0.3 * daily_factor),
                'study_plan': int(base_sessions * 0.2 * daily_factor)
            }
            
            stat, created = StudentUsageStatistics.objects.get_or_create(
                student=student,
                date=stat_date,
                defaults={
                    'total_sessions': int(base_sessions * daily_factor),
                    'total_messages': int(base_messages * daily_factor),
                    'total_duration_minutes': int(base_duration * daily_factor),
                    'functions_used': functions_used
                }
            )
            
            if created:
                print(f"  ✓ {student.username} - {stat_date}: {stat.total_sessions}会话")


def create_sample_chat_data():
    """创建示例聊天数据"""
    students = User.objects.filter(user_type='student')[:3]
    functions = AIFunction.objects.all()
    
    if not students.exists() or not functions.exists():
        print("警告: 没有找到学生用户或AI功能，跳过聊天数据创建")
        return
    
    print("创建示例聊天数据...")
    
    sample_conversations = [
        [
            "你好，我想了解一下机器学习的基本概念",
            "你好！机器学习是人工智能的一个重要分支，它让计算机能够从数据中学习并做出预测或决策，而无需被明确编程来执行特定任务..."
        ],
        [
            "我的课程安排很紧，能帮我制定一个学习计划吗？",
            "当然可以！为了制定最适合你的学习计划，我需要了解一些信息：你目前的课程有哪些？每周有多少空闲时间？..."
        ],
        [
            "如何选择适合的选修课？",
            "选择选修课时可以考虑以下几个因素：1. 与你的专业方向相关性；2. 个人兴趣爱好；3. 课程难度和时间安排..."
        ]
    ]
    
    for i, student in enumerate(students):
        # 为每个学生创建1-2个会话
        for j in range(1 + (i % 2)):
            session_id = f"session_{student.id}_{j}_{int(datetime.now().timestamp())}"
            function = functions[j % len(functions)]
            
            session = ChatSession.objects.create(
                user=student,
                session_id=session_id,
                title=f"与{function.name}的对话",
                function_code=function.function_code,
                started_at=datetime.now() - timedelta(hours=j+1),
                message_count=2,
                total_tokens=150 + (j * 50),
                ip_address='127.0.0.1'
            )
            
            # 添加对话消息
            conversation = sample_conversations[i % len(sample_conversations)]
            
            # 用户消息
            ChatMessage.objects.create(
                session=session,
                message_type='user',
                content=conversation[0],
                function_called=function.function_code,
                model_type='chat',
                tokens_used=20 + len(conversation[0]) // 4,
                response_time=0.5
            )
            
            # AI回复
            ChatMessage.objects.create(
                session=session,
                message_type='assistant',
                content=conversation[1],
                function_called=function.function_code,
                model_type='chat',
                tokens_used=50 + len(conversation[1]) // 4,
                response_time=2.3
            )
            
            print(f"  ✓ 为 {student.username} 创建会话: {session.title}")


def main():
    """主函数"""
    print("=== 创建扩展演示数据 ===")
    print()
    
    try:
        # 1. 创建AI功能
        create_ai_functions()
        print()
        
        # 2. 创建学生群组
        create_student_groups()
        print()
        
        # 3. 创建学生标签
        create_student_tags()
        print()
        
        # 4. 分配权限和标签
        assign_permissions_and_tags()
        print()
        
        # 5. 创建学生备注
        create_student_notes()
        print()
        
        # 6. 创建使用统计
        create_usage_statistics()
        print()
        
        # 7. 创建示例聊天数据
        create_sample_chat_data()
        print()
        
        print("=== 扩展演示数据创建完成 ===")
        print()
        print("现在你可以：")
        print("1. 访问 Django Admin 查看所有数据")
        print("2. 在聊天界面测试不同的AI功能")
        print("3. 查看学生管理、权限配置等功能")
        
    except Exception as e:
        print(f"创建数据时出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main() 