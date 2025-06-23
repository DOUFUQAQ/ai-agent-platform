from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, datetime
import random
import string
import uuid

from behavior_tracking.models import (
    ChatSession, ChatMessage, UserBehaviorLog,
    SensitiveWordDetection, AbnormalBehaviorDetection,
    FunctionUsageStatistics
)
from permissions.models import AIFunction

User = get_user_model()


class Command(BaseCommand):
    help = '创建行为分析测试数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users', 
            type=int, 
            default=20,
            help='创建的测试用户数量'
        )
        parser.add_argument(
            '--sessions', 
            type=int, 
            default=100,
            help='创建的会话数量'
        )
        parser.add_argument(
            '--days', 
            type=int, 
            default=30,
            help='生成数据的天数范围'
        )

    def handle(self, *args, **options):
        users_count = options['users']
        sessions_count = options['sessions']
        days_back = options['days']
        
        self.stdout.write(self.style.SUCCESS(f'开始创建行为分析测试数据...'))
        self.stdout.write(f'用户数量: {users_count}, 会话数量: {sessions_count}, 时间范围: {days_back}天')
        
        # 1. 创建测试用户
        self.create_test_users(users_count)
        
        # 2. 确保AI功能存在
        self.ensure_ai_functions()
        
        # 3. 创建会话和消息
        self.create_chat_sessions(sessions_count, days_back)
        
        # 4. 创建用户行为日志
        self.create_behavior_logs(days_back)
        
        # 5. 创建一些异常行为检测记录
        self.create_abnormal_behaviors()
        
        # 6. 创建敏感内容检测记录
        self.create_sensitive_detections()
        
        self.stdout.write(self.style.SUCCESS('✅ 行为分析测试数据创建完成！'))

    def create_test_users(self, count):
        """创建测试用户"""
        self.stdout.write('创建测试用户...')
        
        created_count = 0
        for i in range(count):
            username = f'test_user_{i+1:03d}'
            
            # 检查用户是否已存在
            if User.objects.filter(username=username).exists():
                continue
                
            user = User.objects.create_user(
                username=username,
                password='testpass123',
                email=f'{username}@test.com',
                user_type=random.choice(['student', 'teacher']),
                first_name=f'测试用户{i+1}',
                is_active=True
            )
            created_count += 1
        
        self.stdout.write(f'✓ 创建了 {created_count} 个测试用户')

    def ensure_ai_functions(self):
        """确保AI功能存在"""
        functions = [
            ('basic_chat', '基础聊天'),
            ('agno_chat', '智能助手'),
            ('code_assistant', '代码助手'),
            ('learning_assistant', '学习助手'),
            ('research_assistant', '研究助手'),
            ('creative_assistant', '创意助手'),
            ('voice_chat', '语音对话'),
            ('image_generation', '图像生成'),
            ('file_upload', '文件上传'),
            ('advanced_analysis', '高级分析'),
        ]
        
        for code, name in functions:
            AIFunction.objects.get_or_create(
                function_code=code,
                defaults={
                    'name': name,
                    'description': f'{name}功能',
                    'function_type': 'qa',
                    'is_active': True,
                    'is_beta': random.choice([True, False])
                }
            )

    def create_chat_sessions(self, count, days_back):
        """创建聊天会话和消息"""
        self.stdout.write('创建聊天会话和消息...')
        
        users = User.objects.filter(user_type='student')
        if not users.exists():
            self.stdout.write(self.style.WARNING('没有找到学生用户，跳过会话创建'))
            return
        
        functions = list(AIFunction.objects.all())
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days_back)
        
        created_sessions = 0
        created_messages = 0
        
        for i in range(count):
            # 随机选择用户和时间
            user = random.choice(users)
            session_time = self.random_datetime(start_date, end_date)
            
            # 创建会话
            session = ChatSession.objects.create(
                user=user,
                session_id=str(uuid.uuid4()),
                title=f'会话{i+1}',
                function_code=random.choice(functions).function_code if functions else None,
                started_at=session_time,
                ended_at=session_time + timedelta(minutes=random.randint(2, 60)),
                is_active=random.choice([True, False]),
                ip_address=self.random_ip(),
                user_agent='Test User Agent'
            )
            created_sessions += 1
            
            # 为会话创建消息
            message_count = random.randint(2, 20)
            session_messages = 0
            
            for j in range(message_count):
                message_time = session_time + timedelta(seconds=j * random.randint(10, 120))
                
                # 用户消息
                user_message = ChatMessage.objects.create(
                    session=session,
                    message_type='user',
                    content=self.random_user_message(),
                    tokens_used=random.randint(10, 100),
                    created_at=message_time
                )
                session_messages += 1
                created_messages += 1
                
                # AI回复
                ai_message = ChatMessage.objects.create(
                    session=session,
                    message_type='assistant',
                    content=self.random_ai_response(),
                    tokens_used=random.randint(50, 300),
                    response_time=random.uniform(0.5, 3.0),
                    created_at=message_time + timedelta(seconds=random.randint(1, 5))
                )
                session_messages += 1
                created_messages += 1
            
            # 更新会话消息计数
            session.message_count = session_messages
            session.total_tokens = session_messages * random.randint(50, 200)
            session.save()
        
        self.stdout.write(f'✓ 创建了 {created_sessions} 个会话，{created_messages} 条消息')

    def create_behavior_logs(self, days_back):
        """创建用户行为日志"""
        self.stdout.write('创建用户行为日志...')
        
        users = User.objects.all()
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days_back)
        
        actions = ['login', 'logout', 'chat_start', 'chat_end', 'function_call']
        created_count = 0
        
        for user in users:
            # 为每个用户创建一些行为日志
            log_count = random.randint(5, 30)
            
            for _ in range(log_count):
                log_time = self.random_datetime(start_date, end_date)
                
                UserBehaviorLog.objects.create(
                    user=user,
                    action_type=random.choice(actions),
                    action_detail=f'用户{user.username}执行了操作',
                    ip_address=self.random_ip(),
                    user_agent='Test User Agent',
                    created_at=log_time
                )
                created_count += 1
        
        self.stdout.write(f'✓ 创建了 {created_count} 个行为日志')

    def create_abnormal_behaviors(self):
        """创建异常行为检测记录"""
        self.stdout.write('创建异常行为检测记录...')
        
        users = User.objects.filter(user_type='student')[:5]  # 只为部分用户创建异常
        behavior_types = ['high_frequency', 'unusual_time', 'resource_abuse', 'suspicious_pattern']
        
        created_count = 0
        for user in users:
            for _ in range(random.randint(1, 3)):
                behavior_type = random.choice(behavior_types)
                risk_score = random.randint(30, 95)
                
                AbnormalBehaviorDetection.objects.create(
                    user=user,
                    behavior_type=behavior_type,
                    description=f'检测到用户{user.username}存在{behavior_type}异常行为',
                    detection_data={
                        'threshold': random.randint(50, 100),
                        'actual_value': random.randint(60, 150),
                        'time_period': '1_hour'
                    },
                    risk_score=risk_score,
                    is_confirmed=random.choice([True, False]),
                    is_handled=random.choice([True, False])
                )
                created_count += 1
        
        self.stdout.write(f'✓ 创建了 {created_count} 个异常行为检测记录')

    def create_sensitive_detections(self):
        """创建敏感内容检测记录 - 已禁用，使用真实检测"""
        self.stdout.write('跳过创建敏感内容检测记录...')
        self.stdout.write('系统现在使用真实的敏感词检测，不再创建模拟数据。')
        self.stdout.write('敏感内容将在用户发送消息时自动检测并记录。')

    def random_datetime(self, start, end):
        """生成随机时间"""
        time_between = end - start
        total_seconds = int(time_between.total_seconds())
        
        if total_seconds <= 0:
            return start
        
        random_seconds = random.randrange(total_seconds)
        return start + timedelta(seconds=random_seconds)

    def random_ip(self):
        """生成随机IP地址"""
        return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

    def random_user_message(self):
        """生成随机用户消息"""
        messages = [
            "请帮我解答这个问题",
            "我需要了解关于人工智能的知识",
            "能帮我写一段代码吗？",
            "请解释一下这个概念",
            "我有一个项目需要帮助",
            "能给我一些学习建议吗？",
            "请帮我分析这个数据",
            "我想了解更多相关信息",
            "能帮我解决这个难题吗？",
            "请为我提供一些资源"
        ]
        return random.choice(messages)

    def random_ai_response(self):
        """生成随机AI回复"""
        responses = [
            "我很乐意帮助您解答这个问题。根据您的需求...",
            "关于人工智能，这是一个非常有趣的领域...",
            "当然可以！以下是相关的代码示例...",
            "让我为您详细解释这个概念...",
            "关于您的项目，我建议您可以考虑以下几个方面...",
            "基于您的情况，我推荐以下学习路径...",
            "根据数据分析，我发现了以下几个关键点...",
            "我为您整理了一些相关的信息和资源...",
            "这确实是一个有挑战性的问题，让我们一步步来解决...",
            "以下是一些优质的学习资源，希望对您有所帮助..."
        ]
        return random.choice(responses) 