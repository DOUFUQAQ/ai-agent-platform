"""
监控相关的定时任务
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .monitoring import monitoring_service
from .models import ChatMessage, SensitiveWordDetection, AbnormalBehaviorDetection
import logging

logger = logging.getLogger(__name__)


@shared_task
def run_monitoring_batch():
    """运行批量监控任务"""
    try:
        results = monitoring_service.run_batch_monitoring()
        
        logger.info(f"监控任务完成: {len(results['sensitive_words'])} 敏感词检测, "
                   f"{len(results['abnormal_behaviors'])} 异常行为检测")
        
        return results
    except Exception as e:
        logger.error(f"监控任务执行失败: {str(e)}")
        raise


@shared_task
def cleanup_old_monitoring_data():
    """清理旧的监控数据"""
    try:
        # 删除30天前的敏感词检测记录
        cutoff_date = timezone.now() - timedelta(days=30)
        
        deleted_sensitive = SensitiveWordDetection.objects.filter(
            created_at__lt=cutoff_date,
            is_reviewed=True
        ).delete()
        
        deleted_abnormal = AbnormalBehaviorDetection.objects.filter(
            created_at__lt=cutoff_date,
            is_handled=True
        ).delete()
        
        logger.info(f"清理完成: 删除了 {deleted_sensitive[0]} 条敏感词记录, "
                   f"{deleted_abnormal[0]} 条异常行为记录")
        
        return {
            'deleted_sensitive': deleted_sensitive[0],
            'deleted_abnormal': deleted_abnormal[0]
        }
    except Exception as e:
        logger.error(f"清理任务执行失败: {str(e)}")
        raise


@shared_task
def generate_monitoring_report():
    """生成监控报告"""
    try:
        stats = monitoring_service.get_monitoring_stats()
        
        # 这里可以发送邮件报告或保存到文件
        logger.info(f"监控报告生成完成: {stats}")
        
        return stats
    except Exception as e:
        logger.error(f"报告生成失败: {str(e)}")
        raise


# 如果没有Celery，可以使用Django的管理命令来运行这些任务
# python manage.py run_monitoring 