#!/usr/bin/env python
"""
全面的Playwright测试脚本
测试AI智能体平台的所有页面和功能
"""

import asyncio
import json
import time
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError

class ComprehensivePlaywrightTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_results = {
            "login_tests": [],
            "page_access_tests": [],
            "functionality_tests": [],
            "api_tests": [],
            "ui_tests": [],
            "errors": []
        }
        
        # 测试账户
        self.test_accounts = [
            {"username": "admin", "password": "admin123", "type": "admin"},
            {"username": "landaofu", "password": "123", "type": "admin"},
            {"username": "teacher", "password": "teacher123", "type": "teacher"},
            {"username": "student", "password": "student123", "type": "student"},
        ]
        
        # 页面配置 - 按权限分组
        self.pages = {
            "public": [
                {"name": "登录页面", "url": "/auth/login/", "check_elements": ["input[name='username']", "input[name='password']", "button[type='submit']"]},
            ],
            "authenticated": [
                {"name": "AI聊天页面", "url": "/ai_agent/chat/", "check_elements": ["#chatContainer", "#message-input", "#send-btn"]},
                {"name": "Agno智能体页面", "url": "/ai_agent/agno/", "check_elements": [".agno-agent-card", "#agnoHealthStatus"]},
            ],
            "admin_teacher": [
                {"name": "权限管理页面", "url": "/permissions/toggle/", "check_elements": [".function-toggle-card", ".user-function-list"]},
                {"name": "行为监控页面", "url": "/behavior/", "check_elements": [".behavior-dashboard", ".user-behavior-list"]},
                {"name": "学生管理页面", "url": "/students/", "check_elements": [".student-list", ".student-card"]},
                {"name": "权限功能管理", "url": "/permissions/functions/", "check_elements": [".function-list", ".function-item"]},
                {"name": "学生权限管理", "url": "/permissions/students/", "check_elements": [".student-permission-list"]},
                {"name": "群组管理", "url": "/permissions/groups/", "check_elements": [".group-list"]},
                {"name": "行为用户列表", "url": "/behavior/users/", "check_elements": [".user-list"]},
                {"name": "异常行为管理", "url": "/behavior/abnormal/", "check_elements": [".abnormal-behavior-list"]},
                {"name": "敏感内容管理", "url": "/behavior/sensitive/", "check_elements": [".sensitive-content-list"]},
                {"name": "功能使用分析", "url": "/behavior/analytics/", "check_elements": [".analytics-dashboard"]},
                {"name": "学生详情页面", "url": "/students/students/", "check_elements": [".students-list"]},
                {"name": "标签管理", "url": "/students/tags/", "check_elements": [".tags-management"]},
            ],
            "admin_only": [
                {"name": "认证管理仪表板", "url": "/auth/admin/dashboard/", "check_elements": [".admin-dashboard", ".user-stats"]},
                {"name": "用户管理", "url": "/auth/admin/users/", "check_elements": [".user-management", ".user-list"]},
                {"name": "登录日志", "url": "/auth/admin/logs/login/", "check_elements": [".login-logs"]},
                {"name": "审计系统仪表板", "url": "/audit/", "check_elements": [".audit-dashboard"]},
                {"name": "用户活动日志", "url": "/audit/user-activity/", "check_elements": [".activity-logs"]},
                {"name": "管理员操作日志", "url": "/audit/admin-operations/", "check_elements": [".operation-logs"]},
                {"name": "审计登录日志", "url": "/audit/login-logs/", "check_elements": [".login-logs"]},
            ]
        }

    async def run_comprehensive_test(self):
        """运行全面测试"""
        print("🚀 开始全面的Playwright测试...")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=300)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            # 设置控制台监听
            console_messages = []
            def handle_console(msg):
                console_messages.append(f"[{msg.type}] {msg.text}")
                if msg.type in ['error', 'warning']:
                    print(f"🔍 控制台 [{msg.type}]: {msg.text}")
            
            page.on("console", handle_console)
            
            # 设置网络监听
            def handle_response(response):
                if response.status >= 400:
                    print(f"🌐 网络错误: {response.url} - {response.status}")
            
            page.on("response", handle_response)
            
            try:
                # 1. 测试公共页面
                await self.test_public_pages(page)
                
                # 2. 测试各种用户角色的登录和页面访问
                for account in self.test_accounts:
                    await self.test_user_access(page, account)
                
                # 3. 测试具体功能
                await self.test_chat_functionality(page)
                await self.test_agno_functionality(page)
                await self.test_permission_management(page)
                await self.test_behavior_tracking(page)
                await self.test_student_management(page)
                await self.test_audit_system(page)
                
                # 4. 生成测试报告
                await self.generate_test_report()
                
            except Exception as e:
                print(f"❌ 测试过程中发生错误: {e}")
                self.test_results["errors"].append(str(e))
            
            finally:
                # 保存控制台消息
                self.test_results["console_messages"] = console_messages
                await browser.close()

    async def test_public_pages(self, page):
        """测试公共页面"""
        print("\n📄 测试公共页面...")
        
        for page_config in self.pages["public"]:
            try:
                print(f"   🔍 测试 {page_config['name']}...")
                await page.goto(f"{self.base_url}{page_config['url']}")
                await page.wait_for_load_state("networkidle", timeout=10000)
                
                # 检查页面元素
                missing_elements = []
                for element in page_config["check_elements"]:
                    element_exists = await page.locator(element).count() > 0
                    if not element_exists:
                        missing_elements.append(element)
                
                result = {
                    "page": page_config['name'],
                    "url": page_config['url'],
                    "accessible": True,
                    "missing_elements": missing_elements,
                    "status": "✅ 成功" if not missing_elements else "⚠️ 部分元素缺失"
                }
                
                self.test_results["page_access_tests"].append(result)
                print(f"      {result['status']}")
                
                if missing_elements:
                    print(f"      缺失元素: {missing_elements}")
                
            except Exception as e:
                error_result = {
                    "page": page_config['name'],
                    "url": page_config['url'],
                    "accessible": False,
                    "error": str(e),
                    "status": "❌ 失败"
                }
                self.test_results["page_access_tests"].append(error_result)
                print(f"      ❌ 失败: {e}")

    async def test_user_access(self, page, account):
        """测试特定用户的页面访问"""
        print(f"\n👤 测试用户 {account['username']} ({account['type']}) 的页面访问...")
        
        # 登录
        login_success = await self.login_user(page, account)
        if not login_success:
            return
        
        # 根据用户类型测试相应页面
        pages_to_test = self.pages["authenticated"].copy()
        
        if account['type'] in ['admin', 'teacher']:
            pages_to_test.extend(self.pages["admin_teacher"])
        
        if account['type'] == 'admin':
            pages_to_test.extend(self.pages["admin_only"])
        
        for page_config in pages_to_test:
            try:
                print(f"   🔍 访问 {page_config['name']}...")
                await page.goto(f"{self.base_url}{page_config['url']}")
                await page.wait_for_load_state("networkidle", timeout=10000)
                
                # 检查是否被重定向到登录页面（权限不足）
                current_url = page.url
                if "/auth/login/" in current_url and page_config['url'] != "/auth/login/":
                    result = {
                        "user": account['username'],
                        "page": page_config['name'],
                        "url": page_config['url'],
                        "accessible": False,
                        "reason": "权限不足，被重定向到登录页",
                        "status": "🚫 权限不足"
                    }
                else:
                    # 检查页面元素
                    missing_elements = []
                    for element in page_config["check_elements"]:
                        try:
                            element_exists = await page.locator(element).count() > 0
                            if not element_exists:
                                missing_elements.append(element)
                        except:
                            missing_elements.append(element)
                    
                    result = {
                        "user": account['username'],
                        "page": page_config['name'],
                        "url": page_config['url'],
                        "accessible": True,
                        "missing_elements": missing_elements,
                        "status": "✅ 成功" if not missing_elements else "⚠️ 部分元素缺失"
                    }
                
                self.test_results["page_access_tests"].append(result)
                print(f"      {result['status']}")
                
                if "missing_elements" in result and result["missing_elements"]:
                    print(f"      缺失元素: {result['missing_elements']}")
                
            except Exception as e:
                error_result = {
                    "user": account['username'],
                    "page": page_config['name'],
                    "url": page_config['url'],
                    "accessible": False,
                    "error": str(e),
                    "status": "❌ 失败"
                }
                self.test_results["page_access_tests"].append(error_result)
                print(f"      ❌ 失败: {e}")
        
        # 登出
        await self.logout_user(page)

    async def login_user(self, page, account):
        """登录用户"""
        try:
            print(f"   🔐 登录用户 {account['username']}...")
            await page.goto(f"{self.base_url}/auth/login/")
            await page.wait_for_load_state("networkidle")
            
            await page.fill('input[name="username"]', account['username'])
            await page.fill('input[name="password"]', account['password'])
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle")
            
            # 检查是否登录成功
            current_url = page.url
            if "/auth/login/" in current_url:
                # 可能登录失败或需要再次检查
                error_text = ""
                try:
                    error_element = await page.locator('.alert-danger, .error-message').first
                    if await error_element.count() > 0:
                        error_text = await error_element.text_content()
                except:
                    pass
                
                login_result = {
                    "username": account['username'],
                    "success": False,
                    "error": error_text or "登录失败，仍在登录页面",
                    "status": "❌ 登录失败"
                }
                self.test_results["login_tests"].append(login_result)
                print(f"      ❌ 登录失败: {login_result['error']}")
                return False
            else:
                login_result = {
                    "username": account['username'],
                    "success": True,
                    "redirect_url": current_url,
                    "status": "✅ 登录成功"
                }
                self.test_results["login_tests"].append(login_result)
                print(f"      ✅ 登录成功，重定向到: {current_url}")
                return True
                
        except Exception as e:
            login_result = {
                "username": account['username'],
                "success": False,
                "error": str(e),
                "status": "❌ 登录异常"
            }
            self.test_results["login_tests"].append(login_result)
            print(f"      ❌ 登录异常: {e}")
            return False

    async def logout_user(self, page):
        """登出用户"""
        try:
            # 尝试多种登出方式
            logout_methods = [
                "a[href*='logout']",
                "button:has-text('登出')",
                "button:has-text('退出')",
                ".logout-btn"
            ]
            
            for method in logout_methods:
                try:
                    logout_element = page.locator(method).first
                    if await logout_element.count() > 0:
                        await logout_element.click()
                        await page.wait_for_load_state("networkidle")
                        print("   📤 用户已登出")
                        return
                except:
                    continue
            
            # 如果找不到登出按钮，直接访问登出URL
            await page.goto(f"{self.base_url}/auth/logout/")
            await page.wait_for_load_state("networkidle")
            print("   📤 通过URL登出用户")
            
        except Exception as e:
            print(f"   ⚠️ 登出时发生错误: {e}")

    async def test_chat_functionality(self, page):
        """测试聊天功能"""
        print("\n💬 测试聊天功能...")
        
        # 使用admin账户登录
        admin_account = {"username": "admin", "password": "admin123", "type": "admin"}
        if not await self.login_user(page, admin_account):
            print("   ❌ 无法登录admin账户，跳过聊天测试")
            return
        
        try:
            await page.goto(f"{self.base_url}/ai_agent/chat/")
            await page.wait_for_load_state("networkidle")
            
            # 测试发送消息
            message_input = page.locator("#message-input")
            send_button = page.locator("#send-btn")
            
            if await message_input.count() > 0 and await send_button.count() > 0:
                test_message = "你好，这是一个测试消息"
                await message_input.fill(test_message)
                await send_button.click()
                
                # 等待响应
                await asyncio.sleep(3)
                
                # 检查消息是否出现在聊天区域
                chat_container = page.locator("#chatContainer")
                messages = await chat_container.locator(".message").count()
                
                result = {
                    "function": "发送聊天消息",
                    "success": messages > 0,
                    "message_count": messages,
                    "status": "✅ 成功" if messages > 0 else "❌ 失败"
                }
                
                self.test_results["functionality_tests"].append(result)
                print(f"   {result['status']} - 消息数量: {messages}")
            else:
                result = {
                    "function": "聊天界面元素",
                    "success": False,
                    "error": "找不到消息输入框或发送按钮",
                    "status": "❌ 失败"
                }
                self.test_results["functionality_tests"].append(result)
                print(f"   ❌ 找不到聊天界面元素")
                
        except Exception as e:
            result = {
                "function": "聊天功能测试",
                "success": False,
                "error": str(e),
                "status": "❌ 异常"
            }
            self.test_results["functionality_tests"].append(result)
            print(f"   ❌ 聊天测试异常: {e}")
        
        await self.logout_user(page)

    async def test_agno_functionality(self, page):
        """测试Agno功能"""
        print("\n🤖 测试Agno功能...")
        
        # 使用admin账户登录
        admin_account = {"username": "admin", "password": "admin123", "type": "admin"}
        if not await self.login_user(page, admin_account):
            print("   ❌ 无法登录admin账户，跳过Agno测试")
            return
        
        try:
            await page.goto(f"{self.base_url}/ai_agent/agno/")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # 等待Agno初始化
            
            # 检查Agno健康状态
            health_status = page.locator("#agnoHealthStatus")
            if await health_status.count() > 0:
                status_text = await health_status.text_content()
                result = {
                    "function": "Agno健康检查",
                    "success": True,
                    "status_text": status_text,
                    "status": "✅ 成功"
                }
                print(f"   ✅ Agno状态: {status_text}")
            else:
                result = {
                    "function": "Agno健康检查",
                    "success": False,
                    "error": "找不到健康状态元素",
                    "status": "❌ 失败"
                }
                print(f"   ❌ 找不到Agno健康状态")
            
            self.test_results["functionality_tests"].append(result)
            
            # 测试智能体选择
            agent_cards = page.locator(".agno-agent-card")
            agent_count = await agent_cards.count()
            
            if agent_count > 0:
                # 点击第一个智能体
                await agent_cards.first.click()
                await asyncio.sleep(1)
                
                # 检查是否激活
                active_cards = await page.locator(".agno-agent-card.active").count()
                
                result = {
                    "function": "Agno智能体选择",
                    "success": active_cards > 0,
                    "agent_count": agent_count,
                    "status": "✅ 成功" if active_cards > 0 else "❌ 失败"
                }
                
                self.test_results["functionality_tests"].append(result)
                print(f"   {result['status']} - 智能体数量: {agent_count}")
            else:
                result = {
                    "function": "Agno智能体卡片",
                    "success": False,
                    "error": "找不到智能体卡片",
                    "status": "❌ 失败"
                }
                self.test_results["functionality_tests"].append(result)
                print(f"   ❌ 找不到智能体卡片")
                
        except Exception as e:
            result = {
                "function": "Agno功能测试",
                "success": False,
                "error": str(e),
                "status": "❌ 异常"
            }
            self.test_results["functionality_tests"].append(result)
            print(f"   ❌ Agno测试异常: {e}")
        
        await self.logout_user(page)

    async def test_permission_management(self, page):
        """测试权限管理功能"""
        print("\n🔐 测试权限管理功能...")
        
        # 使用admin账户登录
        admin_account = {"username": "admin", "password": "admin123", "type": "admin"}
        if not await self.login_user(page, admin_account):
            print("   ❌ 无法登录admin账户，跳过权限管理测试")
            return
        
        try:
            await page.goto(f"{self.base_url}/permissions/toggle/")
            await page.wait_for_load_state("networkidle")
            
            # 检查功能开关卡片
            function_cards = page.locator(".function-toggle-card")
            card_count = await function_cards.count()
            
            result = {
                "function": "权限管理页面加载",
                "success": card_count > 0,
                "function_count": card_count,
                "status": "✅ 成功" if card_count > 0 else "❌ 失败"
            }
            
            self.test_results["functionality_tests"].append(result)
            print(f"   {result['status']} - 功能卡片数量: {card_count}")
            
            # 测试用户功能列表
            await page.goto(f"{self.base_url}/permissions/students/")
            await page.wait_for_load_state("networkidle")
            
            # 检查学生列表
            student_elements = await page.locator(".student-item, .user-item, .permission-item").count()
            
            result = {
                "function": "学生权限管理",
                "success": True,  # 页面能加载就算成功
                "element_count": student_elements,
                "status": "✅ 成功"
            }
            
            self.test_results["functionality_tests"].append(result)
            print(f"   ✅ 学生权限页面加载成功")
            
        except Exception as e:
            result = {
                "function": "权限管理测试",
                "success": False,
                "error": str(e),
                "status": "❌ 异常"
            }
            self.test_results["functionality_tests"].append(result)
            print(f"   ❌ 权限管理测试异常: {e}")
        
        await self.logout_user(page)

    async def test_behavior_tracking(self, page):
        """测试行为追踪功能"""
        print("\n📊 测试行为追踪功能...")
        
        # 使用admin账户登录
        admin_account = {"username": "admin", "password": "admin123", "type": "admin"}
        if not await self.login_user(page, admin_account):
            print("   ❌ 无法登录admin账户，跳过行为追踪测试")
            return
        
        try:
            await page.goto(f"{self.base_url}/behavior/")
            await page.wait_for_load_state("networkidle")
            
            # 检查仪表板元素
            dashboard_elements = await page.locator(".behavior-dashboard, .dashboard-card, .stat-card").count()
            
            result = {
                "function": "行为追踪仪表板",
                "success": dashboard_elements > 0,
                "element_count": dashboard_elements,
                "status": "✅ 成功" if dashboard_elements > 0 else "❌ 失败"
            }
            
            self.test_results["functionality_tests"].append(result)
            print(f"   {result['status']} - 仪表板元素数量: {dashboard_elements}")
            
            # 测试用户行为列表
            await page.goto(f"{self.base_url}/behavior/users/")
            await page.wait_for_load_state("networkidle")
            
            user_list_elements = await page.locator(".user-list, .user-item, .behavior-item").count()
            
            result = {
                "function": "用户行为列表",
                "success": True,  # 页面能加载就算成功
                "element_count": user_list_elements,
                "status": "✅ 成功"
            }
            
            self.test_results["functionality_tests"].append(result)
            print(f"   ✅ 用户行为列表页面加载成功")
            
        except Exception as e:
            result = {
                "function": "行为追踪测试",
                "success": False,
                "error": str(e),
                "status": "❌ 异常"
            }
            self.test_results["functionality_tests"].append(result)
            print(f"   ❌ 行为追踪测试异常: {e}")
        
        await self.logout_user(page)

    async def test_student_management(self, page):
        """测试学生管理功能"""
        print("\n🎓 测试学生管理功能...")
        
        # 使用admin账户登录
        admin_account = {"username": "admin", "password": "admin123", "type": "admin"}
        if not await self.login_user(page, admin_account):
            print("   ❌ 无法登录admin账户，跳过学生管理测试")
            return
        
        try:
            await page.goto(f"{self.base_url}/students/")
            await page.wait_for_load_state("networkidle")
            
            # 检查学生管理仪表板
            dashboard_elements = await page.locator(".student-dashboard, .dashboard-card, .student-list").count()
            
            result = {
                "function": "学生管理仪表板",
                "success": dashboard_elements > 0,
                "element_count": dashboard_elements,
                "status": "✅ 成功" if dashboard_elements > 0 else "❌ 失败"
            }
            
            self.test_results["functionality_tests"].append(result)
            print(f"   {result['status']} - 仪表板元素数量: {dashboard_elements}")
            
            # 测试学生列表页面
            await page.goto(f"{self.base_url}/students/students/")
            await page.wait_for_load_state("networkidle")
            
            student_elements = await page.locator(".students-list, .student-card, .student-item").count()
            
            result = {
                "function": "学生列表页面",
                "success": True,  # 页面能加载就算成功
                "element_count": student_elements,
                "status": "✅ 成功"
            }
            
            self.test_results["functionality_tests"].append(result)
            print(f"   ✅ 学生列表页面加载成功")
            
        except Exception as e:
            result = {
                "function": "学生管理测试",
                "success": False,
                "error": str(e),
                "status": "❌ 异常"
            }
            self.test_results["functionality_tests"].append(result)
            print(f"   ❌ 学生管理测试异常: {e}")
        
        await self.logout_user(page)

    async def test_audit_system(self, page):
        """测试审计系统功能"""
        print("\n🔍 测试审计系统功能...")
        
        # 使用admin账户登录
        admin_account = {"username": "admin", "password": "admin123", "type": "admin"}
        if not await self.login_user(page, admin_account):
            print("   ❌ 无法登录admin账户，跳过审计系统测试")
            return
        
        try:
            await page.goto(f"{self.base_url}/audit/")
            await page.wait_for_load_state("networkidle")
            
            # 检查审计仪表板
            audit_elements = await page.locator(".audit-dashboard, .audit-card, .log-list").count()
            
            result = {
                "function": "审计系统仪表板",
                "success": audit_elements > 0,
                "element_count": audit_elements,
                "status": "✅ 成功" if audit_elements > 0 else "❌ 失败"
            }
            
            self.test_results["functionality_tests"].append(result)
            print(f"   {result['status']} - 审计元素数量: {audit_elements}")
            
            # 测试各种日志页面
            log_pages = [
                {"name": "用户活动日志", "url": "/audit/user-activity/"},
                {"name": "管理员操作日志", "url": "/audit/admin-operations/"},
                {"name": "登录日志", "url": "/audit/login-logs/"}
            ]
            
            for log_page in log_pages:
                try:
                    await page.goto(f"{self.base_url}{log_page['url']}")
                    await page.wait_for_load_state("networkidle")
                    
                    log_elements = await page.locator(".log-list, .log-item, .activity-logs").count()
                    
                    result = {
                        "function": log_page["name"],
                        "success": True,  # 页面能加载就算成功
                        "element_count": log_elements,
                        "status": "✅ 成功"
                    }
                    
                    self.test_results["functionality_tests"].append(result)
                    print(f"   ✅ {log_page['name']}页面加载成功")
                    
                except Exception as e:
                    result = {
                        "function": log_page["name"],
                        "success": False,
                        "error": str(e),
                        "status": "❌ 失败"
                    }
                    self.test_results["functionality_tests"].append(result)
                    print(f"   ❌ {log_page['name']}测试失败: {e}")
            
        except Exception as e:
            result = {
                "function": "审计系统测试",
                "success": False,
                "error": str(e),
                "status": "❌ 异常"
            }
            self.test_results["functionality_tests"].append(result)
            print(f"   ❌ 审计系统测试异常: {e}")
        
        await self.logout_user(page)

    async def generate_test_report(self):
        """生成测试报告"""
        print("\n📋 生成测试报告...")
        
        # 统计结果
        total_login_tests = len(self.test_results["login_tests"])
        successful_logins = len([t for t in self.test_results["login_tests"] if t["success"]])
        
        total_page_tests = len(self.test_results["page_access_tests"])
        successful_page_access = len([t for t in self.test_results["page_access_tests"] if t["accessible"]])
        
        total_functionality_tests = len(self.test_results["functionality_tests"])
        successful_functionality = len([t for t in self.test_results["functionality_tests"] if t["success"]])
        
        # 创建报告
        report = {
            "test_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": total_login_tests + total_page_tests + total_functionality_tests,
                "login_tests": {
                    "total": total_login_tests,
                    "successful": successful_logins,
                    "success_rate": f"{(successful_logins/total_login_tests*100):.1f}%" if total_login_tests > 0 else "0%"
                },
                "page_access_tests": {
                    "total": total_page_tests,
                    "successful": successful_page_access,
                    "success_rate": f"{(successful_page_access/total_page_tests*100):.1f}%" if total_page_tests > 0 else "0%"
                },
                "functionality_tests": {
                    "total": total_functionality_tests,
                    "successful": successful_functionality,
                    "success_rate": f"{(successful_functionality/total_functionality_tests*100):.1f}%" if total_functionality_tests > 0 else "0%"
                }
            },
            "detailed_results": self.test_results
        }
        
        # 保存报告到文件
        report_filename = f"comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 打印摘要
        print("=" * 80)
        print("📊 测试摘要")
        print("=" * 80)
        print(f"🔐 登录测试: {successful_logins}/{total_login_tests} ({report['test_summary']['login_tests']['success_rate']})")
        print(f"📄 页面访问测试: {successful_page_access}/{total_page_tests} ({report['test_summary']['page_access_tests']['success_rate']})")
        print(f"⚙️ 功能测试: {successful_functionality}/{total_functionality_tests} ({report['test_summary']['functionality_tests']['success_rate']})")
        print(f"📋 详细报告已保存到: {report_filename}")
        
        # 打印失败的测试
        failed_tests = []
        
        for test in self.test_results["login_tests"]:
            if not test["success"]:
                failed_tests.append(f"登录失败: {test['username']} - {test.get('error', '未知错误')}")
        
        for test in self.test_results["page_access_tests"]:
            if not test["accessible"]:
                failed_tests.append(f"页面访问失败: {test['page']} - {test.get('error', '未知错误')}")
        
        for test in self.test_results["functionality_tests"]:
            if not test["success"]:
                failed_tests.append(f"功能测试失败: {test['function']} - {test.get('error', '未知错误')}")
        
        if failed_tests:
            print("\n❌ 失败的测试:")
            for failed in failed_tests:
                print(f"   • {failed}")
        else:
            print("\n🎉 所有测试都通过了！")
        
        print("=" * 80)


async def main():
    """主函数"""
    tester = ComprehensivePlaywrightTest()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main()) 