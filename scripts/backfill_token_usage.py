#!/usr/bin/env python
"""
填充用户Token使用统计数据
从现有的ChatMessage记录中生成UserTokenUsage统计数据
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_agent_platform.settings')
django.setup()

from django.contrib.auth import get_user_model
from ai_agent.models import UserTokenUsage
from behavior_tracking.models import ChatMessage, ChatSession
from django.db.models import Sum, Count
from django.db import transaction

User = get_user_model()

def populate_token_usage():
    """填充Token使用统计数据"""
    print("开始填充Token使用统计数据...")
    
    # 获取所有有消息记录的用户
    users_with_messages = User.objects.filter(
        chatsession__chatmessage__isnull=False
    ).distinct()
    
    print(f"找到 {users_with_messages.count()} 个有消息记录的用户")
    
    # 获取最早和最晚的消息时间
    earliest_message = ChatMessage.objects.order_by('created_at').first()
    latest_message = ChatMessage.objects.order_by('-created_at').first()
    
    if not earliest_message:
        print("没有找到任何消息记录")
        return
    
    start_date = earliest_message.created_at.date()
    end_date = latest_message.created_at.date()
    
    print(f"数据时间范围: {start_date} 到 {end_date}")
    
    # 为每个用户生成每日统计
    total_users = users_with_messages.count()
    current_user = 0
    
    for user in users_with_messages:
        current_user += 1
        print(f"处理用户 {current_user}/{total_users}: {user.username}")
        
        # 获取该用户的所有消息日期
        user_message_dates = ChatMessage.objects.filter(
            session__user=user
        ).dates('created_at', 'day')
        
        for date in user_message_dates:
            # 检查是否已存在该日期的统计
            if UserTokenUsage.objects.filter(user=user, date=date).exists():
                print(f"  - 跳过 {date} (已存在)")
                continue
            
            # 计算该日期的统计数据
            day_messages = ChatMessage.objects.filter(
                session__user=user,
                created_at__date=date
            )
            
            # Token统计 - 统计所有消息的Token（用户输入+AI回复）
            total_tokens = day_messages.aggregate(
                total=Sum('tokens_used')
            )['total'] or 0
            
            # 分别统计输入和输出Token
            user_tokens = day_messages.filter(message_type='user').aggregate(
                total=Sum('tokens_used')
            )['total'] or 0
            
            assistant_tokens = day_messages.filter(message_type='assistant').aggregate(
                total=Sum('tokens_used')
            )['total'] or 0
            
            # 会话统计
            day_sessions = ChatSession.objects.filter(
                user=user,
                started_at__date=date
            )
            session_count = day_sessions.count()
            
            # 消息统计
            user_messages = day_messages.filter(message_type='user')
            message_count = user_messages.count()
            
            # 功能使用统计 - 统计所有消息
            function_usage = {}
            function_stats = day_messages.filter(
                function_called__isnull=False
            ).values('function_called').annotate(
                tokens=Sum('tokens_used')
            )
            
            for func_stat in function_stats:
                function_usage[func_stat['function_called']] = func_stat['tokens']
            
            # 创建统计记录
            try:
                with transaction.atomic():
                    UserTokenUsage.objects.create(
                        user=user,
                        date=date,
                        total_tokens=total_tokens,
                        input_tokens=user_tokens,      # 用户输入Token
                        output_tokens=assistant_tokens, # AI回复Token
                        session_count=session_count,
                        message_count=message_count,
                        total_cost=0,  # 暂时设为0，可以后续计算
                        function_usage=function_usage
                    )
                    print(f"  - 创建 {date}: {total_tokens} tokens, {session_count} sessions, {message_count} messages")
            except Exception as e:
                print(f"  - 创建失败 {date}: {str(e)}")
    
    print("\nToken使用统计数据填充完成！")
    
    # 显示统计信息
    total_records = UserTokenUsage.objects.count()
    total_tokens = UserTokenUsage.objects.aggregate(
        total=Sum('total_tokens')
    )['total'] or 0
    
    print(f"\n统计信息:")
    print(f"- 总记录数: {total_records}")
    print(f"- 总Token数: {total_tokens}")
    print(f"- 涉及用户数: {UserTokenUsage.objects.values('user').distinct().count()}")

if __name__ == '__main__':
    populate_token_usage() 