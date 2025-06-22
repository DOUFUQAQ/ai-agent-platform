"""
创建默认AI功能的管理命令
"""

from django.core.management.base import BaseCommand
from permissions.models import AIFunction


class Command(BaseCommand):
    help = '创建默认的AI功能配置'
    
    def handle(self, *args, **options):
        """创建默认功能"""
        
        default_functions = [
            {
                'function_code': 'chat_basic',
                'name': '基础聊天',
                'description': '基础AI聊天功能，适用于日常对话',
                'function_type': 'chat',
                'is_active': True,
                'is_beta': False,
                'max_daily_usage': 100
            },
            {
                'function_code': 'agno_chat',
                'name': 'Agno智能助手',
                'description': 'Agno框架驱动的高级智能助手',
                'function_type': 'agno',
                'is_active': True,
                'is_beta': False,
                'max_daily_usage': 50
            },
            {
                'function_code': 'agno_code',
                'name': 'Agno代码助手',
                'description': '代码生成、调试和优化助手',
                'function_type': 'agno',
                'is_active': True,
                'is_beta': True,
                'max_daily_usage': 30
            },
            {
                'function_code': 'agno_study',
                'name': 'Agno学习助手',
                'description': '学习规划、知识问答和作业辅导',
                'function_type': 'agno',
                'is_active': True,
                'is_beta': False,
                'max_daily_usage': 80
            },
            {
                'function_code': 'agno_research',
                'name': 'Agno研究助手',
                'description': '文献调研、数据分析和报告生成',
                'function_type': 'agno',
                'is_active': True,
                'is_beta': True,
                'max_daily_usage': 20
            },
            {
                'function_code': 'agno_creative',
                'name': 'Agno创意助手',
                'description': '创意写作、头脑风暴和设计建议',
                'function_type': 'agno',
                'is_active': True,
                'is_beta': False,
                'max_daily_usage': 40
            },
            {
                'function_code': 'file_upload',
                'name': '文件上传',
                'description': '支持文档、图片等文件上传分析',
                'function_type': 'file',
                'is_active': True,
                'is_beta': False,
                'max_daily_usage': 20
            },
            {
                'function_code': 'voice_chat',
                'name': '语音对话',
                'description': '语音输入和语音合成对话',
                'function_type': 'voice',
                'is_active': False,
                'is_beta': True,
                'max_daily_usage': 10
            },
            {
                'function_code': 'image_generation',
                'name': '图像生成',
                'description': 'AI图像生成和编辑功能',
                'function_type': 'image',
                'is_active': False,
                'is_beta': True,
                'max_daily_usage': 5
            },
            {
                'function_code': 'advanced_analytics',
                'name': '高级分析',
                'description': '数据分析、可视化和报表生成',
                'function_type': 'analytics',
                'is_active': True,
                'is_beta': True,
                'max_daily_usage': 15
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for func_data in default_functions:
            function, created = AIFunction.objects.get_or_create(
                function_code=func_data['function_code'],
                defaults=func_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 创建功能: {function.name}')
                )
            else:
                # 更新现有功能的非关键字段
                updated = False
                for field, value in func_data.items():
                    if field != 'function_code' and getattr(function, field) != value:
                        setattr(function, field, value)
                        updated = True
                
                if updated:
                    function.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ 更新功能: {function.name}')
                    )
                else:
                    self.stdout.write(
                        self.style.HTTP_INFO(f'- 跳过功能: {function.name} (已存在)')
                    )
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'功能配置完成！创建 {created_count} 个，更新 {updated_count} 个')
        )
        
        # 显示当前状态统计
        total_functions = AIFunction.objects.count()
        active_functions = AIFunction.objects.filter(is_active=True).count()
        beta_functions = AIFunction.objects.filter(is_beta=True).count()
        
        self.stdout.write(f'当前状态：')
        self.stdout.write(f'  总功能数: {total_functions}')
        self.stdout.write(f'  活跃功能: {active_functions}')
        self.stdout.write(f'  测试功能: {beta_functions}')
        self.stdout.write('='*50) 