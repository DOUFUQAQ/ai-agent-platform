from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, F
from datetime import datetime, timedelta
import json
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Any
from django.db import connection

from .models import (
    ChatSession, ChatMessage, UserBehaviorLog, 
    SensitiveWordDetection, AbnormalBehaviorDetection,
    FunctionUsageStatistics
)
from permissions.models import AIFunction

User = get_user_model()


class BehaviorAnalysisService:
    """行为分析服务"""
    
    @staticmethod
    def get_user_activity_stats(user_id: int = None, days: int = 30) -> Dict:
        """获取用户活跃度统计"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        base_query = ChatSession.objects.filter(started_at__gte=start_date)
        if user_id:
            base_query = base_query.filter(user_id=user_id)
        
        # 基础统计
        total_sessions = base_query.count()
        total_messages = ChatMessage.objects.filter(
            session__in=base_query,
            message_type='user'
        ).count()
        
        # 用户数统计
        unique_users = base_query.values('user').distinct().count()
        
        # 平均会话时长
        avg_duration = base_query.exclude(ended_at__isnull=True).aggregate(
            avg_duration=Avg(
                models.ExpressionWrapper(
                    F('ended_at') - F('started_at'),
                    output_field=models.DurationField()
                )
            )
        )['avg_duration']
        
        avg_duration_minutes = 0
        if avg_duration:
            avg_duration_minutes = avg_duration.total_seconds() / 60
        
        return {
            'period_days': days,
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'unique_users': unique_users,
            'avg_duration_minutes': round(avg_duration_minutes, 2),
            'avg_messages_per_session': round(total_messages / max(total_sessions, 1), 2),
            'sessions_per_user': round(total_sessions / max(unique_users, 1), 2)
        }
    
    @staticmethod
    def get_daily_activity_trend(days: int = 30) -> List[Dict]:
        """获取每日活跃度趋势"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # 按日期分组统计
        daily_stats = []
        current_date = start_date
        
        while current_date <= end_date:
            # 当日会话统计
            sessions = ChatSession.objects.filter(
                started_at__date=current_date
            )
            
            # 当日用户数
            daily_users = sessions.values('user').distinct().count()
            
            # 当日消息数
            daily_messages = ChatMessage.objects.filter(
                session__in=sessions,
                message_type='user'
            ).count()
            
            daily_stats.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'sessions': sessions.count(),
                'users': daily_users,
                'messages': daily_messages
            })
            
            current_date += timedelta(days=1)
        
        return daily_stats
    
    @staticmethod
    def get_function_usage_stats(days: int = 30) -> Dict:
        """获取功能使用统计"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # 功能调用统计
        function_stats = ChatSession.objects.filter(
            started_at__gte=start_date,
            function_code__isnull=False
        ).values('function_code').annotate(
            call_count=Count('id'),
            unique_users=Count('user', distinct=True),
            total_messages=Sum('message_count'),
            avg_duration=Avg(
                models.ExpressionWrapper(
                    F('ended_at') - F('started_at'),
                    output_field=models.DurationField()
                )
            )
        ).order_by('-call_count')
        
        # 转换为字典并添加功能名称
        result = []
        for stat in function_stats:
            try:
                function = AIFunction.objects.get(function_code=stat['function_code'])
                function_name = function.name
            except AIFunction.DoesNotExist:
                function_name = stat['function_code']
            
            avg_duration_minutes = 0
            if stat['avg_duration']:
                avg_duration_minutes = stat['avg_duration'].total_seconds() / 60
            
            result.append({
                'function_code': stat['function_code'],
                'function_name': function_name,
                'call_count': stat['call_count'],
                'unique_users': stat['unique_users'],
                'total_messages': stat['total_messages'] or 0,
                'avg_duration_minutes': round(avg_duration_minutes, 2),
                'usage_rate': round(stat['call_count'] / max(1, ChatSession.objects.filter(started_at__gte=start_date).count()) * 100, 2)
            })
        
        return {
            'functions': result[:10],  # 返回前10个热门功能
            'total_functions': len(result)
        }
    
    @staticmethod
    def get_user_behavior_profile(user_id: int) -> Dict:
        """获取用户行为画像"""
        user = User.objects.get(id=user_id)
        
        # 基础统计
        total_sessions = ChatSession.objects.filter(user_id=user_id).count()
        total_messages = ChatMessage.objects.filter(
            session__user_id=user_id,
            message_type='user'
        ).count()
        
        # 最近30天活跃度
        recent_activity = BehaviorAnalysisService.get_user_activity_stats(user_id, 30)
        
        # 常用功能TOP3
        favorite_functions = ChatSession.objects.filter(
            user_id=user_id,
            function_code__isnull=False
        ).values('function_code').annotate(
            count=Count('id')
        ).order_by('-count')[:3]
        
        # 转换功能名称
        fav_functions_with_names = []
        for func in favorite_functions:
            try:
                function = AIFunction.objects.get(function_code=func['function_code'])
                fav_functions_with_names.append({
                    'function_code': func['function_code'],
                    'function_name': function.name,
                    'count': func['count']
                })
            except AIFunction.DoesNotExist:
                fav_functions_with_names.append({
                    'function_code': func['function_code'],
                    'function_name': func['function_code'],
                    'count': func['count']
                })
        
        # 使用时间分布 - 修复SQLite兼容性
        if 'sqlite' in connection.settings_dict['ENGINE']:
            # SQLite语法
            hour_distribution = ChatSession.objects.filter(
                user_id=user_id
            ).extra(
                select={'hour': "CAST(strftime('%%H', started_at) AS INTEGER)"}
            ).values('hour').annotate(
                count=Count('id')
            ).order_by('hour')
        else:
            # PostgreSQL语法
            hour_distribution = ChatSession.objects.filter(
                user_id=user_id
            ).extra(
                select={'hour': "EXTRACT(hour FROM started_at)"}
            ).values('hour').annotate(
                count=Count('id')
            ).order_by('hour')
        
        # 最近登录
        last_session = ChatSession.objects.filter(user_id=user_id).first()
        
        return {
            'user_info': {
                'id': user.id,
                'username': user.username,
                'user_type': user.user_type,
                'date_joined': user.date_joined
            },
            'basic_stats': {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'last_active': last_session.started_at if last_session else None
            },
            'recent_activity': recent_activity,
            'favorite_functions': fav_functions_with_names,
            'hour_distribution': list(hour_distribution)
        }


class AbnormalBehaviorDetector:
    """异常行为检测器"""
    
    # 检测阈值配置
    THRESHOLDS = {
        'high_frequency': {
            'messages_per_hour': 100,  # 每小时超过100条消息
            'sessions_per_hour': 20     # 每小时超过20个会话
        },
        'unusual_time': {
            'late_night_hours': [0, 1, 2, 3, 4, 5],  # 深夜时段
            'early_morning_hours': [5, 6, 7]          # 早晨时段
        },
        'resource_abuse': {
            'token_limit_per_day': 100000,  # 每天token限制
            'long_session_minutes': 180      # 超过3小时的会话
        }
    }
    
    @classmethod
    def detect_high_frequency_usage(cls, user_id: int) -> List[Dict]:
        """检测高频使用行为"""
        detections = []
        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # 检查每小时消息数
        recent_messages = ChatMessage.objects.filter(
            session__user_id=user_id,
            created_at__gte=one_hour_ago,
            message_type='user'
        ).count()
        
        if recent_messages > cls.THRESHOLDS['high_frequency']['messages_per_hour']:
            detections.append({
                'behavior_type': 'high_frequency',
                'description': f'用户在过去1小时内发送了{recent_messages}条消息，超过正常阈值',
                'detection_data': {
                    'messages_count': recent_messages,
                    'time_period': '1_hour',
                    'threshold': cls.THRESHOLDS['high_frequency']['messages_per_hour']
                },
                'risk_score': min(100, 20 + (recent_messages - cls.THRESHOLDS['high_frequency']['messages_per_hour']) * 2)
            })
        
        # 检查每小时会话数
        recent_sessions = ChatSession.objects.filter(
            user_id=user_id,
            started_at__gte=one_hour_ago
        ).count()
        
        if recent_sessions > cls.THRESHOLDS['high_frequency']['sessions_per_hour']:
            detections.append({
                'behavior_type': 'high_frequency',
                'description': f'用户在过去1小时内创建了{recent_sessions}个会话，可能存在异常行为',
                'detection_data': {
                    'sessions_count': recent_sessions,
                    'time_period': '1_hour',
                    'threshold': cls.THRESHOLDS['high_frequency']['sessions_per_hour']
                },
                'risk_score': min(100, 30 + (recent_sessions - cls.THRESHOLDS['high_frequency']['sessions_per_hour']) * 3)
            })
        
        return detections
    
    @classmethod
    def detect_unusual_time_usage(cls, user_id: int) -> List[Dict]:
        """检测异常时段使用"""
        detections = []
        now = timezone.now()
        today = now.date()
        
        # 检查深夜使用
        late_night_sessions = ChatSession.objects.filter(
            user_id=user_id,
            started_at__date=today,
            started_at__hour__in=cls.THRESHOLDS['unusual_time']['late_night_hours']
        ).count()
        
        if late_night_sessions > 0:
            detections.append({
                'behavior_type': 'unusual_time',
                'description': f'用户在深夜时段（0-5点）使用系统{late_night_sessions}次',
                'detection_data': {
                    'sessions_count': late_night_sessions,
                    'time_period': 'late_night',
                    'hours': cls.THRESHOLDS['unusual_time']['late_night_hours']
                },
                'risk_score': min(100, 10 + late_night_sessions * 15)
            })
        
        return detections
    
    @classmethod
    def detect_resource_abuse(cls, user_id: int) -> List[Dict]:
        """检测资源滥用"""
        detections = []
        now = timezone.now()
        today = now.date()
        
        # 检查每日token使用量
        daily_tokens = ChatMessage.objects.filter(
            session__user_id=user_id,
            created_at__date=today
        ).aggregate(total_tokens=Sum('tokens_used'))['total_tokens'] or 0
        
        if daily_tokens > cls.THRESHOLDS['resource_abuse']['token_limit_per_day']:
            detections.append({
                'behavior_type': 'resource_abuse',
                'description': f'用户今日使用了{daily_tokens}个token，超过每日限制',
                'detection_data': {
                    'tokens_used': daily_tokens,
                    'threshold': cls.THRESHOLDS['resource_abuse']['token_limit_per_day'],
                    'date': today.strftime('%Y-%m-%d')
                },
                'risk_score': min(100, 40 + (daily_tokens - cls.THRESHOLDS['resource_abuse']['token_limit_per_day']) // 1000)
            })
        
        # 检查长时间会话
        long_sessions = ChatSession.objects.filter(
            user_id=user_id,
            started_at__date=today,
            ended_at__isnull=False
        ).annotate(
            duration_minutes=models.ExpressionWrapper(
                (F('ended_at') - F('started_at')),
                output_field=models.DurationField()
            )
        ).filter(
            duration_minutes__gte=timedelta(minutes=cls.THRESHOLDS['resource_abuse']['long_session_minutes'])
        ).count()
        
        if long_sessions > 0:
            detections.append({
                'behavior_type': 'resource_abuse',
                'description': f'用户今日有{long_sessions}个超长会话（超过3小时）',
                'detection_data': {
                    'long_sessions_count': long_sessions,
                    'threshold_minutes': cls.THRESHOLDS['resource_abuse']['long_session_minutes'],
                    'date': today.strftime('%Y-%m-%d')
                },
                'risk_score': min(100, 25 + long_sessions * 20)
            })
        
        return detections
    
    @classmethod
    def run_detection_for_user(cls, user_id: int) -> List[Dict]:
        """为用户运行所有异常检测"""
        all_detections = []
        
        # 高频使用检测
        all_detections.extend(cls.detect_high_frequency_usage(user_id))
        
        # 异常时段检测
        all_detections.extend(cls.detect_unusual_time_usage(user_id))
        
        # 资源滥用检测
        all_detections.extend(cls.detect_resource_abuse(user_id))
        
        # 保存检测结果到数据库
        for detection in all_detections:
            AbnormalBehaviorDetection.objects.create(
                user_id=user_id,
                behavior_type=detection['behavior_type'],
                description=detection['description'],
                detection_data=detection['detection_data'],
                risk_score=detection['risk_score']
            )
        
        return all_detections


class SensitiveContentDetector:
    """敏感内容检测器"""
    
    # 真实敏感词库 - 不再使用简化版本
    SENSITIVE_WORDS = {
        'inappropriate': [
            '不当言论', '恶意攻击', '人身攻击', '侮辱', '威胁',
            '歧视', '仇恨', '暴力', '极端', '诽谤', '恶意',
            '欺凌', '霸凌', '骚扰', '恶语', '辱骂'
        ],
        'cheating': [
            '作弊', '抄袭', '代写作业', '代考', '买答案', '卖答案',
            '刷分', '黑客', '破解系统', '绕过检测', '外挂', 
            '代做作业', '找人代写', '论文代写', '考试答案',
            '答案分享', '题库泄露', '考前答案', '内部消息'
        ],
        'violation': [
            '违规操作', '违法行为', '非法获取', '禁止行为', 
            '盗版软件', '侵权内容', '泄露信息', '非法访问',
            '盗取资料', '窃取信息', '恶意传播', '非法下载'
        ],
        'spam': [
            '广告推广', '营销信息', '刷屏', '垃圾信息',
            '重复发送', '恶意刷新', '群发消息', '推销产品',
            '商业推广', '引流', '拉群', '加微信', '联系方式'
        ],
        'academic_misconduct': [
            '学术不端', '抄袭论文', '数据造假', '伪造结果',
            '一稿多投', '剽窃', '代笔', '枪手', '学位造假'
        ]
    }
    
    @classmethod
    def detect_message(cls, message: ChatMessage) -> List[Dict]:
        """检测消息中的敏感内容 - 使用真实检测而非模拟数据"""
        detections = []
        content = message.content.lower()
        
        for detection_type, words in cls.SENSITIVE_WORDS.items():
            matched_words = []
            for word in words:
                if word.lower() in content:
                    matched_words.append(word)
            
            if matched_words:
                # 根据匹配的敏感词数量和类型计算严重程度
                severity = 'low'
                if detection_type in ['inappropriate', 'violation', 'academic_misconduct']:
                    severity = 'high'
                elif detection_type == 'cheating':
                    severity = 'medium'
                elif len(matched_words) > 2:
                    severity = 'high'
                elif len(matched_words) > 1:
                    severity = 'medium'
                
                detection = {
                    'message_id': message.id,
                    'detection_type': detection_type,
                    'matched_words': matched_words,
                    'severity': severity,
                    'context': content[:500]  # 保存前500字符作为上下文
                }
                
                # 保存到数据库 - 确保是真实检测结果
                SensitiveWordDetection.objects.create(
                    message=message,
                    detection_type=detection_type,
                    matched_words=matched_words,
                    severity=severity,
                    context=content[:500]
                )
                
                # 标记消息
                message.is_flagged = True
                message.flag_reason = f'检测到敏感内容: {", ".join(matched_words[:3])}'
                message.save()
                
                detections.append(detection)
        
        return detections
    
    @classmethod
    def check_patterns(cls, content: str) -> List[Dict]:
        """检查特殊模式"""
        import re
        pattern_detections = []
        
        # 特殊模式匹配
        suspicious_patterns = [
            (r'帮我.*(?:写|做).*(?:作业|论文|报告)', 'cheating', '请求代写'),
            (r'(?:买|卖|交易).*(?:答案|作业|论文)', 'cheating', '交易作业'),
            (r'(?:分享|发送).*(?:答案|题库)', 'cheating', '分享答案'),
            (r'(?:联系|加|微信|QQ).*\d{5,}', 'spam', '联系方式'),
            (r'(?:群|加入).*\d{6,}', 'spam', '群号码')
        ]
        
        for pattern, detection_type, description in suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                pattern_detections.append({
                    'detection_type': detection_type,
                    'matched_words': [description],
                    'severity': 'medium',
                    'context': content[:500]
                })
        
        return pattern_detections


class StatisticsService:
    """统计分析服务"""
    
    @staticmethod
    def get_dashboard_stats() -> Dict:
        """获取仪表板统计数据"""
        now = timezone.now()
        today = now.date()
        yesterday = today - timedelta(days=1)
        this_week_start = today - timedelta(days=today.weekday())
        this_month_start = today.replace(day=1)
        
        # 今日统计
        today_sessions = ChatSession.objects.filter(started_at__date=today).count()
        today_users = ChatSession.objects.filter(started_at__date=today).values('user').distinct().count()
        today_messages = ChatMessage.objects.filter(created_at__date=today, message_type='user').count()
        
        # 昨日对比
        yesterday_sessions = ChatSession.objects.filter(started_at__date=yesterday).count()
        yesterday_users = ChatSession.objects.filter(started_at__date=yesterday).values('user').distinct().count()
        
        # 本周统计
        week_sessions = ChatSession.objects.filter(started_at__date__gte=this_week_start).count()
        week_users = ChatSession.objects.filter(started_at__date__gte=this_week_start).values('user').distinct().count()
        
        # 本月统计
        month_sessions = ChatSession.objects.filter(started_at__date__gte=this_month_start).count()
        month_users = ChatSession.objects.filter(started_at__date__gte=this_month_start).values('user').distinct().count()
        
        # 计算变化率
        session_change = ((today_sessions - yesterday_sessions) / max(yesterday_sessions, 1)) * 100
        user_change = ((today_users - yesterday_users) / max(yesterday_users, 1)) * 100
        
        # 异常行为统计
        unhandled_abnormal = AbnormalBehaviorDetection.objects.filter(is_handled=False).count()
        unreviewed_sensitive = SensitiveWordDetection.objects.filter(is_reviewed=False).count()
        
        # 功能使用TOP5
        top_functions = ChatSession.objects.filter(
            started_at__date__gte=this_week_start,
            function_code__isnull=False
        ).values('function_code').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        return {
            'today': {
                'sessions': today_sessions,
                'users': today_users,
                'messages': today_messages,
                'session_change': round(session_change, 1),
                'user_change': round(user_change, 1)
            },
            'week': {
                'sessions': week_sessions,
                'users': week_users
            },
            'month': {
                'sessions': month_sessions,
                'users': month_users
            },
            'alerts': {
                'unhandled_abnormal': unhandled_abnormal,
                'unreviewed_sensitive': unreviewed_sensitive
            },
            'top_functions': list(top_functions)
        }
    
    @staticmethod
    def get_user_statistics(user_id: int = None, period: str = 'month') -> Dict:
        """获取用户统计数据"""
        now = timezone.now()
        
        if period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        else:  # year
            start_date = now - timedelta(days=365)
        
        base_query = ChatSession.objects.filter(started_at__gte=start_date)
        if user_id:
            base_query = base_query.filter(user_id=user_id)
        
        # 基础统计
        total_sessions = base_query.count()
        total_users = base_query.values('user').distinct().count() if not user_id else 1
        total_messages = ChatMessage.objects.filter(
            session__in=base_query,
            message_type='user'
        ).count()
        
        # 平均统计
        avg_session_duration = base_query.exclude(ended_at__isnull=True).aggregate(
            avg=Avg(models.ExpressionWrapper(
                F('ended_at') - F('started_at'),
                output_field=models.DurationField()
            ))
        )['avg']
        
        avg_duration_minutes = 0
        if avg_session_duration:
            avg_duration_minutes = avg_session_duration.total_seconds() / 60
        
        return {
            'period': period,
            'total_sessions': total_sessions,
            'total_users': total_users,
            'total_messages': total_messages,
            'avg_duration_minutes': round(avg_duration_minutes, 2),
            'avg_messages_per_session': round(total_messages / max(total_sessions, 1), 2),
            'sessions_per_user': round(total_sessions / max(total_users, 1), 2)
        } 