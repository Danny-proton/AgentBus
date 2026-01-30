"""
AgentBus Screenshot Manager

基于Moltbot实现的截图管理器，提供页面截图功能。
"""

import os
import logging
from typing import Optional, Union, Dict, Any
from pathlib import Path
from playwright.async_api import Page, ElementHandle
from datetime import datetime

logger = logging.getLogger(__name__)


class ScreenshotManager:
    """截图管理器"""
    
    def __init__(self, page: Page):
        """
        初始化截图管理器
        
        Args:
            page: Playwright页面实例
        """
        self.page = page
        self.default_path = "./screenshots"
        self.ensure_default_directory()
        
    def ensure_default_directory(self):
        """确保默认截图目录存在"""
        Path(self.default_path).mkdir(parents=True, exist_ok=True)
        
    async def take_screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False,
        type: str = "png",
        quality: Optional[int] = None,
        element: Optional[Union[str, ElementHandle]] = None,
        clip: Optional[Dict[str, float]] = None,
        omit_background: bool = False,
        timeout: int = 30000
    ) -> str:
        """
        截取页面截图
        
        Args:
            path: 保存路径，如果为None则自动生成
            full_page: 是否截取完整页面
            type: 截图类型 (png, jpeg, webp)
            quality: 图片质量 (仅对jpeg/webp有效)
            element: 元素选择器或ElementHandle
            clip: 裁剪区域
            omit_background: 隐藏页面背景
            timeout: 超时时间
            
        Returns:
            str: 截图文件路径
        """
        try:
            # 生成文件路径
            if path is None:
                path = self.generate_screenshot_path(type)
                
            # 确保目录存在
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            
            # 准备截图参数
            screenshot_options = {
                'path': path,
                'type': type,
                'timeout': timeout,
                'omit_background': omit_background
            }
            
            if full_page:
                screenshot_options['full_page'] = True
                
            if quality is not None and type in ['jpeg', 'webp']:
                screenshot_options['quality'] = quality
                
            if element is not None:
                if isinstance(element, str):
                    # 如果是选择器，先查找元素
                    element_handle = await self.page.wait_for_selector(element)
                    if not element_handle:
                        raise Exception(f"未找到元素: {element}")
                    screenshot_options['element'] = element_handle
                else:
                    # 如果已经是ElementHandle
                    screenshot_options['element'] = element
                    
            if clip:
                screenshot_options['clip'] = clip
                
            # 执行截图
            await self.page.screenshot(**screenshot_options)
            
            logger.info(f"截图已保存到: {path}")
            return path
            
        except Exception as e:
            logger.error(f"截图失败: {e}")
            raise
            
    async def take_element_screenshot(
        self,
        selector: str,
        path: Optional[str] = None,
        type: str = "png",
        quality: Optional[int] = None,
        timeout: int = 10000
    ) -> str:
        """
        截取指定元素的截图
        
        Args:
            selector: 元素选择器
            path: 保存路径
            type: 截图类型
            quality: 图片质量
            timeout: 超时时间
            
        Returns:
            str: 截图文件路径
        """
        return await self.take_screenshot(
            path=path,
            type=type,
            quality=quality,
            element=selector,
            timeout=timeout
        )
        
    async def take_viewport_screenshot(
        self,
        path: Optional[str] = None,
        type: str = "png",
        quality: Optional[int] = None,
        omit_background: bool = False
    ) -> str:
        """
        截取视口截图
        
        Args:
            path: 保存路径
            type: 截图类型
            quality: 图片质量
            omit_background: 隐藏页面背景
            
        Returns:
            str: 截图文件路径
        """
        return await self.take_screenshot(
            path=path,
            full_page=False,
            type=type,
            quality=quality,
            omit_background=omit_background
        )
        
    async def take_full_page_screenshot(
        self,
        path: Optional[str] = None,
        type: str = "png",
        quality: Optional[int] = None
    ) -> str:
        """
        截取完整页面截图
        
        Args:
            path: 保存路径
            type: 截图类型
            quality: 图片质量
            
        Returns:
            str: 截图文件路径
        """
        return await self.take_screenshot(
            path=path,
            full_page=True,
            type=type,
            quality=quality
        )
        
    async def take_clip_screenshot(
        self,
        clip: Dict[str, float],
        path: Optional[str] = None,
        type: str = "png",
        quality: Optional[int] = None
    ) -> str:
        """
        截取指定区域的截图
        
        Args:
            clip: 裁剪区域 {'x': 0, 'y': 0, 'width': 100, 'height': 100}
            path: 保存路径
            type: 截图类型
            quality: 图片质量
            
        Returns:
            str: 截图文件路径
        """
        return await self.take_screenshot(
            path=path,
            type=type,
            quality=quality,
            clip=clip
        )
        
    def generate_screenshot_path(self, type: str = "png") -> str:
        """
        生成截图文件路径
        
        Args:
            type: 文件类型
            
        Returns:
            str: 文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 精确到毫秒
        filename = f"screenshot_{timestamp}.{type}"
        return os.path.join(self.default_path, filename)
        
    async def get_page_screenshot_info(self) -> Dict[str, Any]:
        """
        获取当前页面截图相关信息
        
        Returns:
            Dict: 截图信息
        """
        viewport_size = self.page.viewport_size
        page_size = await self.page.evaluate("""
            () => {
                const body = document.body;
                const html = document.documentElement;
                return {
                    body: {
                        width: body.scrollWidth,
                        height: body.scrollHeight
                    },
                    html: {
                        width: html.scrollWidth,
                        height: html.scrollHeight
                    }
                };
            }
        """)
        
        return {
            "viewport": viewport_size,
            "page_size": page_size,
            "url": self.page.url,
            "title": await self.page.title()
        }
        
    def set_default_path(self, path: str):
        """
        设置默认保存路径
        
        Args:
            path: 目录路径
        """
        self.default_path = path
        self.ensure_default_directory()
        
    async def compare_screenshots(
        self,
        screenshot1_path: str,
        screenshot2_path: str,
        threshold: float = 0.1
    ) -> Dict[str, Any]:
        """
        比较两个截图的相似度
        
        Args:
            screenshot1_path: 第一张截图路径
            screenshot2_path: 第二张截图路径
            threshold: 差异阈值
            
        Returns:
            Dict: 比较结果
        """
        try:
            # 这里可以实现图像比较逻辑
            # 使用PIL或opencv进行图像比较
            result = {
                "similar": False,
                "difference_percentage": 0.0,
                "message": "图像比较功能需要额外的依赖库"
            }
            return result
            
        except Exception as e:
            logger.error(f"截图比较失败: {e}")
            raise
            
    async def capture_console_screenshot(
        self,
        path: Optional[str] = None,
        message: Optional[str] = None
    ) -> str:
        """
        截取控制台错误时的截图
        
        Args:
            path: 保存路径
            message: 错误消息
            
        Returns:
            str: 截图文件路径
        """
        if message:
            logger.warning(f"控制台错误: {message}")
            
        return await self.take_screenshot(
            path=path,
            full_page=True,
            type="png"
        )