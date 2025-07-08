"""
Agno智能体Django视图
展示如何在Django中使用Agno服务
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
import json
import logging

from .agno_services import agno_service
from permissions.decorators import api_function_permission

logger = logging.getLogger(__name__)

@login_required
def agno_chat_page(request):
    """Agno聊天页面"""
    context = {
        'page_title': 'Agno智能体对话',
        'available_agents': agno_service.get_available_agents() if agno_service else [],
        'agno_available': agno_service is not None
    }
    return render(request, 'ai_agent/agno_chat.html', context)

@csrf_exempt
@require_http_methods(["POST"])
@api_function_permission('agno_chat')
def agno_chat_api(request):
    """Agno聊天API"""
    try:
        if not agno_service:
            return JsonResponse({
                'success': False,
                'error': 'Agno服务未初始化'
            }, status=500)
        
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        agent_type = data.get('agent_type', 'chat')
        session_id = data.get('session_id')
        
        if not message:
            return JsonResponse({
                'success': False,
                'error': '消息不能为空'
            }, status=400)
        
        # 导入模型
        from behavior_tracking.models import ChatSession, ChatMessage
        from django.utils import timezone
        import uuid
        
        # 获取或创建会话
        if session_id:
            try:
                session = ChatSession.objects.get(session_id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': '会话不存在或无权限访问'
                }, status=404)
        else:
            # 创建新会话
            session_id = str(uuid.uuid4())
            session = ChatSession.objects.create(
                user=request.user,
                session_id=session_id,
                title=f"Agno对话 - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            )
        
        # 记录用户消息到数据库
        user_tokens = len(message) // 4  # 估算用户输入Token
        user_message = ChatMessage.objects.create(
            session=session,
            message_type='user',
            content=message,
            tokens_used=user_tokens,
            function_called=f'agno_{agent_type}'
        )
        
        # 使用Agno服务处理消息
        response = agno_service.chat(
            message=message,
            agent_type=agent_type,
            user_id=request.user.id
        )
        
        # 记录AI回复到数据库
        ai_tokens = len(response) // 4  # 估算AI回复Token
        ai_message = ChatMessage.objects.create(
            session=session,
            message_type='assistant',
            content=response,
            tokens_used=ai_tokens,
            function_called=f'agno_{agent_type}'
        )
        
        # 更新会话统计
        total_tokens = user_tokens + ai_tokens
        session.message_count += 2
        session.total_tokens = (session.total_tokens or 0) + total_tokens
        session.save()
        
        return JsonResponse({
            'success': True,
            'response': response,
            'agent_type': agent_type,
            'framework': 'agno',
            'session_id': session_id,
            'tokens_used': total_tokens,
            'user_tokens': user_tokens,
            'ai_tokens': ai_tokens
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"Agno聊天API错误: {e}")
        return JsonResponse({
            'success': False,
            'error': f'处理请求时出错: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@login_required
def agno_health_check(request):
    """Agno健康检查API"""
    try:
        if not agno_service:
            return JsonResponse({
                'success': False,
                'status': 'unavailable',
                'error': 'Agno服务未初始化'
            })
        
        health = agno_service.health_check()
        
        return JsonResponse({
            'success': True,
            'status': 'healthy' if all(health.values()) else 'partial',
            'details': health,
            'available_agents': agno_service.get_available_agents()
        })
        
    except Exception as e:
        logger.error(f"Agno健康检查错误: {e}")
        return JsonResponse({
            'success': False,
            'status': 'error',
            'error': str(e)
        })

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def agno_reset_agent(request):
    """重置指定类型的智能体"""
    try:
        if not agno_service:
            return JsonResponse({
                'success': False,
                'error': 'Agno服务未初始化'
            }, status=500)
        
        data = json.loads(request.body)
        agent_type = data.get('agent_type', 'chat')
        
        agno_service.reset_agent(agent_type)
        
        return JsonResponse({
            'success': True,
            'message': f'已重置{agent_type}智能体'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"重置智能体错误: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500) 