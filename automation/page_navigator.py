"""
AgentBus Page Navigator

基于Moltbot实现的页面导航器，提供页面导航、加载状态监控等功能。
"""

import logging
from typing import Dict, List, Optional, Any, Union
from playwright.async_api import Page, ConsoleMessage, Response
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class PageNavigator:
    """页面导航器"""
    
    def __init__(self, page: Page):
        """
        初始化页面导航器
        
        Args:
            page: Playwright页面实例
        """
        self.page = page
        self.console_messages: List[Dict[str, Any]] = []
        self.network_requests: List[Dict[str, Any]] = []
        self.network_responses: List[Dict[str, Any]] = []
        self.setup_event_listeners()
        
    def setup_event_listeners(self):
        """设置事件监听器"""
        # 监听控制台消息
        self.page.on("console", self._handle_console_message)
        
        # 监听网络请求
        self.page.on("request", self._handle_request)
        
        # 监听网络响应
        self.page.on("response", self._handle_response)
        
    def _handle_console_message(self, msg: ConsoleMessage):
        """处理控制台消息"""
        message_data = {
            "type": msg.type,
            "text": msg.text,
            "location": msg.location,
            "timestamp": msg.timestamp
        }
        self.console_messages.append(message_data)
        
        # 记录不同类型的消息
        if msg.type == "error":
            logger.error(f"页面错误: {msg.text}")
        elif msg.type == "warning":
            logger.warning(f"页面警告: {msg.text}")
        elif msg.type == "info":
            logger.info(f"页面信息: {msg.text}")
            
    def _handle_request(self, request):
        """处理网络请求"""
        request_data = {
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers),
            "timestamp": request.timing,
            "resource_type": request.resource_type
        }
        self.network_requests.append(request_data)
        
    def _handle_response(self, response: Response):
        """处理网络响应"""
        response_data = {
            "url": response.url,
            "status": response.status,
            "status_text": response.status_text,
            "headers": dict(response.headers),
            "content_type": response.headers.get("content-type"),
            "timestamp": response.timing
        }
        self.network_responses.append(response_data)
        
    async def navigate(
        self,
        url: str,
        wait_until: str = "networkidle",
        timeout: int = 30000,
        referer: Optional[str] = None
    ) -> bool:
        """
        导航到指定URL
        
        Args:
            url: 目标URL
            wait_until: 等待状态 (load, domcontentloaded, networkidle)
            timeout: 超时时间
            referer: 引用页面
            
        Returns:
            bool: 是否成功导航
        """
        try:
            logger.info(f"导航到: {url}")
            
            # 构造完整URL
            if not url.startswith(('http://', 'https://')):
                current_url = self.page.url
                url = urljoin(current_url, url)
                
            # 导航选项
            navigation_options = {
                'wait_until': wait_until,
                'timeout': timeout
            }
            
            if referer:
                navigation_options['referer'] = referer
                
            # 执行导航
            response = await self.page.goto(url, **navigation_options)
            
            if response:
                logger.info(f"导航成功: {response.status} - {url}")
                return True
            else:
                logger.warning(f"导航失败，未获取到响应")
                return False
                
        except Exception as e:
            logger.error(f"导航失败: {e}")
            return False
            
    async def navigate_back(self) -> bool:
        """
        返回上一页
        
        Returns:
            bool: 是否成功
        """
        try:
            await self.page.go_back()
            return True
        except Exception as e:
            logger.error(f"返回上一页失败: {e}")
            return False
            
    async def navigate_forward(self) -> bool:
        """
        前进到下一页
        
        Returns:
            bool: 是否成功
        """
        try:
            await self.page.go_forward()
            return True
        except Exception as e:
            logger.error(f"前进到下一页失败: {e}")
            return False
            
    async def reload_page(self, hard: bool = False) -> bool:
        """
        重新加载页面
        
        Args:
            hard: 是否强制重新加载
            
        Returns:
            bool: 是否成功
        """
        try:
            if hard:
                # 强制重新加载
                await self.page.evaluate("location.reload(true)")
            else:
                # 正常重新加载
                await self.page.reload()
            return True
        except Exception as e:
            logger.error(f"重新加载页面失败: {e}")
            return False
            
    async def wait_for_load_state(
        self,
        state: str = "networkidle",
        timeout: int = 30000
    ) -> bool:
        """
        等待页面加载状态
        
        Args:
            state: 加载状态 (load, domcontentloaded, networkidle)
            timeout: 超时时间
            
        Returns:
            bool: 是否成功
        """
        try:
            await self.page.wait_for_load_state(state, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"等待加载状态失败: {e}")
            return False
            
    async def wait_for_url(
        self,
        url_pattern: Union[str, 're.Pattern'],
        timeout: int = 30000
    ) -> bool:
        """
        等待URL变化
        
        Args:
            url_pattern: URL模式或正则表达式
            timeout: 超时时间
            
        Returns:
            bool: 是否成功
        """
        try:
            await self.page.wait_for_url(url_pattern, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"等待URL变化失败: {e}")
            return False
            
    async def wait_for_navigation(
        self,
        timeout: int = 30000,
        url_pattern: Optional[Union[str, 're.Pattern']] = None
    ) -> bool:
        """
        等待导航完成
        
        Args:
            timeout: 超时时间
            url_pattern: URL模式
            
        Returns:
            bool: 是否成功
        """
        try:
            if url_pattern:
                await self.page.wait_for_url(url_pattern, timeout=timeout)
            else:
                await self.page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"等待导航失败: {e}")
            return False
            
    async def get_current_url(self) -> str:
        """
        获取当前页面URL
        
        Returns:
            str: 当前URL
        """
        return self.page.url
        
    async def get_title(self) -> str:
        """
        获取页面标题
        
        Returns:
            str: 页面标题
        """
        return await self.page.title()
        
    async def get_page_info(self) -> Dict[str, Any]:
        """
        获取页面信息
        
        Returns:
            Dict: 页面信息
        """
        try:
            # 获取基本页面信息
            basic_info = await self.page.evaluate("""
                () => {
                    const timing = performance.timing;
                    return {
                        title: document.title,
                        url: window.location.href,
                        domain: window.location.hostname,
                        path: window.location.pathname,
                        protocol: window.location.protocol,
                        load_time: timing.loadEventEnd - timing.navigationStart,
                        dom_ready_time: timing.domContentLoadedEventEnd - timing.navigationStart
                    };
                }
            """)
            
            # 获取页面尺寸
            viewport = self.page.viewport_size
            
            # 获取加载状态
            load_state = await self.page.evaluate("""
                () => {
                    return {
                        ready_state: document.readyState,
                        complete: document.readyState === 'complete'
                    };
                }
            """)
            
            return {
                "basic": basic_info,
                "viewport": viewport,
                "load_state": load_state,
                "url": await self.get_current_url(),
                "title": await self.get_title()
            }
            
        except Exception as e:
            logger.error(f"获取页面信息失败: {e}")
            return {}
            
    async def get_console_messages(
        self,
        message_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取控制台消息
        
        Args:
            message_type: 消息类型过滤
            
        Returns:
            List[Dict]: 控制台消息列表
        """
        if message_type:
            return [msg for msg in self.console_messages if msg["type"] == message_type]
        return self.console_messages.copy()
        
    def clear_console_messages(self):
        """清除控制台消息"""
        self.console_messages.clear()
        
    async def get_network_requests(
        self,
        url_pattern: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取网络请求
        
        Args:
            url_pattern: URL模式过滤
            
        Returns:
            List[Dict]: 网络请求列表
        """
        if url_pattern:
            import re
            pattern = re.compile(url_pattern)
            return [req for req in self.network_requests if pattern.search(req["url"])]
        return self.network_requests.copy()
        
    async def get_network_responses(
        self,
        status_code: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取网络响应
        
        Args:
            status_code: 状态码过滤
            
        Returns:
            List[Dict]: 网络响应列表
        """
        if status_code:
            return [resp for resp in self.network_responses if resp["status"] == status_code]
        return self.network_responses.copy()
        
    def clear_network_logs(self):
        """清除网络日志"""
        self.network_requests.clear()
        self.network_responses.clear()
        
    async def execute_script(self, script: str) -> Any:
        """
        执行JavaScript脚本
        
        Args:
            script: JavaScript代码
            
        Returns:
            Any: 执行结果
        """
        try:
            return await self.page.evaluate(script)
        except Exception as e:
            logger.error(f"执行脚本失败: {e}")
            raise
            
    async def scroll_to_element(self, selector: str) -> bool:
        """
        滚动到指定元素
        
        Args:
            selector: 元素选择器
            
        Returns:
            bool: 是否成功
        """
        try:
            element = await self.page.wait_for_selector(selector)
            if element:
                await element.scroll_into_view_if_needed()
                return True
            return False
        except Exception as e:
            logger.error(f"滚动到元素失败: {e}")
            return False
            
    async def scroll_page(
        self,
        x: int = 0,
        y: int = 0,
        behavior: str = "smooth"
    ) -> bool:
        """
        滚动页面
        
        Args:
            x: X轴滚动量
            y: Y轴滚动量
            behavior: 滚动行为
            
        Returns:
            bool: 是否成功
        """
        try:
            await self.page.evaluate(
                f"window.scrollBy({{left: {x}, top: {y}, behavior: '{behavior}'}})"
            )
            return True
        except Exception as e:
            logger.error(f"滚动页面失败: {e}")
            return False
            
    async def scroll_to_top(self) -> bool:
        """滚动到页面顶部"""
        return await self.scroll_page(y=0)
        
    async def scroll_to_bottom(self) -> bool:
        """滚动到页面底部"""
        try:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            return True
        except Exception as e:
            logger.error(f"滚动到底部失败: {e}")
            return False
            
    async def get_page_scroll_position(self) -> Dict[str, int]:
        """
        获取页面滚动位置
        
        Returns:
            Dict: 滚动位置信息
        """
        try:
            position = await self.page.evaluate("""
                () => {
                    return {
                        x: window.pageXOffset,
                        y: window.pageYOffset,
                        max_x: document.documentElement.scrollWidth,
                        max_y: document.documentElement.scrollHeight,
                        width: window.innerWidth,
                        height: window.innerHeight
                    };
                }
            """)
            return position
        except Exception as e:
            logger.error(f"获取滚动位置失败: {e}")
            return {}
            
    async def set_viewport_size(self, width: int, height: int) -> bool:
        """
        设置视口大小
        
        Args:
            width: 宽度
            height: 高度
            
        Returns:
            bool: 是否成功
        """
        try:
            await self.page.set_viewport_size({"width": width, "height": height})
            return True
        except Exception as e:
            logger.error(f"设置视口大小失败: {e}")
            return False