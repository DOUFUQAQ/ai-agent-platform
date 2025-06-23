#!/usr/bin/env python
"""
设置超级用户的user_type为admin
"""

import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_agent_platform.settings')
django.setup()

from authentication.models import User

def set_user_admin():
    """设置超级用户为admin类型"""
    
    # 获取所有超级用户
    superusers = User.objects.filter(is_superuser=True)
    
    if not superusers.exists():
        print("❌ 没有找到超级用户")
        return
    
    for user in superusers:
        print(f"设置用户 {user.username} 的user_type为admin...")
        user.user_type = 'admin'
        user.save()
        print(f"✅ 用户 {user.username} 已设置为管理员")
    
    print("\n🎉 所有超级用户已设置为管理员！")
    print("\n现在可以使用以下账号登录访问所有管理页面:")
    for user in superusers:
        print(f"用户名: {user.username}")

if __name__ == "__main__":
    set_user_admin() 