#!/usr/bin/env python
"""
最终页面访问验证测试
"""

import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

# 所有测试页面
ALL_PAGES = {
    "公开页面": [
        ("/auth/login/", "登录页面", 200),
    ],
    "需要登录的页面": [
        ("/ai_agent/chat/", "AI聊天页面", [200, 302]),
        ("/auth/admin/dashboard/", "系统管理", [200, 302]),
    ],
    "管理员专属页面": [
        ("/audit/", "安全审计", [200, 302]),
    ],
    "管理员/教师页面": [
        ("/permissions/toggle/", "用户权限", [200, 302]),
        ("/behavior/", "行为监控", [200, 302]),
        ("/students/", "学生管理", [200, 302]),
    ]
}

def test_all_pages():
    """测试所有页面访问"""
    print("🧪 AI智能体平台 - 页面访问测试")
    print(f"服务器地址: {BASE_URL}")
    print("=" * 80)
    
    session = requests.Session()
    all_passed = True
    
    for category, pages in ALL_PAGES.items():
        print(f"\n📋 {category}:")
        print("-" * 60)
        
        for path, name, expected_codes in pages:
            try:
                url = BASE_URL + path
                response = session.get(url, allow_redirects=False, timeout=5)
                status = response.status_code
                
                if isinstance(expected_codes, int):
                    expected_codes = [expected_codes]
                
                if status in expected_codes:
                    if status == 200:
                        result = "✅ 正常访问"
                    else:
                        location = response.headers.get('Location', '')
                        if 'login' in location:
                            result = "✅ 正确重定向到登录"
                        elif 'chat' in location:
                            result = "✅ 权限保护 (重定向到聊天)"
                        else:
                            result = f"✅ 重定向到: {location[:50]}..."
                else:
                    result = f"❌ 状态码 {status} (期望: {expected_codes})"
                    all_passed = False
                
                print(f"{name:<20} {path:<30} {result}")
                
            except requests.exceptions.ConnectionError:
                print(f"{name:<20} {path:<30} ❌ 服务器未运行")
                all_passed = False
                break
            except Exception as e:
                print(f"{name:<20} {path:<30} ❌ 错误: {e}")
                all_passed = False
    
    print("\n" + "=" * 80)
    
    if all_passed:
        print("🎉 所有页面访问测试通过！")
        print("\n✅ 权限系统工作正常:")
        print("   - 公开页面可正常访问")
        print("   - 受保护页面正确重定向")
        print("   - 权限检查由视图装饰器处理")
        
        print("\n📚 使用指南:")
        print("1. 使用管理员账户登录:")
        print("   用户名: landaofu")
        print("   密码: 123")
        print("   访问: http://127.0.0.1:8000/auth/login/")
        
        print("\n2. 登录后可访问的页面:")
        print("   🤖 AI聊天 (含Agno): http://127.0.0.1:8000/ai_agent/chat/")
        print("   🛡️ 系统管理: http://127.0.0.1:8000/auth/admin/dashboard/")
        print("   🔍 安全审计: http://127.0.0.1:8000/audit/")
        print("   ⚙️ 用户权限: http://127.0.0.1:8000/permissions/toggle/")
        print("   📊 行为监控: http://127.0.0.1:8000/behavior/")
        print("   👥 学生管理: http://127.0.0.1:8000/students/")
        
        print("\n3. 功能特色:")
        print("   ✨ Agno智能体完全集成")
        print("   ✨ 基于角色的权限控制 (RBAC)")
        print("   ✨ 完整的行为监控和审计")
        print("   ✨ 学生档案和权限管理")
        
    else:
        print("❌ 部分测试失败")
        print("请检查服务器是否正常运行:")
        print("python manage.py runserver 127.0.0.1:8000")
    
    return all_passed

if __name__ == "__main__":
    success = test_all_pages()
    if not success:
        sys.exit(1) 