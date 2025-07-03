#!/usr/bin/env python
"""
创建仪表板测试数据
"""

import os
import sys
import django
from django.utils import timezone
from datetime import timedelta, datetime
import random

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_agent_platform.settings')
django.setup()

from django.contrib.auth import get_user_model
from behavior_tracking.models import ChatSession, ChatMessage
from permissions.models import AIFunction

User = get_user_model()

def create_test_data():
    """创建测试数据"""
    print("🚀 开始创建仪表板测试数据...")
    
    # 1. 确保有测试用户
    test_users = []
    for i in range(10):
        username = f'test_student_{i+1}'
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@test.com',
                'user_type': 'student',
                'first_name': f'学生{i+1}',
                'is_active': True
            }
        )
        test_users.append(user)
        if created:
            user.set_password('password123')
            user.save()
    
    print(f"✅ 创建了 {len(test_users)} 个测试用户")
    
    # 2. 确保有AI功能
    functions = [
        {'function_code': 'chat', 'name': '智能聊天', 'description': '基础聊天功能'},
        {'function_code': 'agno_chat', 'name': 'AGNO聊天', 'description': 'AGNO智能体聊天'},
        {'function_code': 'agno_reasoning', 'name': 'AGNO推理', 'description': 'AGNO推理功能'},
        {'function_code': 'agno_research', 'name': 'AGNO研究', 'description': 'AGNO研究助手'},
        {'function_code': 'deepseek_chat', 'name': 'DeepSeek聊天', 'description': 'DeepSeek聊天功能'},
        {'function_code': 'study_helper', 'name': '学习助手', 'description': '学习辅导功能'},
    ]
    
    ai_functions = []
    for func_data in functions:
        func, created = AIFunction.objects.get_or_create(
            function_code=func_data['function_code'],
            defaults={
                'name': func_data['name'],
                'description': func_data['description'],
                'is_active': True,
                'is_beta': False,
                'max_daily_usage': 100
            }
        )
        ai_functions.append(func)
    
    print(f"✅ 创建了 {len(ai_functions)} 个AI功能")
    
    # 3. 创建历史会话和消息数据（过去7天）
    today = timezone.now().date()
    session_count = 0
    message_count = 0
    
    for days_back in range(7):
        date = today - timedelta(days=days_back)
        daily_users = random.sample(test_users, random.randint(3, 8))
        
        for user in daily_users:
            # 每个用户创建1-3个会话
            for session_num in range(random.randint(1, 4)):
                # 随机选择功能
                function = random.choice(ai_functions)
                
                # 创建会话时间
                session_start = timezone.make_aware(
                    datetime.combine(date, datetime.min.time()) + 
                    timedelta(hours=random.randint(8, 22), minutes=random.randint(0, 59))
                )
                session_end = session_start + timedelta(minutes=random.randint(5, 120))
                
                session = ChatSession.objects.create(
                    user=user,
                    session_id=f'session_{date}_{user.id}_{session_num}',
                    title=f'{function.name}会话 - {date}',
                    function_code=function.function_code,
                    started_at=session_start,
                    ended_at=session_end if random.random() > 0.1 else None,
                    message_count=0
                )
                session_count += 1
                
                # 为每个会话创建5-20条消息
                msg_count = random.randint(5, 20)
                for msg_num in range(msg_count):
                    msg_time = session_start + timedelta(minutes=msg_num * 2)
                    
                    # 用户消息
                    ChatMessage.objects.create(
                        session=session,
                        message_type='user',
                        content=f'这是用户消息 {msg_num+1}，测试{function.name}功能',
                        created_at=msg_time,
                        function_called=function.function_code
                    )
                    message_count += 1
                    
                    # AI回复
                    ChatMessage.objects.create(
                        session=session,
                        message_type='assistant',
                        content=f'这是AI回复 {msg_num+1}，来自{function.name}',
                        created_at=msg_time + timedelta(seconds=30),
                        function_called=function.function_code
                    )
                    message_count += 1
                
                # 更新会话消息数
                session.message_count = msg_count * 2
                session.save()
    
    print(f"✅ 创建了 {session_count} 个会话和 {message_count} 条消息")
    
    # 4. 创建今天的数据
    today_users = random.sample(test_users, random.randint(5, 8))
    for user in today_users:
        for session_num in range(random.randint(1, 3)):
            function = random.choice(ai_functions)
            
            session_start = timezone.now() - timedelta(hours=random.randint(1, 8))
            
            session = ChatSession.objects.create(
                user=user,
                session_id=f'session_today_{user.id}_{session_num}',
                title=f'今日{function.name}会话',
                function_code=function.function_code,
                started_at=session_start,
                message_count=0
            )
            
            # 创建消息
            msg_count = random.randint(3, 15)
            for msg_num in range(msg_count):
                msg_time = session_start + timedelta(minutes=msg_num * 2)
                
                ChatMessage.objects.create(
                    session=session,
                    message_type='user',
                    content=f'今日用户消息 {msg_num+1}',
                    created_at=msg_time,
                    function_called=function.function_code
                )
                
                ChatMessage.objects.create(
                    session=session,
                    message_type='assistant',
                    content=f'今日AI回复 {msg_num+1}',
                    created_at=msg_time + timedelta(seconds=30),
                    function_called=function.function_code
                )
            
            session.message_count = msg_count * 2
            session.save()
    
    print(f"✅ 创建了今日测试数据")
    
    # 5. 显示统计信息
    total_users = User.objects.filter(user_type='student').count()
    total_sessions = ChatSession.objects.count()
    total_messages = ChatMessage.objects.count()
    today_sessions = ChatSession.objects.filter(started_at__date=today).count()
    
    print("\n📊 数据统计:")
    print(f"   总用户数: {total_users}")
    print(f"   总会话数: {total_sessions}")
    print(f"   总消息数: {total_messages}")
    print(f"   今日会话数: {today_sessions}")
    
    print("\n🎉 仪表板测试数据创建完成!")
    print("现在可以访问 http://localhost:8000/ai_agent/admin/dashboard/ 查看图表效果")

if __name__ == '__main__':
    create_test_data() 