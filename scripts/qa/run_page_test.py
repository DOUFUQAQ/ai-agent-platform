#!/usr/bin/env python
"""
AI智能体平台页面测试脚本
"""
import asyncio
from playwright.async_api import async_playwright

async def test_all_pages():
    print("🚀 开始测试AI智能体平台")
    print("请确保Django服务器在 localhost:8000 运行")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=800)
        page = await browser.new_page()
        
        results = []
        
        try:
            # 1. 测试登录页面
            print("\n1. 测试登录页面...")
            await page.goto("http://localhost:8000/auth/login/")
            await page.wait_for_load_state("networkidle")
            
            username_field = await page.locator('input[name="username"]').count()
            password_field = await page.locator('input[name="password"]').count()
            
            if username_field > 0 and password_field > 0:
                print("   ✅ 登录页面正常")
                results.append("✅ 登录页面")
            else:
                print("   ❌ 登录页面异常")
                results.append("❌ 登录页面")
                return
            
            # 2. 执行登录
            print("\n2. 执行管理员登录...")
            await page.fill('input[name="username"]', 'admin')
            await page.fill('input[name="password"]', 'admin123')
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle")
            
            if "/auth/login/" not in page.url:
                print("   ✅ 管理员登录成功")
                results.append("✅ 管理员登录")
            else:
                print("   ❌ 管理员登录失败")
                results.append("❌ 管理员登录")
                return
            
            # 3. 测试各个页面
            test_pages = [
                ("AI聊天页面", "/ai_agent/chat/"),
                ("Agno智能体页面", "/ai_agent/agno/"),
                ("权限管理页面", "/permissions/toggle/"),
                ("行为监控页面", "/behavior/"),
                ("学生管理页面", "/students/"),
                ("审计系统页面", "/audit/"),
                ("功能管理页面", "/permissions/functions/"),
                ("学生权限管理", "/permissions/students/"),
                ("群组管理页面", "/permissions/groups/"),
                ("用户管理页面", "/auth/admin/users/"),
                ("用户活动日志", "/audit/user-activity/"),
                ("管理员操作日志", "/audit/admin-operations/"),
                ("登录日志页面", "/audit/login-logs/"),
            ]
            
            for i, (name, url) in enumerate(test_pages, 3):
                print(f"\n{i}. 测试{name}...")
                try:
                    await page.goto(f"http://localhost:8000{url}")
                    await page.wait_for_load_state("networkidle", timeout=8000)
                    await asyncio.sleep(1)
                    
                    if "/auth/login/" in page.url:
                        print(f"   🚫 权限不足")
                        results.append(f"🚫 {name}")
                    else:
                        title = await page.title()
                        print(f"   ✅ 页面正常 - {title}")
                        results.append(f"✅ {name}")
                        
                except Exception as e:
                    print(f"   ❌ 页面异常 - {str(e)[:30]}...")
                    results.append(f"❌ {name}")
            
            # 4. 测试聊天功能
            print(f"\n{len(test_pages)+3}. 测试聊天功能...")
            try:
                await page.goto("http://localhost:8000/ai_agent/chat/")
                await page.wait_for_load_state("networkidle")
                
                chat_input = await page.locator("#message-input").count()
                send_btn = await page.locator("#send-btn").count()
                
                if chat_input > 0 and send_btn > 0:
                    await page.fill("#message-input", "你好，测试消息")
                    await page.click("#send-btn")
                    await asyncio.sleep(3)
                    
                    messages = await page.locator("#chatContainer .message").count()
                    if messages > 0:
                        print(f"   ✅ 聊天功能正常 - {messages}条消息")
                        results.append("✅ 聊天功能")
                    else:
                        print("   ⚠️ 聊天功能 - 无回复")
                        results.append("⚠️ 聊天功能")
                else:
                    print("   ❌ 聊天功能 - 元素缺失")
                    results.append("❌ 聊天功能")
                    
            except Exception as e:
                print(f"   ❌ 聊天功能异常 - {str(e)[:30]}...")
                results.append("❌ 聊天功能")
            
            # 5. 测试Agno功能
            print(f"\n{len(test_pages)+4}. 测试Agno功能...")
            try:
                await page.goto("http://localhost:8000/ai_agent/agno/")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                
                health_status = await page.locator("#agnoHealthStatus").count()
                if health_status > 0:
                    status_text = await page.locator("#agnoHealthStatus").text_content()
                    print(f"   ✅ Agno状态: {status_text}")
                    
                    agent_cards = await page.locator(".agno-agent-card").count()
                    print(f"   ✅ 智能体卡片: {agent_cards}个")
                    results.append("✅ Agno功能")
                else:
                    print("   ❌ Agno状态元素未找到")
                    results.append("❌ Agno功能")
                    
            except Exception as e:
                print(f"   ❌ Agno功能异常 - {str(e)[:30]}...")
                results.append("❌ Agno功能")
            
        except Exception as e:
            print(f"❌ 测试过程异常: {e}")
            results.append(f"❌ 测试异常: {e}")
        
        finally:
            await browser.close()
        
        # 生成报告
        print("\n" + "=" * 50)
        print("📊 测试报告")
        print("=" * 50)
        
        success_count = len([r for r in results if r.startswith("✅")])
        warning_count = len([r for r in results if r.startswith("⚠️")])
        denied_count = len([r for r in results if r.startswith("🚫")])
        failed_count = len([r for r in results if r.startswith("❌")])
        total_count = len(results)
        
        print(f"✅ 成功: {success_count}")
        print(f"⚠️ 警告: {warning_count}")
        print(f"🚫 权限不足: {denied_count}")
        print(f"❌ 失败: {failed_count}")
        print(f"📊 总计: {total_count}")
        
        if total_count > 0:
            success_rate = (success_count + warning_count) / total_count * 100
            print(f"📈 成功率: {success_rate:.1f}%")
        
        print("\n📝 详细结果:")
        for result in results:
            print(f"   {result}")
        
        print("\n" + "=" * 50)
        print("🏁 测试完成!")

if __name__ == "__main__":
    asyncio.run(test_all_pages()) 