"""
AgentBus Playwright Manager

基于Moltbot实现的Playwright管理器，负责Playwright的生命周期管理。
"""

import asyncio
import logging
from typing import Optional
from playwright.async_api import Playwright, async_playwright

logger = logging.getLogger(__name__)


class PlaywrightManager:
    """Playwright管理器"""
    
    def __init__(self):
        """初始化Playwright管理器"""
        self._playwright: Optional[Playwright] = None
        self._running = False
        
    async def start(self) -> Playwright:
        """
        启动Playwright
        
        Returns:
            Playwright: Playwright实例
        """
        try:
            if self._running and self._playwright:
                logger.warning("Playwright已经在运行中")
                return self._playwright
                
            logger.info("启动Playwright...")
            self._playwright = await async_playwright().start()
            self._running = True
            
            logger.info("Playwright启动成功")
            return self._playwright
            
        except Exception as e:
            logger.error(f"启动Playwright失败: {e}")
            raise
            
    async def stop(self) -> None:
        """停止Playwright"""
        try:
            if self._playwright and self._running:
                logger.info("停止Playwright...")
                await self._playwright.stop()
                self._running = False
                self._playwright = None
                logger.info("Playwright已停止")
            else:
                logger.warning("Playwright未运行或已经停止")
                
        except Exception as e:
            logger.error(f"停止Playwright失败: {e}")
            
    async def restart(self) -> Playwright:
        """
        重启Playwright
        
        Returns:
            Playwright: Playwright实例
        """
        await self.stop()
        return await self.start()
        
    @property
    def playwright(self) -> Optional[Playwright]:
        """
        获取Playwright实例
        
        Returns:
            Optional[Playwright]: Playwright实例，如果未启动则返回None
        """
        return self._playwright
        
    @property
    def is_running(self) -> bool:
        """
        检查Playwright是否在运行
        
        Returns:
            bool: 是否在运行
        """
        return self._running and self._playwright is not None
        
    def __enter__(self):
        """同步上下文管理器入口"""
        # 同步方法，实际使用中通常使用异步版本
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """同步上下文管理器出口"""
        # 这里需要异步操作，但__exit__是同步的
        # 用户应该使用异步版本或手动调用stop()
        pass