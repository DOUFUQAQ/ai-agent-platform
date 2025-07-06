from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from ai_agent.models import UserTokenUsage
from behavior_tracking.models import ChatMessage, ChatSession

User = get_user_model()

class Command(BaseCommand):
    help = '更新用户Token使用统计数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='更新最近N天的数据（默认7天）'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='只更新指定用户的数据'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新计算已存在的数据'
        )

    def handle(self, *args, **options):
        days = options['days']
        user_filter = options['user']
        force_update = options['force']
        
        self.stdout.write(f"开始更新Token使用统计数据（最近{days}天）...")
        
        # 计算日期范围
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        self.stdout.write(f"更新日期范围: {start_date} 到 {end_date}")
        
        # 获取要更新的用户
        users_query = User.objects.filter(
            chatsession__chatmessage__isnull=False
        ).distinct()
        
        if user_filter:
            users_query = users_query.filter(username=user_filter)
        
        users = list(users_query)
        total_users = len(users)
        
        if total_users == 0:
            self.stdout.write(self.style.WARNING("没有找到需要更新的用户"))
            return
        
        self.stdout.write(f"找到 {total_users} 个用户需要更新")
        
        # 统计计数器
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        # 为每个用户更新统计
        for i, user in enumerate(users, 1):
            self.stdout.write(f"处理用户 {i}/{total_users}: {user.username}")
            
            # 获取该用户在指定日期范围内的消息日期
            user_message_dates = ChatMessage.objects.filter(
                session__user=user,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            ).dates('created_at', 'day')
            
            for date in user_message_dates:
                # 检查是否已存在该日期的统计
                existing_usage = UserTokenUsage.objects.filter(
                    user=user, 
                    date=date
                ).first()
                
                if existing_usage and not force_update:
                    self.stdout.write(f"  - 跳过 {date} (已存在)")
                    skipped_count += 1
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
                
                # 创建或更新统计记录
                try:
                    with transaction.atomic():
                        if existing_usage:
                            # 更新现有记录
                            existing_usage.total_tokens = total_tokens
                            existing_usage.input_tokens = user_tokens
                            existing_usage.output_tokens = assistant_tokens
                            existing_usage.session_count = session_count
                            existing_usage.message_count = message_count
                            existing_usage.function_usage = function_usage
                            existing_usage.save()
                            
                            self.stdout.write(f"  - 更新 {date}: {total_tokens} tokens, {session_count} sessions, {message_count} messages")
                            updated_count += 1
                        else:
                            # 创建新记录
                            UserTokenUsage.objects.create(
                                user=user,
                                date=date,
                                total_tokens=total_tokens,
                                input_tokens=user_tokens,      # 用户输入Token
                                output_tokens=assistant_tokens, # AI回复Token
                                session_count=session_count,
                                message_count=message_count,
                                total_cost=0,  # 暂时设为0
                                function_usage=function_usage
                            )
                            
                            self.stdout.write(f"  - 创建 {date}: {total_tokens} tokens, {session_count} sessions, {message_count} messages")
                            created_count += 1
                            
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  - 处理失败 {date}: {str(e)}")
                    )
        
        # 输出统计结果
        self.stdout.write(
            self.style.SUCCESS(
                f"\nToken使用统计数据更新完成！\n"
                f"- 新创建记录: {created_count}\n"
                f"- 更新记录: {updated_count}\n"
                f"- 跳过记录: {skipped_count}\n"
                f"- 总处理记录: {created_count + updated_count + skipped_count}"
            )
        )
        
        # 显示总体统计信息
        total_records = UserTokenUsage.objects.count()
        total_tokens = UserTokenUsage.objects.aggregate(
            total=Sum('total_tokens')
        )['total'] or 0
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n系统总统计信息:\n"
                f"- 总记录数: {total_records}\n"
                f"- 总Token数: {total_tokens:,}\n"
                f"- 涉及用户数: {UserTokenUsage.objects.values('user').distinct().count()}"
            )
        ) 