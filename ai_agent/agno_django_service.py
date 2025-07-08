"""
Django + Agno集成服务
使用您的Agno API密钥在Django项目中集成Agno智能体
"""

import json
import os
import time
import uuid
from typing import Dict, List, Optional
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

# Agno 平台密钥从环境变量读取，避免把凭据写进仓库
AGNO_API_KEY = os.getenv("AGNO_API_KEY", "")

try:
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from agno.tools.reasoning import ReasoningTools
    from agno.tools.duckduckgo import DuckDuckGoTools
    from agno.team import Team
    AGNO_AVAILABLE = True
    print("✅ Agno SDK可用")
except ImportError:
    AGNO_AVAILABLE = False
    print("❌ Agno SDK未安装，请运行: pip install agno")

User = get_user_model()


class AgnoDjangoService:
    """Django + Agno集成服务"""
    
    def __init__(self):
        if not AGNO_AVAILABLE:
            raise ImportError("Agno SDK未安装")
        
        self.api_key = AGNO_API_KEY
        self.agents = {}  # 智能体缓存
        self.teams = {}   # 团队缓存
        
        print(f"🔑 使用Agno API密钥: {self.api_key[:15]}...{self.api_key[-10:]}")
    
    def get_agent(self, agent_type: str = "chat", user_id: str = None) -> Agent:
        """获取或创建智能体"""
        agent_key = f"{agent_type}_{user_id}" if user_id else agent_type
        
        if agent_key not in self.agents:
            self.agents[agent_key] = self._create_agent(agent_type)
            print(f"🤖 创建新智能体: {agent_type}")
        
        return self.agents[agent_key]
    
    def _create_agent(self, agent_type: str) -> Agent:
        """创建不同类型的智能体"""
        
        # 使用您的Agno API密钥创建模型
        model = OpenAIChat(
            id="gpt-4o",
            api_key=self.api_key
        )
        
        # 根据类型配置智能体
        if agent_type == "reasoning":
            # 推理智能体
            agent = Agent(
                name="推理专家",
                model=model,
                tools=[ReasoningTools(add_instructions=True)],
                instructions=[
                    "你是一个具有高级推理能力的AI助手",
                    "使用推理工具分析复杂问题",
                    "提供详细的思考过程"
                ],
                markdown=True,
                show_tool_calls=True
            )
            
        elif agent_type == "research":
            # 研究智能体
            agent = Agent(
                name="研究助手",
                model=model,
                tools=[DuckDuckGoTools()],
                instructions=[
                    "你是一个专业的研究助手",
                    "擅长搜索和分析信息",
                    "总是提供可靠的来源"
                ],
                markdown=True,
                show_tool_calls=True
            )
            
        elif agent_type == "tutor":
            # 学习导师
            agent = Agent(
                name="学习导师",
                model=model,
                tools=[ReasoningTools(), DuckDuckGoTools()],
                instructions=[
                    "你是一个专业的学习导师",
                    "擅长解释复杂概念",
                    "根据学生水平调整教学方式",
                    "鼓励学生主动思考"
                ],
                markdown=True,
                show_tool_calls=True
            )
            
        else:
            # 默认聊天智能体
            agent = Agent(
                name="通用助手",
                model=model,
                instructions=[
                    "你是一个友善、专业的AI助手",
                    "为高校学生提供学习和生活支持",
                    "保持积极正面的态度"
                ],
                markdown=True
            )
        
        return agent
    
    def create_agent_team(self, team_type: str = "research") -> Team:
        """创建智能体团队"""
        if team_type not in self.teams:
            
            model = OpenAIChat(id="gpt-4o", api_key=self.api_key)
            
            if team_type == "research":
                # 研究团队
                research_agent = Agent(
                    name="信息收集专家",
                    model=model,
                    tools=[DuckDuckGoTools()],
                    instructions=["专门负责收集和整理信息"]
                )
                
                analysis_agent = Agent(
                    name="分析专家", 
                    model=model,
                    tools=[ReasoningTools()],
                    instructions=["专门负责分析和推理"]
                )
                
                team = Team(
                    name="研究团队",
                    members=[research_agent, analysis_agent],
                    model=model,
                    instructions=[
                        "协作完成研究任务",
                        "确保信息准确完整",
                        "提供深入分析"
                    ],
                    show_tool_calls=True,
                    markdown=True
                )
                
            else:
                # 默认协作团队
                chat_agent = self.get_agent("chat")
                reasoning_agent = self.get_agent("reasoning")
                
                team = Team(
                    name="协作团队",
                    members=[chat_agent, reasoning_agent],
                    model=model,
                    instructions=["协作解决用户问题"],
                    show_tool_calls=True,
                    markdown=True
                )
            
            self.teams[team_type] = team
            print(f"👥 创建智能体团队: {team_type}")
        
        return self.teams[team_type]
    
    def send_message(self, user: User, session_id: str, message: str, 
                    function_code: str = None, agent_type: str = 'chat',
                    use_team: bool = False) -> Dict:
        """发送消息并获取AI回复"""
        from behavior_tracking.models import ChatSession, ChatMessage
        
        try:
            # 获取会话
            session = ChatSession.objects.get(session_id=session_id, user=user)
            
            # 记录用户消息
            user_tokens = len(message) // 4  # 估算用户输入Token
            user_message = ChatMessage.objects.create(
                session=session,
                message_type='user',
                content=message,
                tokens_used=user_tokens,
                function_called=function_code
            )
            
            print(f"💬 用户消息: {message[:50]}...")
            print(f"🤖 使用智能体类型: {agent_type}")
            print(f"👥 使用团队模式: {use_team}")
            
            # 获取AI实体
            start_time = time.time()
            
            if use_team:
                ai_entity = self.create_agent_team(agent_type)
                ai_type = f"Team({agent_type})"
            else:
                ai_entity = self.get_agent(agent_type, str(user.id))
                ai_type = f"Agent({agent_type})"
            
            try:
                # 调用Agno AI
                print(f"🚀 调用Agno {ai_type}...")
                response = ai_entity.run(message)
                response_time = time.time() - start_time
                
                # 提取回复内容
                ai_response = response.content if hasattr(response, 'content') else str(response)
                ai_tokens = len(ai_response) // 4  # 估算AI回复Token
                total_tokens = user_tokens + ai_tokens  # 总Token = 用户输入 + AI回复
                
                print(f"✅ AI回复: {ai_response[:100]}...")
                print(f"⏱️ 响应时间: {response_time:.2f}秒")
                print(f"📊 Token使用: {user_tokens}(用户) + {ai_tokens}(AI) = {total_tokens}")
                
                # 记录AI回复
                ai_message = ChatMessage.objects.create(
                    session=session,
                    message_type='assistant',
                    content=ai_response,
                    tokens_used=ai_tokens,
                    response_time=response_time
                )
                
                # 更新会话统计
                session.message_count += 2
                session.total_tokens = (session.total_tokens or 0) + total_tokens
                session.save()
                
                return {
                    'success': True,
                    'response': ai_response,
                    'tokens_used': total_tokens,
                    'user_tokens': user_tokens,
                    'ai_tokens': ai_tokens,
                    'response_time': response_time,
                    'agent_type': agent_type,
                    'use_team': use_team,
                    'ai_type': ai_type,
                    'framework': 'agno'
                }
                
            except Exception as e:
                print(f"❌ Agno调用失败: {e}")
                raise Exception(f"Agno AI调用失败: {str(e)}")
                
        except ChatSession.DoesNotExist:
            raise Exception("会话不存在")
    
    def create_chat_session(self, user: User, function_code: str = None) -> str:
        """创建对话会话"""
        from behavior_tracking.models import ChatSession
        
        session_id = str(uuid.uuid4())
        session = ChatSession.objects.create(
            user=user,
            session_id=session_id,
            title=f"Agno智能体对话 - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        print(f"🆕 创建新会话: {session_id}")
        return session_id
    
    def get_available_agents(self) -> List[Dict]:
        """获取可用的智能体类型"""
        return [
            {
                'type': 'chat',
                'name': '通用助手',
                'description': '友善的AI助手，适合日常对话',
                'tools': ['基础对话'],
                'icon': '💬'
            },
            {
                'type': 'reasoning',
                'name': '推理专家',
                'description': '具有高级推理能力，适合复杂问题分析',
                'tools': ['推理工具', '逻辑分析'],
                'icon': '🧠'
            },
            {
                'type': 'research',
                'name': '研究助手',
                'description': '专业研究能力，擅长信息收集和分析',
                'tools': ['网络搜索', '信息整理'],
                'icon': '🔍'
            },
            {
                'type': 'tutor',
                'name': '学习导师',
                'description': '专业教学智能体，提供个性化学习指导',
                'tools': ['推理工具', '网络搜索', '教学方法'],
                'icon': '👨‍🏫'
            }
        ]
    
    def get_available_teams(self) -> List[Dict]:
        """获取可用的智能体团队"""
        return [
            {
                'type': 'research',
                'name': '研究团队',
                'description': '信息收集+分析专家组合，适合深度研究',
                'members': ['信息收集专家', '分析专家'],
                'icon': '👥'
            },
            {
                'type': 'collaborative',
                'name': '协作团队',
                'description': '通用助手+推理专家组合，适合综合任务',
                'members': ['通用助手', '推理专家'],
                'icon': '🤝'
            }
        ]


# 全局服务实例
def get_agno_service():
    """获取Agno服务实例"""
    if AGNO_AVAILABLE:
        return AgnoDjangoService()
    else:
        raise ImportError("Agno SDK未安装，请运行: pip install agno")


# 测试函数
def test_agno_service():
    """测试Agno服务"""
    print("🧪 开始测试Agno Django服务...")
    
    try:
        service = get_agno_service()
        
        # 测试创建智能体
        chat_agent = service.get_agent("chat")
        print(f"✅ 聊天智能体创建成功: {chat_agent.name}")
        
        reasoning_agent = service.get_agent("reasoning")
        print(f"✅ 推理智能体创建成功: {reasoning_agent.name}")
        
        # 测试创建团队
        research_team = service.create_agent_team("research")
        print(f"✅ 研究团队创建成功: {research_team.name}")
        
        # 测试简单对话
        print("\n💬 测试简单对话...")
        response = chat_agent.run("你好，请简单介绍一下Agno平台")
        print(f"🤖 AI回复: {response.content}")
        
        print("\n🎉 Agno服务测试成功！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    test_agno_service() 