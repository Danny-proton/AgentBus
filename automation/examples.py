"""
AgentBus Browser Automation Examples

浏览器自动化使用示例
"""

import asyncio
import logging
from .browser import BrowserAutomation, BrowserConfig
from .screenshot import ScreenshotManager
from .form_handler import FormHandler
from .page_navigator import PageNavigator
from .element_finder import ElementFinder

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_browser_example():
    """基本浏览器使用示例"""
    print("=== 基本浏览器使用示例 ===")
    
    # 配置浏览器
    config = BrowserConfig(
        headless=False,  # 显示浏览器窗口
        viewport_width=1920,
        viewport_height=1080
    )
    
    # 使用异步上下文管理器
    async with BrowserAutomation(config) as browser:
        # 导航到网站
        await browser.navigate_to("https://www.baidu.com")
        
        # 截取截图
        screenshot_path = await browser.take_screenshot(
            path="./examples/baidu_homepage.png",
            full_page=True
        )
        print(f"截图已保存: {screenshot_path}")
        
        # 查找搜索框并输入内容
        await browser.type_text(
            selector="input[name='wd']",
            value="Playwright 自动化测试"
        )
        
        # 点击搜索按钮
        await browser.click_element(
            selector="input[type='submit']"
        )
        
        # 等待页面加载
        await browser.page_navigator.wait_for_load_state("networkidle")
        
        # 获取页面信息
        page_info = await browser.get_page_info()
        print(f"页面标题: {page_info.get('title', 'Unknown')}")
        print(f"当前URL: {page_info.get('url', 'Unknown')}")
        
        # 截取搜索结果截图
        search_screenshot = await browser.take_screenshot(
            path="./examples/baidu_search_results.png",
            full_page=True
        )
        print(f"搜索结果截图: {search_screenshot}")


async def form_automation_example():
    """表单自动化示例"""
    print("=== 表单自动化示例 ===")
    
    config = BrowserConfig(headless=False)
    
    async with BrowserAutomation(config) as browser:
        # 创建一个测试页面
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>测试表单</title>
        </head>
        <body>
            <h1>用户注册表单</h1>
            <form id="registerForm">
                <label for="username">用户名:</label>
                <input type="text" id="username" name="username" required><br><br>
                
                <label for="email">邮箱:</label>
                <input type="email" id="email" name="email" required><br><br>
                
                <label for="password">密码:</label>
                <input type="password" id="password" name="password" required><br><br>
                
                <label for="confirmPassword">确认密码:</label>
                <input type="password" id="confirmPassword" name="confirmPassword" required><br><br>
                
                <label for="gender">性别:</label>
                <select id="gender" name="gender">
                    <option value="male">男</option>
                    <option value="female">女</option>
                </select><br><br>
                
                <label for="newsletter">
                    <input type="checkbox" id="newsletter" name="newsletter">
                    订阅新闻邮件
                </label><br><br>
                
                <input type="submit" value="注册">
            </form>
        </body>
        </html>
        """
        
        # 打开数据URL
        await browser.navigate_to(f"data:text/html,{test_html}")
        
        # 填写表单数据
        form_data = {
            "input[name='username']": "testuser123",
            "input[name='email']": "test@example.com",
            "input[name='password']": "password123",
            "input[name='confirmPassword']": "password123",
            "select[name='gender']": "male",
            "input[name='newsletter']": True
        }
        
        # 填写表单
        success = await browser.fill_form(form_data)
        print(f"表单填写: {'成功' if success else '失败'}")
        
        # 验证表单
        validation = await browser.form_handler.validate_form(form_data)
        print(f"表单验证结果: {validation}")
        
        # 提交表单
        submit_success = await browser.form_handler.submit_form("input[type='submit']")
        print(f"表单提交: {'成功' if submit_success else '失败'}")
        
        # 截图保存结果
        await browser.take_screenshot("./examples/form_filled.png")


async def advanced_interaction_example():
    """高级交互示例"""
    print("=== 高级交互示例 ===")
    
    config = BrowserConfig(headless=False)
    
    async with BrowserAutomation(config) as browser:
        # 访问一个复杂的网页
        await browser.navigate_to("https://example.com")
        
        # 查找多个元素
        links = await browser.find_elements(selector="a")
        print(f"找到 {len(links)} 个链接")
        
        # 查找按钮
        buttons = await browser.find_elements(selector="button")
        print(f"找到 {len(buttons)} 个按钮")
        
        # 获取页面控制台信息
        console_messages = await browser.get_page_console()
        print(f"控制台消息数量: {len(console_messages)}")
        
        # 滚动页面
        await browser.page_navigator.scroll_to_bottom()
        await asyncio.sleep(1)
        await browser.page_navigator.scroll_to_top()
        
        # 等待特定元素出现
        element_found = await browser.element_finder.wait_for_element(
            selector="h1",
            timeout=5000
        )
        print(f"找到标题元素: {element_found}")
        
        # 截图保存
        await browser.take_screenshot("./examples/advanced_interaction.png")


async def error_handling_example():
    """错误处理示例"""
    print("=== 错误处理示例 ===")
    
    config = BrowserConfig(headless=False)
    
    try:
        async with BrowserAutomation(config) as browser:
            # 尝试访问不存在的页面
            await browser.navigate_to("https://nonexistent-website-12345.com")
            
            # 尝试查找不存在的元素
            element = await browser.find_element(selector="#nonexistent")
            if element is None:
                print("元素未找到，这是预期的结果")
            
            # 尝试输入到不存在的元素
            success = await browser.type_text(
                selector="#nonexistent",
                value="测试"
            )
            print(f"输入操作: {'成功' if success else '失败'}")
            
    except Exception as e:
        print(f"捕获到异常: {e}")


async def performance_monitoring_example():
    """性能监控示例"""
    print("=== 性能监控示例 ===")
    
    config = BrowserConfig(headless=False)
    
    async with BrowserAutomation(config) as browser:
        # 访问网站并监控性能
        await browser.navigate_to("https://www.github.com")
        
        # 获取详细的页面信息
        page_info = await browser.get_page_info()
        
        if page_info:
            basic = page_info.get("basic", {})
            print(f"页面加载时间: {basic.get('load_time', 0)}ms")
            print(f"DOM就绪时间: {basic.get('dom_ready_time', 0)}ms")
            print(f"页面域: {basic.get('domain', 'Unknown')}")
            
        # 获取网络请求
        requests = await browser.page_navigator.get_network_requests()
        print(f"网络请求数量: {len(requests)}")
        
        # 获取网络响应
        responses = await browser.page_navigator.get_network_responses()
        failed_responses = [r for r in responses if r.get("status", 0) >= 400]
        print(f"失败响应数量: {len(failed_responses)}")
        
        # 截图保存
        await browser.take_screenshot("./examples/performance_monitoring.png")


async def batch_screenshot_example():
    """批量截图示例"""
    print("=== 批量截图示例 ===")
    
    config = BrowserConfig(headless=False)
    
    websites = [
        "https://www.baidu.com",
        "https://www.github.com", 
        "https://www.stackoverflow.com"
    ]
    
    async with BrowserAutomation(config) as browser:
        for i, url in enumerate(websites, 1):
            try:
                print(f"正在访问第 {i} 个网站: {url}")
                
                # 导航到网站
                await browser.navigate_to(url)
                
                # 等待页面加载
                await browser.page_navigator.wait_for_load_state("networkidle")
                
                # 截取截图
                screenshot_path = await browser.take_screenshot(
                    path=f"./examples/website_{i}.png",
                    full_page=True
                )
                print(f"截图已保存: {screenshot_path}")
                
                # 获取页面信息
                page_info = await browser.get_page_info()
                title = page_info.get("title", "Unknown")
                print(f"页面标题: {title}")
                
                # 等待一下再访问下一个网站
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"处理网站 {url} 时出错: {e}")
                continue


async def main():
    """主函数"""
    print("AgentBus 浏览器自动化演示")
    print("=" * 50)
    
    try:
        # 运行各种示例
        await basic_browser_example()
        print()
        
        await form_automation_example()
        print()
        
        await advanced_interaction_example()
        print()
        
        await error_handling_example()
        print()
        
        await performance_monitoring_example()
        print()
        
        await batch_screenshot_example()
        print()
        
        print("所有示例运行完成！")
        
    except Exception as e:
        print(f"运行示例时出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())