#!/usr/bin/env python
"""
重置用户密码
"""

import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_agent_platform.settings')
django.setup()

from authentication.models import User

def reset_passwords():
    """重置演示账户密码"""
    
    accounts = [
        ('admin', 'admin123'),
        ('teacher', 'teacher123'),
        ('student', 'student123'),
        ('guest', 'guest123'),
        ('landaofu', '123'),
    ]
    
    for username, password in accounts:
        try:
            user = User.objects.get(username=username)
            user.set_password(password)
            user.save()
            print(f"✅ {username} 密码已重置为: {password}")
        except User.DoesNotExist:
            print(f"❌ 用户 {username} 不存在")
        except Exception as e:
            print(f"❌ 重置 {username} 密码失败: {e}")

if __name__ == "__main__":
    print("🔑 重置演示账户密码...")
    reset_passwords()
    print("\n🎉 密码重置完成！") 