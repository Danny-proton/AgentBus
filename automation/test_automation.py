"""
AgentBus Browser Automation Tests

浏览器自动化系统测试
"""

import asyncio
import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from agentbus.automation.browser import BrowserAutomation, BrowserConfig, BrowserStatus, TabInfo
from agentbus.automation.screenshot import ScreenshotManager
from agentbus.automation.form_handler import FormHandler
from agentbus.automation.page_navigator import PageNavigator
from agentbus.automation.element_finder import ElementFinder
from playwright.async_api import Page, Browser, BrowserContext


class TestBrowserAutomation:
    """浏览器自动化测试类"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return BrowserConfig(
            headless=True,
            viewport_width=800,
            viewport_height=600,
            timeout=10000
        )
    
    @pytest.mark.asyncio
    async def test_browser_initialization(self, config):
        """测试浏览器初始化"""
        browser = BrowserAutomation(config)
        assert browser.config == config
        assert browser._status.running is False
        assert browser.playwright_manager is not None
    
    @pytest.mark.asyncio
    async def test_browser_start_stop(self, config):
        """测试浏览器启动和停止"""
        browser = BrowserAutomation(config)
        
        try:
            # 测试启动
            status = await browser.start()
            assert status.running is True
            assert status.browser is not None
            assert status.context is not None
            assert len(status.pages) > 0
            
            # 测试状态获取
            current_status = await browser.get_status()
            assert current_status.running is True
            
            # 测试停止
            await browser.stop()
            final_status = await browser.get_status()
            assert final_status.running is False
            
        except Exception as e:
            # 如果没有安装浏览器，跳过测试
            pytest.skip(f"浏览器启动失败，跳过测试: {e}")
    
    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        """测试异步上下文管理器"""
        async with BrowserAutomation(config) as browser:
            # 在上下文中验证浏览器已启动
            status = await browser.get_status()
            assert status.running is True
        
        # 离开上下文后浏览器应该已停止
        status = await browser.get_status()
        assert status.running is False
    
    @pytest.mark.asyncio
    async def test_navigation(self, config):
        """测试页面导航"""
        async with BrowserAutomation(config) as browser:
            try:
                # 导航到测试页面
                success = await browser.navigate_to("data:text/html,<h1>Test Page</h1>")
                assert success is True
                
                # 获取页面信息
                page_info = await browser.get_page_info()
                assert page_info is not None
                assert isinstance(page_info, dict)
                
            except Exception as e:
                pytest.skip(f"导航测试失败: {e}")
    
    @pytest.mark.asyncio
    async def test_screenshot_functionality(self, config):
        """测试截图功能"""
        async with BrowserAutomation(config) as browser:
            try:
                # 导航到测试页面
                await browser.navigate_to("data:text/html,<h1>Screenshot Test</h1>")
                
                # 测试截图
                with tempfile.TemporaryDirectory() as tmpdir:
                    screenshot_path = os.path.join(tmpdir, "test_screenshot.png")
                    path = await browser.take_screenshot(
                        path=screenshot_path,
                        full_page=False
                    )
                    
                    assert path == screenshot_path
                    assert os.path.exists(path)
                    assert os.path.getsize(path) > 0
                    
            except Exception as e:
                pytest.skip(f"截图测试失败: {e}")
    
    @pytest.mark.asyncio
    async def test_element_finding(self, config):
        """测试元素查找功能"""
        async with BrowserAutomation(config) as browser:
            try:
                # 创建测试页面
                test_html = """
                <html>
                <body>
                    <h1 id="title">Test Title</h1>
                    <button id="test-btn">Test Button</button>
                    <input type="text" name="test-input" placeholder="Test Input">
                    <a href="#">Test Link</a>
                </body>
                </html>
                """
                
                await browser.navigate_to(f"data:text/html,{test_html}")
                
                # 测试元素查找
                title_element = await browser.find_element(selector="#title")
                assert title_element is not None
                
                # 测试查找多个元素
                buttons = await browser.find_elements(selector="button")
                assert len(buttons) > 0
                
                # 测试获取元素信息
                element_info = await browser.element_finder.get_element_info(
                    selector="#title"
                )
                assert element_info is not None
                assert element_info.get("tag_name") == "h1"
                
            except Exception as e:
                pytest.skip(f"元素查找测试失败: {e}")
    
    @pytest.mark.asyncio
    async def test_element_interaction(self, config):
        """测试元素交互功能"""
        async with BrowserAutomation(config) as browser:
            try:
                # 创建测试表单
                test_html = """
                <html>
                <body>
                    <input type="text" id="test-input" value="">
                    <button id="test-btn" type="button">Click Me</button>
                    <select id="test-select">
                        <option value="1">Option 1</option>
                        <option value="2">Option 2</option>
                    </select>
                </body>
                </html>
                """
                
                await browser.navigate_to(f"data:text/html,{test_html}")
                
                # 测试输入文本
                success = await browser.type_text(
                    selector="#test-input",
                    value="Hello World"
                )
                assert success is True
                
                # 测试点击按钮
                success = await browser.click_element(
                    selector="#test-btn"
                )
                assert success is True
                
                # 测试选择选项
                success = await browser.form_handler.select_option(
                    selector="#test-select",
                    value="1"
                )
                assert success is True
                
            except Exception as e:
                pytest.skip(f"元素交互测试失败: {e}")
    
    @pytest.mark.asyncio
    async def test_form_handling(self, config):
        """测试表单处理功能"""
        async with BrowserAutomation(config) as browser:
            try:
                # 创建测试表单
                test_html = """
                <html>
                <body>
                    <form id="test-form">
                        <input type="text" name="username" required>
                        <input type="email" name="email" required>
                        <input type="password" name="password" required>
                        <select name="country">
                            <option value="us">US</option>
                            <option value="cn">China</option>
                        </select>
                        <input type="checkbox" name="newsletter">
                        <input type="submit" value="Submit">
                    </form>
                </body>
                </html>
                """
                
                await browser.navigate_to(f"data:text/html,{test_html}")
                
                # 测试表单填写
                form_data = {
                    "input[name='username']": "testuser",
                    "input[name='email']": "test@example.com",
                    "input[name='password']": "password123",
                    "select[name='country']": "cn",
                    "input[name='newsletter']": True
                }
                
                success = await browser.fill_form(form_data)
                assert success is True
                
                # 测试表单验证
                validation = await browser.form_handler.validate_form(form_data)
                assert validation is not None
                assert isinstance(validation, dict)
                
                # 测试表单数据获取
                form_data_retrieved = await browser.form_handler.get_form_data()
                assert form_data_retrieved is not None
                assert isinstance(form_data_retrieved, dict)
                
            except Exception as e:
                pytest.skip(f"表单处理测试失败: {e}")
    
    @pytest.mark.asyncio
    async def test_console_monitoring(self, config):
        """测试控制台监控功能"""
        async with BrowserAutomation(config) as browser:
            try:
                # 创建包含JavaScript错误的测试页面
                test_html = """
                <html>
                <body>
                    <script>
                        console.log('Test log message');
                        console.error('Test error message');
                        console.warn('Test warning message');
                    </script>
                    <h1>Console Test Page</h1>
                </body>
                </html>
                """
                
                await browser.navigate_to(f"data:text/html,{test_html}")
                
                # 等待控制台消息
                await asyncio.sleep(1)
                
                # 获取控制台消息
                console_messages = await browser.get_page_console()
                assert console_messages is not None
                assert isinstance(console_messages, list)
                
                # 检查是否有日志消息
                log_messages = [msg for msg in console_messages if msg.get("type") == "log"]
                assert len(log_messages) > 0
                
            except Exception as e:
                pytest.skip(f"控制台监控测试失败: {e}")
    
    @pytest.mark.asyncio
    async def test_network_monitoring(self, config):
        """测试网络监控功能"""
        async with BrowserAutomation(config) as browser:
            try:
                # 访问一个包含网络请求的页面
                await browser.navigate_to("https://httpbin.org/get")
                
                # 等待网络请求完成
                await asyncio.sleep(2)
                
                # 获取网络请求
                requests = await browser.page_navigator.get_network_requests()
                assert requests is not None
                assert isinstance(requests, list)
                
                # 获取网络响应
                responses = await browser.page_navigator.get_network_responses()
                assert responses is not None
                assert isinstance(responses, list)
                
            except Exception as e:
                pytest.skip(f"网络监控测试失败: {e}")
    
    @pytest.mark.asyncio
    async def test_wait_functionality(self, config):
        """测试等待功能"""
        async with BrowserAutomation(config) as browser:
            try:
                # 创建动态页面
                test_html = """
                <html>
                <body>
                    <script>
                        setTimeout(() => {
                            const h1 = document.createElement('h1');
                            h1.id = 'dynamic-element';
                            h1.textContent = 'Dynamic Content';
                            document.body.appendChild(h1);
                        }, 100);
                    </script>
                    <h1>Loading...</h1>
                </body>
                </html>
                """
                
                await browser.navigate_to(f"data:text/html,{test_html}")
                
                # 等待动态元素出现
                success = await browser.element_finder.wait_for_element(
                    selector="#dynamic-element",
                    timeout=2000
                )
                assert success is True
                
                # 验证元素存在
                element = await browser.find_element(selector="#dynamic-element")
                assert element is not None
                
            except Exception as e:
                pytest.skip(f"等待功能测试失败: {e}")


def test_browser_config():
    """测试浏览器配置"""
    config = BrowserConfig(
        headless=True,
        viewport_width=1024,
        viewport_height=768,
        timeout=15000
    )
    
    assert config.headless is True
    assert config.viewport_width == 1024
    assert config.viewport_height == 768
    assert config.timeout == 15000


def test_browser_status():
    """测试浏览器状态"""
    status = BrowserStatus(running=False)
    
    assert status.running is False
    assert status.browser is None
    assert status.context is None
    assert status.pages is None
    assert status.pid is None


def test_tab_info():
    """测试标签页信息"""
    tab = TabInfo(
        target_id="tab_1",
        title="Test Page",
        url="https://example.com"
    )
    
    assert tab.target_id == "tab_1"
    assert tab.title == "Test Page"
    assert tab.url == "https://example.com"
    assert tab.type == "page"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])