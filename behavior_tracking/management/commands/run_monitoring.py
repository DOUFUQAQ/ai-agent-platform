"""
运行监控系统的管理命令
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from behavior_tracking.models import ChatMessage
from behavior_tracking.monitoring import monitoring_service


class Command(BaseCommand):
    help = '运行监控系统'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=1,
            help='检查过去多少小时的消息（默认1小时）'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        
        self.stdout.write(
            self.style.SUCCESS(f'开始监控过去{hours}小时的消息...')
        )
        
        # 获取需要检查的消息
        since = timezone.now() - timezone.timedelta(hours=hours)
        messages = ChatMessage.objects.filter(
            created_at__gte=since,
            message_type='user',
            is_flagged=False
        )
        
        checked_count = 0
        flagged_count = 0
        
        for message in messages:
            results = monitoring_service.process_new_message(message)
            checked_count += 1
            
            if results.get('sensitive_word', {}).get('detected', False):
                flagged_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'发现敏感内容: 用户 {message.session.user.username} - '
                        f'严重程度: {results["sensitive_word"]["severity"]}'
                    )
                )
        
        # 显示统计信息
        stats = monitoring_service.get_monitoring_stats()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n监控完成:\n'
                f'- 检查消息数: {checked_count}\n'
                f'- 标记消息数: {flagged_count}\n'
                f'- 今日敏感词检测: {stats["today"]["sensitive_detections"]}\n'
                f'- 待审核敏感词: {stats["pending_review"]["sensitive_words"]}'
            )
        ) 