"""
自动化监控服务
实现敏感词检测、异常行为监控等功能
"""

import re
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q, Avg, Sum
from django.contrib.auth import get_user_model
from .models import (
    ChatMessage, ChatSession, SensitiveWordDetection, 
    AbnormalBehaviorDetection, UserBehaviorLog
)

User = get_user_model()


class SensitiveWordMonitor:
    """敏感词监控器"""
    
    def __init__(self):
        # 真实敏感词库 - 覆盖各种违规内容
        self.sensitive_words = {
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
        
        # 敏感词变体检测 - 检测故意规避的写法
        self.variant_patterns = {
            '作弊': [r'作\s*弊', r'作\.*弊', r'做弊', r'作.弊'],
            '抄袭': [r'抄\s*袭', r'抄\.*袭', r'炒袭', r'抄.袭'],
            '代写': [r'代\s*写', r'代\.*写', r'带写', r'代.写'],
            '答案': [r'答\s*案', r'答\.*案', r'答.案']
        }
    
    def check_message(self, message):
        """检查消息是否包含敏感词"""
        content = message.content.lower()
        detected_words = []
        detection_type = None
        severity = 'low'
        
        # 检查直接匹配
        for category, words in self.sensitive_words.items():
            for word in words:
                if word in content:
                    detected_words.append(word)
                    if not detection_type:
                        detection_type = category
                    
                    # 根据敏感词类型调整严重程度
                    if category in ['inappropriate', 'violation', 'academic_misconduct']:
                        severity = 'high'
                    elif category in ['cheating']:
                        severity = 'medium'
        
        # 检查变体模式
        for base_word, patterns in self.variant_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    detected_words.append(f"{base_word}(变体)")
                    if not detection_type:
                        detection_type = 'cheating'
                    severity = 'medium'
        
        # 检查特殊模式
        suspicious_patterns = [
            (r'帮我.*(?:写|做).*(?:作业|论文|报告)', 'cheating', '请求代写'),
            (r'(?:买|卖|交易).*(?:答案|作业|论文)', 'cheating', '交易作业'),
            (r'(?:分享|发送).*(?:答案|题库)', 'cheating', '分享答案'),
            (r'(?:联系|加|微信|QQ).*\d{5,}', 'spam', '联系方式'),
            (r'(?:群|加入).*\d{6,}', 'spam', '群号码')
        ]
        
        for pattern, cat, desc in suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                detected_words.append(desc)
                if not detection_type:
                    detection_type = cat
                severity = 'medium'
        
        if detected_words:
            # 创建敏感词检测记录
            SensitiveWordDetection.objects.create(
                message=message,
                detection_type=detection_type,
                matched_words=detected_words,
                severity=severity,
                context=content[:500],  # 保存前500个字符作为上下文
            )
            
            # 标记消息
            message.is_flagged = True
            message.flag_reason = f'检测到敏感内容: {", ".join(detected_words[:3])}'
            message.save()
            
            return True, detected_words, severity
        
        return False, [], 'none'


class MonitoringService:
    """监控服务主类"""
    
    def __init__(self):
        self.sensitive_word_monitor = SensitiveWordMonitor()
    
    def process_new_message(self, message):
        """处理新消息（实时监控）"""
        results = {}
        
        # 敏感词检测
        if message.message_type == 'user':
            is_sensitive, words, severity = self.sensitive_word_monitor.check_message(message)
            results['sensitive_word'] = {
                'detected': is_sensitive,
                'words': words,
                'severity': severity
            }
        
        return results
    
    def run_batch_monitoring(self):
        """批量运行监控检测"""
        # 检查最近1小时未标记的用户消息
        one_hour_ago = timezone.now() - timedelta(hours=1)
        messages = ChatMessage.objects.filter(
            created_at__gte=one_hour_ago,
            message_type='user',
            is_flagged=False
        )
        
        results = {
            'sensitive_words': [],
            'processed_count': 0
        }
        
        for message in messages:
            result = self.process_new_message(message)
            results['processed_count'] += 1
            
            if result.get('sensitive_word', {}).get('detected', False):
                results['sensitive_words'].append({
                    'message_id': message.id,
                    'user': message.session.user.username,
                    'words': result['sensitive_word']['words'],
                    'severity': result['sensitive_word']['severity']
                })
        
        return results
    
    def get_monitoring_stats(self):
        """获取监控统计信息"""
        today = timezone.now().date()
        
        stats = {
            'today': {
                'sensitive_detections': SensitiveWordDetection.objects.filter(
                    created_at__date=today
                ).count(),
                'abnormal_behaviors': AbnormalBehaviorDetection.objects.filter(
                    created_at__date=today
                ).count(),
                'flagged_messages': ChatMessage.objects.filter(
                    created_at__date=today,
                    is_flagged=True
                ).count()
            },
            'pending_review': {
                'sensitive_words': SensitiveWordDetection.objects.filter(
                    is_reviewed=False
                ).count(),
                'abnormal_behaviors': AbnormalBehaviorDetection.objects.filter(
                    is_handled=False
                ).count()
            }
        }
        
        return stats


# 创建全局实例
monitoring_service = MonitoringService() 