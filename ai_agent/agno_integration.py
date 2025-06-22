"""
Agno框架集成示例
演示如何在Django项目中使用Agno代替DeepSeek
"""

# 1. 安装依赖
# pip install agno

# 2. 基础Agno智能体示例
def basic_agno_example():
    """基础Agno智能体使用示例"""
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from agno.tools.reasoning import ReasoningTools
    
    # 创建智能体
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        tools=[ReasoningTools(add_instructions=True)],
        instructions=["你是一个高校AI助手", "请提供专业、准确的回答"],
        markdown=True
    )
    
    # 使用智能体
    response = agent.run("请解释机器学习的基本概念")
    return response.content


# 3. 多智能体团队示例
def multi_agent_team_example():
    """多智能体团队使用示例"""
    from agno.agent import Agent
    from agno.team import Team
    from agno.models.openai import OpenAIChat
    from agno.tools.duckduckgo import DuckDuckGoTools
    from agno.tools.reasoning import ReasoningTools
    
    # 创建研究智能体
    research_agent = Agent(
        name="Research Agent",
        role="信息收集专家",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGoTools()],
        instructions=["专门负责收集和整理信息", "提供可靠的数据来源"]
    )
    
    # 创建分析智能体
    analysis_agent = Agent(
        name="Analysis Agent", 
        role="数据分析专家",
        model=OpenAIChat(id="gpt-4o"),
        tools=[ReasoningTools()],
        instructions=["专门负责分析和推理", "提供深入的见解"]
    )
    
    # 创建智能体团队
    team = Team(
        members=[research_agent, analysis_agent],
        model=OpenAIChat(id="gpt-4o"),
        instructions=["协作完成复杂任务", "确保信息准确完整"]
    )
    
    # 使用团队
    response = team.run("研究人工智能在教育领域的最新应用")
    return response.content


# 4. 与Django集成的完整示例
class DjangoAgnoService:
    """Django + Agno 集成服务"""
    
    def __init__(self):
        self.agents = {}
        self.teams = {}
    
    def get_or_create_agent(self, agent_type: str):
        """获取或创建智能体"""
        if agent_type not in self.agents:
            self.agents[agent_type] = self._create_agent(agent_type)
        return self.agents[agent_type]
    
    def _create_agent(self, agent_type: str):
        """根据类型创建智能体"""
        from agno.agent import Agent
        from agno.models.openai import OpenAIChat
        from agno.tools.reasoning import ReasoningTools
        from agno.tools.duckduckgo import DuckDuckGoTools
        
        base_model = OpenAIChat(id="gpt-4o")
        
        if agent_type == "tutor":
            return Agent(
                name="学习导师",
                model=base_model,
                tools=[ReasoningTools(), DuckDuckGoTools()],
                instructions=[
                    "你是一个专业的学习导师",
                    "根据学生水平提供个性化指导",
                    "鼓励主动思考和学习"
                ]
            )
        elif agent_type == "researcher":
            return Agent(
                name="研究助手", 
                model=base_model,
                tools=[DuckDuckGoTools()],
                instructions=[
                    "你是一个专业的研究助手",
                    "擅长信息收集和整理",
                    "提供准确可靠的资料"
                ]
            )
        else:
            return Agent(
                name="通用助手",
                model=base_model,
                instructions=["你是一个友善专业的AI助手"]
            )
    
    def chat_with_agent(self, agent_type: str, message: str):
        """与智能体对话"""
        agent = self.get_or_create_agent(agent_type)
        response = agent.run(message)
        return response.content


# 5. 配置环境变量示例
def setup_environment():
    """设置环境变量"""
    import os
    
    # 在Django settings.py中配置
    settings_example = """
    # AI服务配置
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    
    # Agno配置
    AGNO_STORAGE_DIR = os.path.join(BASE_DIR, 'media', 'agno_storage')
    AGNO_MEMORY_ENABLED = True
    
    # 继续保留DeepSeek配置作为备用
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
    DEEPSEEK_API_BASE = 'https://api.deepseek.com'
    """
    
    return settings_example


# 6. URL配置示例
def url_configuration():
    """URL配置示例"""
    url_example = """
    # ai_agent/urls.py
    from django.urls import path
    from . import agno_views
    
    urlpatterns = [
        # Agno相关API
        path('agno/chat/', agno_views.agno_chat, name='agno_chat'),
        path('agno/team-chat/', agno_views.team_chat, name='team_chat'),
        path('agno/agents/', agno_views.list_agents, name='list_agents'),
        
        # 统一接口（自动选择Agno或DeepSeek）
        path('unified/chat/', agno_views.unified_chat, name='unified_chat'),
        
        # 原有DeepSeek接口保持不变
        path('deepseek/chat/', views.send_message, name='deepseek_chat'),
    ]
    """
    
    return url_example


# 7. 前端集成示例
def frontend_integration():
    """前端集成示例"""
    js_example = """
    // JavaScript前端代码示例
    
    // 获取可用的AI服务
    async function getAvailableServices() {
        const response = await fetch('/api/ai/services/');
        const data = await response.json();
        return data.services;
    }
    
    // 使用Agno智能体
    async function chatWithAgno(message, agentType = 'chat') {
        const response = await fetch('/api/ai/agno/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                message: message,
                agent_type: agentType,
                session_id: currentSessionId
            })
        });
        
        const data = await response.json();
        if (data.success) {
            displayMessage(data.response, 'ai');
            updateAgentInfo(data.agent_type, data.framework);
        }
    }
    
    // 使用智能体团队
    async function chatWithTeam(message, teamType = 'collaborative') {
        const response = await fetch('/api/ai/agno/team-chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                message: message,
                team_type: teamType,
                session_id: currentSessionId
            })
        });
        
        const data = await response.json();
        if (data.success) {
            displayMessage(data.response, 'ai');
            displayTeamInfo(data.team_members);
        }
    }
    """
    
    return js_example


# 8. 迁移指南
def migration_guide():
    """从DeepSeek迁移到Agno的指南"""
    guide = """
    从DeepSeek迁移到Agno的步骤：
    
    1. 安装Agno：
       pip install agno
    
    2. 配置API密钥：
       - OpenAI API Key（推荐）
       - Anthropic API Key（备选）
       - 保留DeepSeek API Key作为后备
    
    3. 创建智能体服务：
       - 创建AgnoAIService类
       - 实现不同类型的智能体
       - 支持团队协作模式
    
    4. 更新视图函数：
       - 添加Agno相关的API端点
       - 保持向后兼容性
       - 实现自动降级机制
    
    5. 更新前端界面：
       - 添加智能体类型选择
       - 添加团队模式开关
       - 显示智能体状态信息
    
    6. 测试和优化：
       - 逐步替换现有功能
       - 性能对比测试
       - 用户体验优化
    
    优势对比：
    
    DeepSeek vs Agno:
    
    DeepSeek:
    ✓ 专门的对话和推理模型
    ✓ 高性能推理
    ✓ 成本效益
    - 单一模型提供商
    - 功能相对单一
    
    Agno:
    ✓ 支持23+模型提供商
    ✓ 多智能体协作
    ✓ 内置推理和记忆
    ✓ 丰富的工具生态
    ✓ 高度可扩展
    - 学习成本稍高
    - 依赖更多
    
    建议：
    - 保持两种服务并存
    - 根据场景选择最适合的方案
    - 逐步迁移非关键功能到Agno
    - 关键功能可以继续使用DeepSeek
    """
    
    return guide


if __name__ == "__main__":
    print("Agno集成示例")
    print("请参考各个函数的示例代码来集成Agno到您的Django项目中") 
Agno框架集成示例
演示如何在Django项目中使用Agno代替DeepSeek
"""

# 1. 安装依赖
# pip install agno

# 2. 基础Agno智能体示例
def basic_agno_example():
    """基础Agno智能体使用示例"""
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from agno.tools.reasoning import ReasoningTools
    
    # 创建智能体
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        tools=[ReasoningTools(add_instructions=True)],
        instructions=["你是一个高校AI助手", "请提供专业、准确的回答"],
        markdown=True
    )
    
    # 使用智能体
    response = agent.run("请解释机器学习的基本概念")
    return response.content


# 3. 多智能体团队示例
def multi_agent_team_example():
    """多智能体团队使用示例"""
    from agno.agent import Agent
    from agno.team import Team
    from agno.models.openai import OpenAIChat
    from agno.tools.duckduckgo import DuckDuckGoTools
    from agno.tools.reasoning import ReasoningTools
    
    # 创建研究智能体
    research_agent = Agent(
        name="Research Agent",
        role="信息收集专家",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGoTools()],
        instructions=["专门负责收集和整理信息", "提供可靠的数据来源"]
    )
    
    # 创建分析智能体
    analysis_agent = Agent(
        name="Analysis Agent", 
        role="数据分析专家",
        model=OpenAIChat(id="gpt-4o"),
        tools=[ReasoningTools()],
        instructions=["专门负责分析和推理", "提供深入的见解"]
    )
    
    # 创建智能体团队
    team = Team(
        members=[research_agent, analysis_agent],
        model=OpenAIChat(id="gpt-4o"),
        instructions=["协作完成复杂任务", "确保信息准确完整"]
    )
    
    # 使用团队
    response = team.run("研究人工智能在教育领域的最新应用")
    return response.content


# 4. 与Django集成的完整示例
class DjangoAgnoService:
    """Django + Agno 集成服务"""
    
    def __init__(self):
        self.agents = {}
        self.teams = {}
    
    def get_or_create_agent(self, agent_type: str):
        """获取或创建智能体"""
        if agent_type not in self.agents:
            self.agents[agent_type] = self._create_agent(agent_type)
        return self.agents[agent_type]
    
    def _create_agent(self, agent_type: str):
        """根据类型创建智能体"""
        from agno.agent import Agent
        from agno.models.openai import OpenAIChat
        from agno.tools.reasoning import ReasoningTools
        from agno.tools.duckduckgo import DuckDuckGoTools
        
        base_model = OpenAIChat(id="gpt-4o")
        
        if agent_type == "tutor":
            return Agent(
                name="学习导师",
                model=base_model,
                tools=[ReasoningTools(), DuckDuckGoTools()],
                instructions=[
                    "你是一个专业的学习导师",
                    "根据学生水平提供个性化指导",
                    "鼓励主动思考和学习"
                ]
            )
        elif agent_type == "researcher":
            return Agent(
                name="研究助手", 
                model=base_model,
                tools=[DuckDuckGoTools()],
                instructions=[
                    "你是一个专业的研究助手",
                    "擅长信息收集和整理",
                    "提供准确可靠的资料"
                ]
            )
        else:
            return Agent(
                name="通用助手",
                model=base_model,
                instructions=["你是一个友善专业的AI助手"]
            )
    
    def chat_with_agent(self, agent_type: str, message: str):
        """与智能体对话"""
        agent = self.get_or_create_agent(agent_type)
        response = agent.run(message)
        return response.content


# 5. 配置环境变量示例
def setup_environment():
    """设置环境变量"""
    import os
    
    # 在Django settings.py中配置
    settings_example = """
    # AI服务配置
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    
    # Agno配置
    AGNO_STORAGE_DIR = os.path.join(BASE_DIR, 'media', 'agno_storage')
    AGNO_MEMORY_ENABLED = True
    
    # 继续保留DeepSeek配置作为备用
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
    DEEPSEEK_API_BASE = 'https://api.deepseek.com'
    """
    
    return settings_example


# 6. URL配置示例
def url_configuration():
    """URL配置示例"""
    url_example = """
    # ai_agent/urls.py
    from django.urls import path
    from . import agno_views
    
    urlpatterns = [
        # Agno相关API
        path('agno/chat/', agno_views.agno_chat, name='agno_chat'),
        path('agno/team-chat/', agno_views.team_chat, name='team_chat'),
        path('agno/agents/', agno_views.list_agents, name='list_agents'),
        
        # 统一接口（自动选择Agno或DeepSeek）
        path('unified/chat/', agno_views.unified_chat, name='unified_chat'),
        
        # 原有DeepSeek接口保持不变
        path('deepseek/chat/', views.send_message, name='deepseek_chat'),
    ]
    """
    
    return url_example


# 7. 前端集成示例
def frontend_integration():
    """前端集成示例"""
    js_example = """
    // JavaScript前端代码示例
    
    // 获取可用的AI服务
    async function getAvailableServices() {
        const response = await fetch('/api/ai/services/');
        const data = await response.json();
        return data.services;
    }
    
    // 使用Agno智能体
    async function chatWithAgno(message, agentType = 'chat') {
        const response = await fetch('/api/ai/agno/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                message: message,
                agent_type: agentType,
                session_id: currentSessionId
            })
        });
        
        const data = await response.json();
        if (data.success) {
            displayMessage(data.response, 'ai');
            updateAgentInfo(data.agent_type, data.framework);
        }
    }
    
    // 使用智能体团队
    async function chatWithTeam(message, teamType = 'collaborative') {
        const response = await fetch('/api/ai/agno/team-chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                message: message,
                team_type: teamType,
                session_id: currentSessionId
            })
        });
        
        const data = await response.json();
        if (data.success) {
            displayMessage(data.response, 'ai');
            displayTeamInfo(data.team_members);
        }
    }
    """
    
    return js_example


# 8. 迁移指南
def migration_guide():
    """从DeepSeek迁移到Agno的指南"""
    guide = """
    从DeepSeek迁移到Agno的步骤：
    
    1. 安装Agno：
       pip install agno
    
    2. 配置API密钥：
       - OpenAI API Key（推荐）
       - Anthropic API Key（备选）
       - 保留DeepSeek API Key作为后备
    
    3. 创建智能体服务：
       - 创建AgnoAIService类
       - 实现不同类型的智能体
       - 支持团队协作模式
    
    4. 更新视图函数：
       - 添加Agno相关的API端点
       - 保持向后兼容性
       - 实现自动降级机制
    
    5. 更新前端界面：
       - 添加智能体类型选择
       - 添加团队模式开关
       - 显示智能体状态信息
    
    6. 测试和优化：
       - 逐步替换现有功能
       - 性能对比测试
       - 用户体验优化
    
    优势对比：
    
    DeepSeek vs Agno:
    
    DeepSeek:
    ✓ 专门的对话和推理模型
    ✓ 高性能推理
    ✓ 成本效益
    - 单一模型提供商
    - 功能相对单一
    
    Agno:
    ✓ 支持23+模型提供商
    ✓ 多智能体协作
    ✓ 内置推理和记忆
    ✓ 丰富的工具生态
    ✓ 高度可扩展
    - 学习成本稍高
    - 依赖更多
    
    建议：
    - 保持两种服务并存
    - 根据场景选择最适合的方案
    - 逐步迁移非关键功能到Agno
    - 关键功能可以继续使用DeepSeek
    """
    
    return guide


if __name__ == "__main__":
    print("Agno集成示例")
    print("请参考各个函数的示例代码来集成Agno到您的Django项目中") 
 
 