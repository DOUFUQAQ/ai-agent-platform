import json
import time
import uuid
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class DeepSeekAPIClient:
    """DeepSeek API客户端 - 使用OpenAI SDK调用DeepSeek API"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_API_BASE
        )
    
    def chat_completion(self, messages: List[Dict], model: str = "deepseek-chat", 
                       temperature: float = 0.7, max_tokens: int = 4096, stream: bool = False) -> Dict:
        """发送聊天完成请求"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            
            # 如果是非流式响应，转换为字典格式
            if not stream:
                return {
                    'choices': [{
                        'message': {
                            'role': response.choices[0].message.role,
                            'content': response.choices[0].message.content
                        },
                        'finish_reason': response.choices[0].finish_reason
                    }],
                    'usage': {
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': response.usage.total_tokens
                    },
                    'model': response.model,
                    'id': response.id,
                    'created': response.created
                }
            else:
                return response
                
        except Exception as e:
            raise Exception(f"DeepSeek API请求失败: {str(e)}")


class AIAgentService:
    """AI代理服务"""
    
    def __init__(self):
        self.client = DeepSeekAPIClient()
        # 支持的模型配置
        self.models = {
            'chat': 'deepseek-chat',        # DeepSeek-V3-0324
            'reasoning': 'deepseek-reasoner' # DeepSeek-R1-0528
        }
    
    def create_chat_session(self, user: User, function_code: str = None) -> str:
        """创建对话会话"""
        from behavior_tracking.models import ChatSession
        
        session_id = str(uuid.uuid4())
        session = ChatSession.objects.create(
            user=user,
            session_id=session_id,
            title=f"AI对话 - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
        )
        return session_id
    
    def send_message(self, user: User, session_id: str, message: str, 
                    function_code: str = None, model_type: str = 'chat') -> Dict:
        """发送消息并获取AI回复
        
        Args:
            user: 用户对象
            session_id: 会话ID
            message: 用户消息
            function_code: 功能代码
            model_type: 模型类型 ('chat' 或 'reasoning')
        """
        from behavior_tracking.models import ChatSession, ChatMessage
        
        try:
            # 获取会话
            session = ChatSession.objects.get(session_id=session_id, user=user)
            
            # 记录用户消息
            user_message = ChatMessage.objects.create(
                session=session,
                message_type='user',
                content=message,
                function_called=function_code
            )
            
            # 构建消息历史
            messages = self._build_message_history(session, function_code)
            
            # 选择模型
            model = self.models.get(model_type, 'deepseek-chat')
            
            # 调用AI API
            start_time = time.time()
            try:
                response = self.client.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=0.7,
                    max_tokens=4096
                )
                response_time = time.time() - start_time
                
                # 提取回复内容
                ai_response = response['choices'][0]['message']['content']
                tokens_used = response['usage']['total_tokens']
                
                # 记录AI回复
                ai_message = ChatMessage.objects.create(
                    session=session,
                    message_type='assistant',
                    content=ai_response,
                    tokens_used=tokens_used
                )
                
                # 更新会话统计
                session.message_count += 2
                session.total_tokens += tokens_used
                session.save()
                
                # 记录API使用日志
                self._log_api_usage(user, session_id, function_code, response, response_time, True, model)
                
                # 记录用户行为
                self._log_user_behavior(user, 'function_call', {
                    'session_id': session_id,
                    'function_code': function_code,
                    'model_type': model_type,
                    'model': model,
                    'message_length': len(message),
                    'response_length': len(ai_response)
                })
                
                return {
                    'success': True,
                    'response': ai_response,
                    'tokens_used': tokens_used,
                    'response_time': response_time,
                    'model': model
                }
                
            except Exception as e:
                # 记录错误
                self._log_api_usage(user, session_id, function_code, None, 
                                  time.time() - start_time, False, model, str(e))
                raise
                
        except ChatSession.DoesNotExist:
            raise Exception("会话不存在")
    
    def _build_message_history(self, session, function_code: str = None) -> List[Dict]:
        """构建消息历史"""
        messages = []
        
        # 添加系统提示词
        system_prompt = self._get_system_prompt(function_code)
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 获取最近的对话历史（限制数量以控制token使用）
        # 使用正向查询避免负索引问题
        total_messages = session.chatmessage_set.count()
        skip_count = max(0, total_messages - 20)
        chat_messages = session.chatmessage_set.order_by('created_at')[skip_count:]
        
        for msg in chat_messages:
            role = "user" if msg.message_type == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})
        
        return messages
    
    def _get_system_prompt(self, function_code: str = None) -> str:
        """获取系统提示词"""
        base_prompt = """你是一个高校AI助手，专门为学生提供学习和生活支持。
请遵循以下原则：
1. 回答要准确、有帮助，符合高校学生的需求
2. 保持友善、专业的语气
3. 如果不确定答案，请诚实说明
4. 避免提供可能有害或不当的建议
5. 优先使用中文回答
6. 回答要简洁明了，避免过于冗长"""
        
        function_prompts = {
            'course_selection': base_prompt + "\n\n专注于课程选择相关的咨询和建议，包括课程内容、难度、学分、先修要求等信息。",
            'calendar': base_prompt + "\n\n帮助学生进行日程管理和时间规划，包括课程安排、考试时间、作业截止日期等。",
            'email': base_prompt + "\n\n协助处理邮件相关事务，包括邮件撰写、格式规范、沟通技巧等。",
            'study_plan': base_prompt + "\n\n提供学业规划和学习方法指导，包括学习计划制定、学习技巧、复习方法等。",
            'qa': base_prompt + "\n\n回答各类学习和生活问题，提供全面的支持和建议。",
            'reasoning': base_prompt + "\n\n进行深度思考和推理，分析复杂问题，提供详细的解决方案和论证过程。"
        }
        
        return function_prompts.get(function_code, base_prompt)
    
    def _log_api_usage(self, user: User, session_id: str, function_code: str, 
                      response: Dict, response_time: float, is_success: bool, 
                      model: str = 'deepseek-chat', error_message: str = None):
        """记录API使用情况"""
        from ai_agent.models import APIUsageLog, AIModel, AIFunction
        
        try:
            # 获取模型和功能信息
            model_obj, _ = AIModel.objects.get_or_create(
                model_id=model,
                defaults={
                    'name': f'DeepSeek {model.split("-")[-1].title()}',
                    'provider': 'DeepSeek',
                    'api_endpoint': settings.DEEPSEEK_API_BASE
                }
            )
            
            function, _ = AIFunction.objects.get_or_create(
                code=function_code or 'general',
                defaults={
                    'name': '通用对话',
                    'function_type': 'qa',
                    'description': '通用AI对话功能',
                    'prompt_template': ''
                }
            )
            
            if is_success and response:
                usage = response.get('usage', {})
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)
                total_tokens = usage.get('total_tokens', 0)
                cost = self._calculate_cost(input_tokens, output_tokens, model)
            else:
                input_tokens = output_tokens = total_tokens = 0
                cost = 0.0
            
            # 创建使用日志
            APIUsageLog.objects.create(
                user=user,
                session_id=session_id,
                model=model_obj,
                function=function,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                response_time=response_time,
                is_success=is_success,
                error_message=error_message,
                cost=cost
            )
        except Exception as e:
            # 记录日志失败不应该影响主要功能
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"记录API使用日志失败: {str(e)}")

    def _calculate_cost(self, input_tokens: int, output_tokens: int, model: str = 'deepseek-chat') -> float:
        """计算API调用成本"""
        # DeepSeek API 价格 (每1K tokens)
        # 这里使用估算价格，实际价格请参考 DeepSeek 官网
        pricing = {
            'deepseek-chat': {'input': 0.0002, 'output': 0.0004},      # $0.2/$0.4 per 1K tokens
            'deepseek-reasoner': {'input': 0.0005, 'output': 0.001}    # $0.5/$1.0 per 1K tokens
        }
        
        model_pricing = pricing.get(model, pricing['deepseek-chat'])
        input_cost = (input_tokens / 1000) * model_pricing['input']
        output_cost = (output_tokens / 1000) * model_pricing['output']
        
        return input_cost + output_cost
    
    def _log_user_behavior(self, user: User, action_type: str, action_detail: Dict):
        """记录用户行为"""
        from behavior_tracking.models import UserBehaviorLog
        
        try:
            UserBehaviorLog.objects.create(
                user=user,
                action_type=action_type,
                action_detail=json.dumps(action_detail, ensure_ascii=False)
            )
        except Exception as e:
            print(f"记录用户行为失败: {e}")
    
    def get_user_chat_history(self, user: User, session_id: str = None, limit: int = 50) -> List[Dict]:
        """获取用户对话历史"""
        from behavior_tracking.models import ChatSession, ChatMessage
        
        if session_id:
            # 获取指定会话的消息
            try:
                session = ChatSession.objects.get(session_id=session_id, user=user)
                messages = session.chatmessage_set.order_by('created_at')[:limit]
                return [
                    {
                        'message_type': msg.message_type,
                        'content': msg.content,
                        'created_at': msg.created_at.isoformat(),
                        'session_id': msg.session.session_id
                    }
                    for msg in messages
                ]
            except ChatSession.DoesNotExist:
                return []
        else:
            # 获取用户的会话列表（而不是消息列表）
            sessions = ChatSession.objects.filter(user=user).order_by('-started_at')[:limit]
            
            result = []
            for session in sessions:
                # 获取该会话的所有消息
                messages = session.chatmessage_set.order_by('created_at')
                
                session_data = {
                    'session_id': session.session_id,
                    'title': session.title,
                    'function_code': session.function_code,
                    'started_at': session.started_at.isoformat(),
                    'created_at': session.started_at.isoformat(),  # 兼容前端
                    'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                    'message_count': session.message_count,
                    'total_tokens': session.total_tokens,
                    'is_active': session.is_active,
                    'messages': [
                        {
                            'message_type': msg.message_type,
                            'content': msg.content,
                            'created_at': msg.created_at.isoformat(),
                            'session_id': msg.session.session_id
                        }
                        for msg in messages
                    ]
                }
                result.append(session_data)
            
            return result
    
    def end_chat_session(self, user: User, session_id: str, delete_session: bool = False):
        """结束对话会话"""
        from behavior_tracking.models import ChatSession
        
        try:
            session = ChatSession.objects.get(session_id=session_id, user=user)
            
            if delete_session:
                # 真正删除会话和相关消息
                self._log_user_behavior(user, 'chat_delete', {'session_id': session_id})
                session.delete()  # 这会级联删除相关的消息
            else:
                # 只是标记为结束
                session.ended_at = timezone.now()
                session.is_active = False
                session.save()
                
                # 记录用户行为
                self._log_user_behavior(user, 'chat_end', {'session_id': session_id})
            
        except ChatSession.DoesNotExist:
            pass 


class UserTokenService:
    """用户Token使用统计服务"""
    
    @staticmethod
    def update_daily_usage(user, date, tokens_used, session_count=0, message_count=0, function_code=None, cost=0):
        """更新用户每日Token使用统计"""
        from ai_agent.models import UserTokenUsage
        from django.db import transaction
        
        try:
            with transaction.atomic():
                usage, created = UserTokenUsage.objects.get_or_create(
                    user=user,
                    date=date,
                    defaults={
                        'total_tokens': tokens_used,
                        'session_count': session_count,
                        'message_count': message_count,
                        'total_cost': cost,
                        'function_usage': {}
                    }
                )
                
                if not created:
                    # 更新现有记录
                    usage.total_tokens += tokens_used
                    usage.session_count += session_count
                    usage.message_count += message_count
                    usage.total_cost += cost
                    
                    # 更新功能使用统计
                    if function_code:
                        if not usage.function_usage:
                            usage.function_usage = {}
                        
                        if function_code in usage.function_usage:
                            usage.function_usage[function_code] += tokens_used
                        else:
                            usage.function_usage[function_code] = tokens_used
                    
                    usage.save()
                else:
                    # 新记录，设置功能使用统计
                    if function_code:
                        usage.function_usage = {function_code: tokens_used}
                        usage.save()
                
                return usage
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"更新用户Token使用统计失败: {str(e)}")
            return None
    
    @staticmethod
    def get_user_token_stats(user, days=30):
        """获取用户Token使用统计"""
        from ai_agent.models import UserTokenUsage
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # 获取期间内的统计数据
        usage_records = UserTokenUsage.objects.filter(
            user=user,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        # 计算总计
        total_tokens = sum(record.total_tokens for record in usage_records)
        total_sessions = sum(record.session_count for record in usage_records)
        total_messages = sum(record.message_count for record in usage_records)
        total_cost = sum(record.total_cost for record in usage_records)
        
        # 构建每日数据
        daily_data = []
        current_date = start_date
        
        while current_date <= end_date:
            day_record = next((r for r in usage_records if r.date == current_date), None)
            daily_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'tokens': day_record.total_tokens if day_record else 0,
                'sessions': day_record.session_count if day_record else 0,
                'messages': day_record.message_count if day_record else 0,
                'cost': float(day_record.total_cost) if day_record else 0
            })
            current_date += timedelta(days=1)
        
        # 功能使用统计
        function_stats = {}
        for record in usage_records:
            if record.function_usage:
                for func_code, tokens in record.function_usage.items():
                    if func_code in function_stats:
                        function_stats[func_code] += tokens
                    else:
                        function_stats[func_code] = tokens
        
        return {
            'total_tokens': total_tokens,
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'total_cost': float(total_cost),
            'daily_data': daily_data,
            'function_stats': function_stats,
            'period_days': days
        }
    
    @staticmethod
    def get_user_ranking(user):
        """获取用户在所有用户中的Token使用排名"""
        from ai_agent.models import UserTokenUsage
        from django.db.models import Sum
        
        # 计算所有用户的总Token使用量
        user_totals = UserTokenUsage.objects.values('user').annotate(
            total_tokens=Sum('total_tokens')
        ).order_by('-total_tokens')
        
        # 找到当前用户的排名
        user_total = UserTokenUsage.objects.filter(user=user).aggregate(
            total_tokens=Sum('total_tokens')
        )['total_tokens'] or 0
        
        rank = 1
        for user_data in user_totals:
            if user_data['total_tokens'] > user_total:
                rank += 1
            else:
                break
        
        return {
            'rank': rank,
            'total_users': len(user_totals),
            'user_tokens': user_total
        } 