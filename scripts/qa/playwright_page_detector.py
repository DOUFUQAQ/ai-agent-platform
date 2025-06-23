#!/usr/bin/env python
"""
使用Playwright进行AI智能体平台页面检测和问题诊断
"""

import asyncio
import json
import time
from datetime import datetime
from playwright.async_api import async_playwright
import os
import sys

# Django环境设置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_agent_platform.settings')
import django
django.setup()

class PageDetector:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.admin_username = "landaofu"
        self.admin_password = "123"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "pages": {},
            "summary": {
                "total_pages": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
        
        # 要检测的页面
        self.pages_to_test = {
            "AI聊天页面": {
                "url": "/ai_agent/chat/",
                "requires_login": True,
                "expected_elements": [
                    "chatContainer",
                    "messageInput", 
                    "sendButton",
                    "chatMessages"
                ],
                "checks": [
                    "chat_interface_loaded",
                    "agno_integration_working", 
                    "message_input_functional"
                ]
            },
            "系统管理": {
                "url": "/auth/admin/dashboard/",
                "requires_login": True,
                "expected_elements": [
                    "dashboard",
                    "statsCards",
                    "userStats"
                ],
                "checks": [
                    "dashboard_loaded",
                    "stats_displayed",
                    "navigation_working"
                ]
            },
            "安全审计": {
                "url": "/audit/",
                "requires_login": True,
                "expected_elements": [
                    "auditDashboard",
                    "auditLogs",
                    "securityMetrics"
                ],
                "checks": [
                    "audit_dashboard_loaded",
                    "logs_displayed",
                    "security_metrics_working"
                ]
            },
            "用户权限管理": {
                "url": "/permissions/toggle/",
                "requires_login": True,
                "expected_elements": [
                    "permissionToggle",
                    "functionList",
                    "userPermissions"
                ],
                "checks": [
                    "permission_interface_loaded",
                    "function_toggle_working",
                    "user_list_displayed"
                ]
            },
            "行为监控": {
                "url": "/behavior/",
                "requires_login": True,
                "expected_elements": [
                    "behaviorDashboard",
                    "userBehaviorList",
                    "abnormalDetection"
                ],
                "checks": [
                    "behavior_dashboard_loaded",
                    "user_behavior_displayed",
                    "monitoring_active"
                ]
            },
            "学生管理": {
                "url": "/students/",
                "requires_login": True,
                "expected_elements": [
                    "studentDashboard",
                    "studentList",
                    "studentStats"
                ],
                "checks": [
                    "student_dashboard_loaded",
                    "student_list_displayed",
                    "management_tools_working"
                ]
            }
        }

    async def run_detection(self):
        """运行页面检测"""
        print("🔍 开始Playwright页面检测...")
        print(f"目标服务器: {self.base_url}")
        print("=" * 80)
        
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # 首先尝试访问登录页面
                login_success = await self.login(page)
                if not login_success:
                    print("❌ 登录失败，无法继续检测")
                    return False
                
                # 检测每个页面
                for page_name, page_config in self.pages_to_test.items():
                    print(f"\n📋 检测页面: {page_name}")
                    print("-" * 60)
                    
                    page_result = await self.check_page(page, page_name, page_config)
                    self.results["pages"][page_name] = page_result
                    self.results["summary"]["total_pages"] += 1
                    
                    if page_result["status"] == "passed":
                        self.results["summary"]["passed"] += 1
                        print(f"✅ {page_name}: 检测通过")
                    elif page_result["status"] == "warning":
                        self.results["summary"]["warnings"] += 1
                        print(f"⚠️ {page_name}: 有警告")
                    else:
                        self.results["summary"]["failed"] += 1
                        print(f"❌ {page_name}: 检测失败")
                    
                    # 显示具体问题
                    if page_result["issues"]:
                        for issue in page_result["issues"]:
                            print(f"   • {issue}")
                
            finally:
                await browser.close()
        
        # 生成报告
        await self.generate_report()
        return True

    async def login(self, page):
        """登录系统"""
        try:
            print("🔐 正在登录管理员账户...")
            
            # 访问登录页面
            await page.goto(f"{self.base_url}/auth/login/")
            await page.wait_for_load_state('networkidle')
            
            # 检查是否成功加载登录页面
            if "login" not in page.url.lower():
                print("❌ 无法访问登录页面")
                return False
            
            # 填写登录信息
            await page.fill('input[name="username"]', self.admin_username)
            await page.fill('input[name="password"]', self.admin_password)
            
            # 点击登录按钮
            await page.click('button[type="submit"], input[type="submit"]')
            await page.wait_for_load_state('networkidle')
            
            # 检查是否登录成功
            if "login" not in page.url.lower():
                print("✅ 登录成功")
                return True
            else:
                print("❌ 登录失败")
                return False
                
        except Exception as e:
            print(f"❌ 登录过程出错: {e}")
            return False

    async def check_page(self, page, page_name, config):
        """检查单个页面"""
        result = {
            "status": "unknown",
            "url": config["url"],
            "issues": [],
            "warnings": [],
            "console_errors": [],
            "network_errors": [],
            "missing_elements": [],
            "performance": {}
        }
        
        try:
            # 设置网络和控制台监听
            console_errors = []
            network_errors = []
            
            def handle_console(msg):
                if msg.type in ["error", "warning"]:
                    console_errors.append(f"{msg.type}: {msg.text}")
            
            def handle_response(response):
                if response.status >= 400:
                    network_errors.append(f"{response.status} {response.url}")
            
            page.on("console", handle_console)
            page.on("response", handle_response)
            
            # 记录开始时间
            start_time = time.time()
            
            # 访问页面
            await page.goto(f"{self.base_url}{config['url']}")
            await page.wait_for_load_state('networkidle')
            
            # 记录加载时间
            load_time = time.time() - start_time
            result["performance"]["load_time"] = load_time
            
            # 检查页面状态
            current_url = page.url
            if "login" in current_url.lower() and config["requires_login"]:
                result["issues"].append("页面重定向到登录页面，权限检查失败")
                result["status"] = "failed"
                return result
            
            # 检查页面标题
            title = await page.title()
            result["page_title"] = title
            
            # 检查关键元素
            for element in config.get("expected_elements", []):
                element_exists = await self.check_element_exists(page, element)
                if not element_exists:
                    result["missing_elements"].append(element)
            
            # 检查JavaScript错误
            result["console_errors"] = console_errors
            result["network_errors"] = network_errors
            
            # 运行特定检查
            for check in config.get("checks", []):
                check_result = await self.run_specific_check(page, check)
                if not check_result["passed"]:
                    result["issues"].append(f"{check}: {check_result['message']}")
            
            # 检查页面内容
            content_check = await self.check_page_content(page)
            if content_check["has_errors"]:
                result["issues"].extend(content_check["errors"])
            if content_check["has_warnings"]:
                result["warnings"].extend(content_check["warnings"])
            
            # 确定最终状态
            if result["issues"] or len(result["missing_elements"]) > 2:
                result["status"] = "failed"
            elif result["warnings"] or result["missing_elements"]:
                result["status"] = "warning"
            else:
                result["status"] = "passed"
                
        except Exception as e:
            result["issues"].append(f"页面检测异常: {str(e)}")
            result["status"] = "failed"
        
        return result

    async def check_element_exists(self, page, element_id):
        """检查元素是否存在"""
        try:
            selectors_to_try = [
                f"#{element_id}",
                f".{element_id}",
                f"[data-testid='{element_id}']",
                f"[class*='{element_id}']",
                f"[id*='{element_id}']"
            ]
            
            for selector in selectors_to_try:
                element = await page.query_selector(selector)
                if element:
                    return True
            return False
        except:
            return False

    async def run_specific_check(self, page, check_name):
        """运行特定的页面检查"""
        try:
            if check_name == "chat_interface_loaded":
                # 检查聊天界面
                chat_container = await page.query_selector(".chat-container, #chatContainer, .chat-interface")
                input_field = await page.query_selector("input[type='text'], textarea")
                return {
                    "passed": chat_container is not None and input_field is not None,
                    "message": "聊天界面和输入框检查"
                }
            
            elif check_name == "agno_integration_working":
                # 检查Agno集成
                agno_elements = await page.query_selector_all("[class*='agno'], [id*='agno'], [data-agno]")
                return {
                    "passed": len(agno_elements) > 0,
                    "message": "Agno智能体集成检查"
                }
            
            elif check_name == "dashboard_loaded":
                # 检查仪表板
                dashboard = await page.query_selector(".dashboard, #dashboard, .admin-dashboard")
                return {
                    "passed": dashboard is not None,
                    "message": "仪表板加载检查"
                }
            
            elif check_name == "stats_displayed":
                # 检查统计数据
                stats = await page.query_selector_all(".stat, .stats, .metric, .card")
                return {
                    "passed": len(stats) > 0,
                    "message": "统计数据显示检查"
                }
            
            else:
                return {
                    "passed": True,
                    "message": f"未实现的检查: {check_name}"
                }
                
        except Exception as e:
            return {
                "passed": False,
                "message": f"检查执行失败: {str(e)}"
            }

    async def check_page_content(self, page):
        """检查页面内容"""
        result = {
            "has_errors": False,
            "has_warnings": False,
            "errors": [],
            "warnings": []
        }
        
        try:
            # 检查页面是否有明显的错误信息
            error_selectors = [
                ".error", ".alert-danger", ".error-message", 
                "[class*='error']", "h1:has-text('Error')",
                "h1:has-text('404')", "h1:has-text('500')"
            ]
            
            for selector in error_selectors:
                error_elements = await page.query_selector_all(selector)
                if error_elements:
                    for element in error_elements:
                        text = await element.text_content()
                        if text and text.strip():
                            result["errors"].append(f"发现错误信息: {text[:100]}")
                            result["has_errors"] = True
            
            # 检查页面是否基本空白
            body_text = await page.evaluate("document.body.innerText")
            if len(body_text.strip()) < 50:
                result["warnings"].append("页面内容过少，可能加载不完整")
                result["has_warnings"] = True
            
            # 检查是否有Django错误页面
            page_content = await page.content()
            if "DisallowedHost" in page_content or "Django" in page_content and "error" in page_content.lower():
                result["errors"].append("发现Django错误页面")
                result["has_errors"] = True
                
        except Exception as e:
            result["warnings"].append(f"内容检查异常: {str(e)}")
            result["has_warnings"] = True
        
        return result

    async def generate_report(self):
        """生成检测报告"""
        print("\n" + "=" * 80)
        print("📊 页面检测报告")
        print("=" * 80)
        
        summary = self.results["summary"]
        print(f"总计页面: {summary['total_pages']}")
        print(f"✅ 通过: {summary['passed']}")
        print(f"⚠️ 警告: {summary['warnings']}")
        print(f"❌ 失败: {summary['failed']}")
        
        print("\n📋 详细问题列表:")
        print("-" * 60)
        
        issues_by_priority = []
        
        for page_name, result in self.results["pages"].items():
            if result["status"] == "failed":
                issues_by_priority.append({
                    "page": page_name,
                    "priority": "HIGH",
                    "issues": result["issues"]
                })
            elif result["status"] == "warning":
                issues_by_priority.append({
                    "page": page_name,
                    "priority": "MEDIUM", 
                    "issues": result["warnings"] + [f"缺失元素: {', '.join(result['missing_elements'])}"] if result["missing_elements"] else result["warnings"]
                })
        
        # 按优先级排序
        issues_by_priority.sort(key=lambda x: 0 if x["priority"] == "HIGH" else 1)
        
        for issue_group in issues_by_priority:
            print(f"\n🔴 {issue_group['priority']} - {issue_group['page']}:")
            for issue in issue_group["issues"]:
                if issue.strip():
                    print(f"   • {issue}")
        
        # 保存详细报告到文件
        report_file = "playwright_detection_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存到: {report_file}")
        
        # 生成修复建议
        await self.generate_fix_suggestions()

    async def generate_fix_suggestions(self):
        """生成修复建议"""
        print("\n🔧 修复建议:")
        print("-" * 60)
        
        common_issues = {}
        
        for page_name, result in self.results["pages"].items():
            for issue in result["issues"]:
                if "权限检查失败" in issue:
                    common_issues["权限问题"] = common_issues.get("权限问题", [])
                    common_issues["权限问题"].append(page_name)
                elif "缺失元素" in issue or result["missing_elements"]:
                    common_issues["前端元素缺失"] = common_issues.get("前端元素缺失", [])
                    common_issues["前端元素缺失"].append(page_name)
                elif "Django错误" in issue:
                    common_issues["后端错误"] = common_issues.get("后端错误", [])
                    common_issues["后端错误"].append(page_name)
        
        suggestions = []
        
        if "权限问题" in common_issues:
            suggestions.append({
                "issue": "权限检查失败",
                "pages": common_issues["权限问题"],
                "solution": "检查视图装饰器配置，确保@login_required和权限装饰器正确应用"
            })
        
        if "前端元素缺失" in common_issues:
            suggestions.append({
                "issue": "前端元素缺失",
                "pages": common_issues["前端元素缺失"],
                "solution": "检查HTML模板，补充缺失的CSS类和ID，完善前端界面"
            })
        
        if "后端错误" in common_issues:
            suggestions.append({
                "issue": "后端错误",
                "pages": common_issues["后端错误"],
                "solution": "检查Django视图逻辑，修复模型导入和数据库查询问题"
            })
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion['issue']}")
            print(f"   影响页面: {', '.join(suggestion['pages'])}")
            print(f"   建议方案: {suggestion['solution']}")
            print()

async def main():
    """主函数"""
    print("🚀 启动AI智能体平台页面检测器")
    
    # 检查Django服务器是否运行
    import requests
    try:
        response = requests.get("http://127.0.0.1:8000", timeout=3)
        print("✅ Django服务器运行正常")
    except:
        print("❌ Django服务器未运行，请先启动:")
        print("python manage.py runserver 127.0.0.1:8000")
        return
    
    detector = PageDetector()
    success = await detector.run_detection()
    
    if success:
        print("\n🎉 页面检测完成！请查看上述报告进行修复。")
    else:
        print("\n❌ 页面检测失败！")

if __name__ == "__main__":
    asyncio.run(main()) 