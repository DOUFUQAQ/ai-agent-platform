#!/usr/bin/env python
"""
最终系统测试脚本 - 全面验证AI智能体平台功能
"""

import requests
import json
from datetime import datetime

class FinalSystemTester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.session = requests.Session()
        
        # 测试账户列表
        self.test_accounts = [
            ("admin", "admin123"),
            ("landaofu", "123"),
            ("teacher", "teacher123"),
            ("student", "student123"),
        ]
        
        # 页面测试配置
        self.pages = [
            ("AI聊天", "/ai_agent/chat/", True, "chat"),
            ("系统管理", "/auth/admin/dashboard/", True, "admin"),
            ("安全审计", "/audit/", True, "admin"),
            ("权限管理", "/permissions/toggle/", True, "admin_teacher"),
            ("行为监控", "/behavior/", True, "admin_teacher"),
            ("学生管理", "/students/", True, "admin_teacher"),
        ]
        
        self.logged_in_user = None
        self.test_results = {
            "login_tests": [],
            "page_tests": [],
            "functionality_tests": []
        }
    
    def test_login_attempts(self):
        """测试多个账户的登录"""
        print("🔐 测试登录功能...")
        
        for username, password in self.test_accounts:
            print(f"   尝试登录: {username}")
            
            # 获取登录页面和CSRF token
            login_url = f"{self.base_url}/auth/login/"
            try:
                response = self.session.get(login_url)
                if response.status_code != 200:
                    print(f"     ❌ 无法访问登录页面")
                    continue
                
                # 提取CSRF token
                import re
                csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]*)"', response.text)
                if not csrf_match:
                    print(f"     ❌ 无法获取CSRF token")
                    continue
                
                csrf_token = csrf_match.group(1)
                
                # 尝试登录
                login_data = {
                    'username': username,
                    'password': password,
                    'csrfmiddlewaretoken': csrf_token
                }
                
                login_response = self.session.post(f"{self.base_url}/auth/api/login/", data=login_data)
                
                if login_response.status_code == 302:
                    redirect_url = login_response.headers.get('Location', '')
                    if 'chat' in redirect_url or 'dashboard' in redirect_url:
                        print(f"     ✅ 登录成功，重定向到: {redirect_url}")
                        self.logged_in_user = username
                        self.test_results["login_tests"].append({
                            "username": username,
                            "success": True,
                            "redirect": redirect_url
                        })
                        return True
                    else:
                        print(f"     ⚠️ 登录后重定向异常: {redirect_url}")
                elif login_response.status_code == 200:
                    if '错误' in login_response.text or 'error' in login_response.text.lower():
                        print(f"     ❌ 登录失败: 用户名或密码错误")
                    else:
                        print(f"     ⚠️ 登录状态不明")
                else:
                    print(f"     ❌ 登录请求失败: {login_response.status_code}")
                
                self.test_results["login_tests"].append({
                    "username": username,
                    "success": False,
                    "status_code": login_response.status_code
                })
                
            except Exception as e:
                print(f"     ❌ 登录过程出错: {str(e)[:50]}")
        
        return False
    
    def test_page_functionality(self):
        """测试页面功能"""
        print("\n📋 测试页面功能...")
        print("-" * 60)
        
        for name, path, requires_login, permission_level in self.pages:
            try:
                url = f"{self.base_url}{path}"
                response = self.session.get(url, timeout=10)
                
                result = {
                    "name": name,
                    "path": path,
                    "status": response.status_code,
                    "success": False,
                    "issues": []
                }
                
                if response.status_code == 200:
                    print(f"✅ {name:<15} 页面加载成功")
                    result["success"] = True
                    
                    # 检查页面内容
                    content_issues = self.analyze_page_content(response.text, name)
                    if content_issues:
                        print(f"   ⚠️ 内容问题: {', '.join(content_issues)}")
                        result["issues"] = content_issues
                    
                elif response.status_code == 302:
                    redirect_url = response.headers.get('Location', '')
                    if 'login' in redirect_url:
                        if self.logged_in_user:
                            print(f"⚠️ {name:<15} 意外重定向到登录页面")
                            result["issues"].append("权限检查失败")
                        else:
                            print(f"✅ {name:<15} 正确重定向到登录页面")
                            result["success"] = True
                    else:
                        print(f"✅ {name:<15} 重定向到: {redirect_url[:50]}...")
                        result["success"] = True
                else:
                    print(f"❌ {name:<15} HTTP错误: {response.status_code}")
                    result["issues"].append(f"HTTP {response.status_code}")
                
                self.test_results["page_tests"].append(result)
                
            except Exception as e:
                print(f"❌ {name:<15} 请求异常: {str(e)[:50]}")
                self.test_results["page_tests"].append({
                    "name": name,
                    "path": path,
                    "success": False,
                    "error": str(e)
                })
    
    def analyze_page_content(self, content, page_name):
        """分析页面内容"""
        issues = []
        
        # 基础检查
        if len(content) < 500:
            issues.append("页面内容过少")
        
        if 'TemplateDoesNotExist' in content:
            issues.append("模板文件缺失")
        
        if 'ImportError' in content:
            issues.append("导入错误")
        
        if 'DisallowedHost' in content:
            issues.append("Django配置错误")
        
        # 特定页面检查
        if page_name == "AI聊天":
            required_elements = ['chat', 'message', 'input']
            missing = [elem for elem in required_elements if elem.lower() not in content.lower()]
            if missing:
                issues.append(f"缺少聊天元素: {', '.join(missing)}")
        
        elif page_name == "系统管理":
            required_elements = ['dashboard', '管理', 'admin']
            missing = [elem for elem in required_elements if elem.lower() not in content.lower()]
            if missing:
                issues.append(f"缺少管理元素: {', '.join(missing)}")
        
        return issues
    
    def test_api_endpoints(self):
        """测试API端点"""
        print("\n🔌 测试API端点...")
        
        api_endpoints = [
            ("/ai_agent/api/agno/health/", "Agno健康检查"),
            ("/ai_agent/api/chat/create/", "创建聊天会话"),
        ]
        
        for endpoint, description in api_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = self.session.get(url, timeout=5)
                
                if response.status_code == 200:
                    print(f"✅ {description:<20} API正常")
                elif response.status_code == 403:
                    print(f"⚠️ {description:<20} 需要权限")
                else:
                    print(f"❌ {description:<20} 状态码: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {description:<20} 请求失败: {str(e)[:30]}")
    
    def generate_comprehensive_report(self):
        """生成全面的测试报告"""
        print("\n" + "=" * 80)
        print("📊 AI智能体平台 - 全面测试报告")
        print("=" * 80)
        
        # 登录测试结果
        login_success = len([t for t in self.test_results["login_tests"] if t["success"]])
        login_total = len(self.test_results["login_tests"])
        print(f"\n🔐 登录测试: {login_success}/{login_total} 成功")
        
        if self.logged_in_user:
            print(f"   ✅ 当前登录用户: {self.logged_in_user}")
        else:
            print("   ❌ 无法登录任何账户")
        
        # 页面测试结果
        page_success = len([t for t in self.test_results["page_tests"] if t["success"]])
        page_total = len(self.test_results["page_tests"])
        print(f"\n📋 页面测试: {page_success}/{page_total} 通过")
        
        # 详细问题
        failed_pages = [t for t in self.test_results["page_tests"] if not t["success"] or t.get("issues")]
        if failed_pages:
            print("\n🔴 需要修复的问题:")
            for page in failed_pages:
                print(f"   • {page['name']}")
                if page.get("issues"):
                    for issue in page["issues"]:
                        print(f"     - {issue}")
        
        # 总体评估
        overall_score = ((login_success/login_total if login_total > 0 else 0) * 0.3 + 
                        (page_success/page_total if page_total > 0 else 0) * 0.7) * 100
        
        print(f"\n🎯 总体评分: {overall_score:.1f}/100")
        
        if overall_score >= 90:
            print("🎉 系统状态: 优秀 - 平台运行良好！")
        elif overall_score >= 70:
            print("👍 系统状态: 良好 - 有小问题需要修复")
        elif overall_score >= 50:
            print("⚠️ 系统状态: 一般 - 需要重点修复")
        else:
            print("❌ 系统状态: 差 - 需要大量修复工作")
        
        # 修复建议
        print("\n🔧 修复建议:")
        if not self.logged_in_user:
            print("1. 【高优先级】修复登录功能 - 检查用户密码或认证逻辑")
        
        if any(t.get("issues") for t in self.test_results["page_tests"]):
            print("2. 【中优先级】修复页面内容问题 - 检查模板和视图")
        
        if overall_score >= 90:
            print("   ✨ 系统已基本完善，可以进行功能扩展")
        
        # 保存报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_score": overall_score,
            "logged_in_user": self.logged_in_user,
            "results": self.test_results
        }
        
        with open("final_system_test_report.json", "w", encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存到: final_system_test_report.json")
    
    def run_comprehensive_test(self):
        """运行全面测试"""
        print("🚀 AI智能体平台 - 全面系统测试")
        print(f"服务器: {self.base_url}")
        print("=" * 80)
        
        # 检查服务器
        try:
            response = requests.get(self.base_url, timeout=5)
            print("✅ Django服务器运行正常")
        except:
            print("❌ Django服务器未运行")
            return False
        
        # 执行各项测试
        login_success = self.test_login_attempts()
        self.test_page_functionality()
        self.test_api_endpoints()
        
        # 生成报告
        self.generate_comprehensive_report()
        
        return True

if __name__ == "__main__":
    tester = FinalSystemTester()
    tester.run_comprehensive_test() 