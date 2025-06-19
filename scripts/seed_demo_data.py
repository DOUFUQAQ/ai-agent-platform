#!/usr/bin/env python
"""
创建演示数据脚本
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_agent_platform.settings')
django.setup()

from django.contrib.auth import get_user_model
from authentication.models import StudentProfile
from ai_agent.models import AIModel, AIFunction

User = get_user_model()

def create_demo_users():
    """创建演示用户"""
    print("正在创建演示用户...")
    
    # 创建管理员用户
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'user_type': 'admin',
            'first_name': '系统',
            'last_name': '管理员',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin.set_password('admin123')
        admin.save()
        print("✓ 创建管理员用户: admin / admin123")
    
    # 创建教师用户
    teacher, created = User.objects.get_or_create(
        username='teacher',
        defaults={
            'email': 'teacher@example.com',
            'user_type': 'teacher',
            'first_name': '张',
            'last_name': '老师',
            'is_staff': True
        }
    )
    if created:
        teacher.set_password('teacher123')
        teacher.save()
        print("✓ 创建教师用户: teacher / teacher123")
    
    # 创建学生用户
    student, created = User.objects.get_or_create(
        username='student',
        defaults={
            'email': 'student@example.com',
            'user_type': 'student',
            'first_name': '李',
            'last_name': '小明'
        }
    )
    if created:
        student.set_password('student123')
        student.save()
        print("✓ 创建学生用户: student / student123")
        
        # 创建学生档案
        StudentProfile.objects.get_or_create(
            user=student,
            defaults={
                'student_id': '2024001',
                'real_name': '李小明',
                'gender': 'M',
                'grade': '2024级',
                'major': '计算机科学与技术',
                'class_name': '计科1班',
                'enrollment_year': 2024,
                'graduation_year': 2028
            }
        )
        print("✓ 创建学生档案")
    
    # 创建访客用户
    guest, created = User.objects.get_or_create(
        username='guest',
        defaults={
            'email': 'guest@example.com',
            'user_type': 'guest',
            'first_name': '访客',
            'last_name': '用户'
        }
    )
    if created:
        guest.set_password('guest123')
        guest.save()
        print("✓ 创建访客用户: guest / guest123")

def create_ai_models():
    """创建AI模型配置"""
    print("正在创建AI模型配置...")
    
    deepseek_model, created = AIModel.objects.get_or_create(
        model_id='deepseek-chat',
        defaults={
            'name': 'DeepSeek Chat',
            'provider': 'DeepSeek',
            'api_endpoint': 'https://api.deepseek.com/v1/chat/completions',
            'max_tokens': 4096,
            'temperature': 0.7,
            'cost_per_1k_input_tokens': 0.002,
            'cost_per_1k_output_tokens': 0.006,
            'description': 'DeepSeek智能对话模型'
        }
    )
    if created:
        print("✓ 创建DeepSeek模型配置")

def create_ai_functions():
    """创建AI功能配置"""
    print("正在创建AI功能配置...")
    
    functions = [
        {
            'name': '通用问答助手',
            'code': 'qa',
            'function_type': 'qa',
            'description': '回答各类学习和生活问题',
            'prompt_template': '你是一个专业的问答助手，请准确回答用户的问题。'
        },
        {
            'name': '选课助手',
            'code': 'course_selection',
            'function_type': 'course_selection',
            'description': '帮助学生进行课程选择和规划',
            'prompt_template': '你是一个选课助手，帮助学生分析课程内容、学分要求和选课策略。'
        },
        {
            'name': 'AI日历助手',
            'code': 'calendar',
            'function_type': 'calendar',
            'description': '协助进行日程管理和时间规划',
            'prompt_template': '你是一个日程管理助手，帮助用户规划时间、安排任务。'
        },
        {
            'name': '邮件助手',
            'code': 'email',
            'function_type': 'email',
            'description': '协助处理邮件相关事务',
            'prompt_template': '你是一个邮件助手，帮助用户撰写、回复和管理邮件。'
        },
        {
            'name': '学业规划助手',
            'code': 'study_plan',
            'function_type': 'study_plan',
            'description': '提供学业规划和学习方法指导',
            'prompt_template': '你是一个学业规划助手，帮助学生制定学习计划、选择专业方向。'
        },
        {
            'name': '文档处理助手',
            'code': 'document',
            'function_type': 'document',
            'description': '协助处理各类文档任务',
            'prompt_template': '你是一个文档处理助手，帮助用户编写、修改和整理文档。'
        },
        {
            'name': '翻译助手',
            'code': 'translation',
            'function_type': 'translation',
            'description': '提供多语言翻译服务',
            'prompt_template': '你是一个专业的翻译助手，提供准确的多语言翻译服务。'
        }
    ]
    
    for func_data in functions:
        function, created = AIFunction.objects.get_or_create(
            code=func_data['code'],
            defaults=func_data
        )
        if created:
            print(f"✓ 创建AI功能: {func_data['name']}")

def main():
    """主函数"""
    print("开始创建演示数据...")
    print("=" * 50)
    
    try:
        create_demo_users()
        print()
        create_ai_models()
        print()
        create_ai_functions()
        print()
        print("=" * 50)
        print("演示数据创建完成！")
        print()
        print("可以使用以下账号登录系统:")
        print("管理员: admin / admin123")
        print("教师: teacher / teacher123")
        print("学生: student / student123")
        print("访客: guest / guest123")
        print()
        print("访问地址: http://127.0.0.1:8000/")
        print("管理后台: http://127.0.0.1:8000/admin/")
        
    except Exception as e:
        print(f"创建演示数据时出错: {e}")

if __name__ == '__main__':
    main() 