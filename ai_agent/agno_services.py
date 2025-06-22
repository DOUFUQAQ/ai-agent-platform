"""
正确的Agno服务类
使用真实的OpenAI API密钥
"""

import os
from typing import Dict, Optional, List
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class AgnoService:
    """
    Agno AI智能体服务类
    使用真实的OpenAI API密钥
    """
    
    def __init__(self):
        self.agents = {}
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        
        if not self.api_key:
            raise ValueError("未配置OpenAI API密钥，请在settings.py中设置OPENAI_API_KEY")
    
    def get_agent(self, agent_type: str = "chat"):
        """获取或创建智能体"""
        if agent_type not in self.agents:
            try:
                from agno.agent import Agent
                from agno.models.openai import OpenAIChat
                
                # 创建OpenAI模型
                model = OpenAIChat(
                    id="gpt-4o-mini",  # 使用更便宜的模型
                    api_key=self.api_key
                )
                
                # 根据类型配置不同的智能体
                if agent_type == "chat":
                    agent = Agent(
                        model=model,
                        instructions=[
                            "你是一个有用的AI助手",
                            "请用中文回答问题",
                            "保持回答简洁明了"
                        ],
                        markdown=True
                    )
                elif agent_type == "reasoning":
                    from agno.tools.reasoning import ReasoningTools
                    agent = Agent(
                        model=model,
                        tools=[ReasoningTools()],
                        instructions=[
                            "你是一个具有推理能力的AI助手",
                            "对于复杂问题，请先分析再给出答案",
                            "使用逻辑推理解决问题"
                        ],
                        markdown=True
                    )
                elif agent_type == "tutor":
                    agent = Agent(
                        model=model,
                        instructions=[
                            "你是一个专业的教学助手",
                            "善于解释复杂概念",
                            "提供循序渐进的学习指导",
                            "鼓励学生思考和提问"
                        ],
                        markdown=True
                    )
                else:
                    # 默认聊天智能体
                    agent = Agent(
                        model=model,
                        instructions=["你是一个有用的AI助手"],
                        markdown=True
                    )
                
                self.agents[agent_type] = agent
                logger.info(f"成功创建{agent_type}类型的智能体")
                
            except ImportError as e:
                logger.error(f"Agno导入失败: {e}")
                raise ValueError(f"Agno框架未正确安装: {e}")
            except Exception as e:
                logger.error(f"创建智能体失败: {e}")
                raise ValueError(f"创建智能体失败: {e}")
        
        return self.agents[agent_type]
    
    def chat(self, message: str, agent_type: str = "chat", user_id: Optional[int] = None) -> str:
        """与智能体对话"""
        try:
            agent = self.get_agent(agent_type)
            
            # 添加用户上下文
            if user_id:
                context_message = f"用户ID: {user_id}\n问题: {message}"
            else:
                context_message = message
            
            response = agent.run(context_message)
            
            logger.info(f"智能体{agent_type}成功处理消息")
            return response.content
            
        except Exception as e:
            logger.error(f"智能体对话失败: {e}")
            return f"抱歉，处理您的请求时出现了错误: {str(e)}"
    
    def get_available_agents(self) -> List[str]:
        """获取可用的智能体类型"""
        return ["chat", "reasoning", "tutor"]
    
    def reset_agent(self, agent_type: str):
        """重置指定类型的智能体"""
        if agent_type in self.agents:
            del self.agents[agent_type]
            logger.info(f"已重置{agent_type}类型的智能体")
    
    def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        result = {
            "api_key_configured": bool(self.api_key),
            "agno_available": False,
            "openai_connection": False
        }
        
        try:
            from agno.agent import Agent
            from agno.models.openai import OpenAIChat
            result["agno_available"] = True
            
            # 测试OpenAI连接
            model = OpenAIChat(
                id="gpt-4o-mini",
                api_key=self.api_key
            )
            
            agent = Agent(
                model=model,
                instructions=["简短回答"]
            )
            
            response = agent.run("Hello")
            if response and response.content:
                result["openai_connection"] = True
                
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
        
        return result


# 全局服务实例
try:
    agno_service = AgnoService()
    logger.info("Agno服务初始化成功")
    AGNO_AVAILABLE = True
except Exception as e:
    logger.error(f"Agno服务初始化失败: {e}")
    agno_service = None
    AGNO_AVAILABLE = False


def get_ai_service():
    """获取AI服务实例"""
    if AGNO_AVAILABLE and agno_service:
        return agno_service
    else:
        # 回退到原有的DeepSeek服务
        from .services import AIAgentService
        return AIAgentService() 