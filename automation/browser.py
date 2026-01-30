"""
AgentBus Browser Automation Core

基于Moltbot实现的浏览器自动化核心模块，提供浏览器启动、停止、状态查询等基础功能。
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from playwright.async_api import Browser, BrowserContext, Page, Playwright
from .playwright_manager import PlaywrightManager
from .page_navigator import PageNavigator
from .element_finder import ElementFinder
from .form_handler import FormHandler
from .screenshot import ScreenshotManager

logger = logging.getLogger(__name__)


@dataclass
class BrowserStatus:
    """浏览器状态信息"""
    running: bool
    browser: Optional[Browser] = None
    context: Optional[BrowserContext] = None
    pages: List[Page] = None
    pid: Optional[int] = None
    version: Optional[str] = None
    executable_path: Optional[str] = None


@dataclass
class BrowserConfig:
    """浏览器配置"""
    headless: bool = False
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: Optional[str] = None
    disable_images: bool = False
    disable_javascript: bool = False
    disable_css: bool = False
    proxy: Optional[str] = None
    timeout: int = 30000
    slow_mo: int = 0
    ignore_https_errors: bool = True
    java_script_enabled: bool = True
    bypass_csp: bool = False


@dataclass
class TabInfo:
    """标签页信息"""
    target_id: str
    title: str
    url: str
    ws_url: Optional[str] = None
    type: str = "page"


class BrowserAutomation:
    """浏览器自动化主类"""
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        初始化浏览器自动化
        
        Args:
            config: 浏览器配置
        """
        self.config = config or BrowserConfig()
        self.playwright_manager = PlaywrightManager()
        self.page_navigator = None
        self.element_finder = None
        self.form_handler = None
        self.screenshot_manager = None
        
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._status = BrowserStatus(running=False)
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()
        
    async def start(self) -> BrowserStatus:
        """
        启动浏览器
        
        Returns:
            BrowserStatus: 浏览器状态信息
        """
        try:
            logger.info("启动浏览器...")
            
            # 初始化Playwright
            playwright = await self.playwright_manager.start()
            
            # 启动浏览器
            browser_kwargs = {
                'headless': self.config.headless,
                'timeout': self.config.timeout,
                'slow_mo': self.config.slow_mo,
                'ignore_https_errors': self.config.ignore_https_errors
            }
            
            # 设置可执行路径（如果指定）
            # 注意：这里需要根据实际情况设置浏览器路径
            browser_kwargs['executable_path'] = None  # playwright会自动选择合适的浏览器
            
            # 设置代理
            if self.config.proxy:
                browser_kwargs['proxy'] = {'server': self.config.proxy}
                
            self._browser = await playwright.chromium.launch(**browser_kwargs)
            
            # 创建浏览器上下文
            context_kwargs = {
                'viewport': {
                    'width': self.config.viewport_width,
                    'height': self.config.viewport_height
                },
                'java_script_enabled': self.config.java_script_enabled,
                'bypass_csp': self.config.bypass_csp
            }
            
            if self.config.user_agent:
                context_kwargs['user_agent'] = self.config.user_agent
                
            self._context = await self._browser.new_context(**context_kwargs)
            
            # 初始化页面导航器等组件
            page = await self._context.new_page()
            self.page_navigator = PageNavigator(page)
            self.element_finder = ElementFinder(page)
            self.form_handler = FormHandler(page)
            self.screenshot_manager = ScreenshotManager(page)
            
            # 更新状态
            self._status = BrowserStatus(
                running=True,
                browser=self._browser,
                context=self._context,
                pages=[page],
                pid=self._browser.process.pid if self._browser.process else None,
                version=playwright.chromium.name
            )
            
            logger.info(f"浏览器启动成功，版本: {playwright.chromium.name}")
            return self._status
            
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            raise
            
    async def stop(self) -> None:
        """停止浏览器"""
        try:
            logger.info("停止浏览器...")
            
            # 停止浏览器
            if self._browser:
                await self._browser.close()
                
            # 停止Playwright
            await self.playwright_manager.stop()
            
            # 重置状态
            self._status = BrowserStatus(running=False)
            self._browser = None
            self._context = None
            self.page_navigator = None
            self.element_finder = None
            self.form_handler = None
            self.screenshot_manager = None
            
            logger.info("浏览器已停止")
            
        except Exception as e:
            logger.error(f"停止浏览器失败: {e}")
            
    async def get_status(self) -> BrowserStatus:
        """
        获取浏览器状态
        
        Returns:
            BrowserStatus: 浏览器状态信息
        """
        if self._browser and self._context:
            self._status.running = True
            self._status.browser = self._browser
            self._status.context = self._context
            self._status.pages = self._context.pages
            
        return self._status
        
    async def new_tab(self, url: Optional[str] = None) -> TabInfo:
        """
        创建新标签页
        
        Args:
            url: 初始URL，如果为None则创建空白页
            
        Returns:
            TabInfo: 标签页信息
        """
        if not self._context:
            raise RuntimeError("浏览器未启动")
            
        page = await self._context.new_page()
        
        if url:
            await page.goto(url)
            
        target_id = f"tab_{len(self._context.pages)}"
        
        return TabInfo(
            target_id=target_id,
            title=await page.title(),
            url=page.url,
            type="page"
        )
        
    async def close_tab(self, target_id: str) -> bool:
        """
        关闭指定标签页
        
        Args:
            target_id: 标签页ID
            
        Returns:
            bool: 是否成功关闭
        """
        if not self._context:
            return False
            
        # 这里简化处理，实际需要维护target_id到page的映射
        pages = self._context.pages
        if pages:
            await pages[-1].close()
            return True
        return False
        
    async def get_tabs(self) -> List[TabInfo]:
        """
        获取所有标签页信息
        
        Returns:
            List[TabInfo]: 标签页信息列表
        """
        if not self._context:
            return []
            
        tabs = []
        for i, page in enumerate(self._context.pages):
            target_id = f"tab_{i}"
            tabs.append(TabInfo(
                target_id=target_id,
                title=await page.title(),
                url=page.url,
                type="page"
            ))
            
        return tabs
        
    async def focus_tab(self, target_id: str) -> bool:
        """
        聚焦指定标签页
        
        Args:
            target_id: 标签页ID
            
        Returns:
            bool: 是否成功聚焦
        """
        if not self._context:
            return False
            
        # 简化处理，实际需要维护target_id到page的映射
        pages = self._context.pages
        if pages:
            # 这里简化处理，默认聚焦最后一个标签页
            await pages[-1].bring_to_front()
            return True
        return False
        
    async def take_screenshot(self, **kwargs) -> str:
        """
        截取当前页面截图
        
        Args:
            **kwargs: 截图参数
            
        Returns:
            str: 截图文件路径
        """
        if not self.screenshot_manager:
            raise RuntimeError("页面管理器未初始化")
            
        return await self.screenshot_manager.take_screenshot(**kwargs)
        
    async def navigate_to(self, url: str, **kwargs) -> bool:
        """
        导航到指定URL
        
        Args:
            url: 目标URL
            **kwargs: 导航参数
            
        Returns:
            bool: 是否成功导航
        """
        if not self.page_navigator:
            raise RuntimeError("页面导航器未初始化")
            
        return await self.page_navigator.navigate(url, **kwargs)
        
    async def find_element(self, **kwargs):
        """
        查找页面元素
        
        Args:
            **kwargs: 查找参数
            
        Returns:
            查找到的元素
        """
        if not self.element_finder:
            raise RuntimeError("元素查找器未初始化")
            
        return await self.element_finder.find_element(**kwargs)
        
    async def find_elements(self, **kwargs):
        """
        查找页面元素（多个）
        
        Args:
            **kwargs: 查找参数
            
        Returns:
            查找到的元素列表
        """
        if not self.element_finder:
            raise RuntimeError("元素查找器未初始化")
            
        return await self.element_finder.find_elements(**kwargs)
        
    async def fill_form(self, **kwargs):
        """
        填写表单
        
        Args:
            **kwargs: 表单数据
        """
        if not self.form_handler:
            raise RuntimeError("表单处理器未初始化")
            
        return await self.form_handler.fill_form(**kwargs)
        
    async def click_element(self, **kwargs):
        """
        点击元素
        
        Args:
            **kwargs: 点击参数
        """
        if not self.element_finder:
            raise RuntimeError("元素查找器未初始化")
            
        return await self.element_finder.click_element(**kwargs)
        
    async def type_text(self, **kwargs):
        """
        输入文本
        
        Args:
            **kwargs: 输入参数
        """
        if not self.element_finder:
            raise RuntimeError("元素查找器未初始化")
            
        return await self.element_finder.type_text(**kwargs)
        
    async def get_page_console(self) -> List[Dict[str, Any]]:
        """
        获取页面控制台日志
        
        Returns:
            List[Dict]: 控制台日志列表
        """
        if not self.page_navigator:
            return []
            
        return await self.page_navigator.get_console_messages()
        
    async def execute_script(self, script: str) -> Any:
        """
        执行JavaScript脚本
        
        Args:
            script: JavaScript代码
            
        Returns:
            执行结果
        """
        if not self.page_navigator:
            raise RuntimeError("页面导航器未初始化")
            
        return await self.page_navigator.execute_script(script)
        
    async def get_page_info(self) -> Dict[str, Any]:
        """
        获取当前页面信息
        
        Returns:
            Dict: 页面信息
        """
        if not self.page_navigator:
            return {}
            
        return await self.page_navigator.get_page_info()
        
    def get_config(self) -> BrowserConfig:
        """获取浏览器配置"""
        return self.config
        
    def update_config(self, config: BrowserConfig):
        """更新浏览器配置"""
        self.config = config