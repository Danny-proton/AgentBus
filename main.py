#!/usr/bin/env python3
"""
Moltbot Python Implementation - Main Application
===============================================

跨平台AI助手的Python实现主程序
Main application for cross-platform AI assistant implementation in Python

Author: MiniMax Agent
License: MIT
"""

import asyncio
import sys
import signal
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from py_moltbot.core.config import Settings, settings
from py_moltbot.core.logger import get_logger, setup_logging
from py_moltbot.skills.base import SkillManager, SkillRegistry
from py_moltbot.adapters.base import AdapterRegistry, AdapterConfig, AdapterType

logger = get_logger(__name__)


class MoltBot:
    """
    MoltBot主应用程序
    
    负责协调所有组件的初始化、运行和关闭
    """
    
    def __init__(self, config: Optional[Settings] = None):
        """初始化MoltBot应用"""
        self.config = config or settings
        self.logger = get_logger(self.__class__.__name__)
        
        # 核心组件
        self.skill_manager: Optional[SkillManager] = None
        self.adapters = {}
        
        # 应用状态
        self.running = False
        self._shutdown_event = asyncio.Event()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """处理系统信号"""
        self.logger.info("Received shutdown signal", signal=signum)
        asyncio.create_task(self.shutdown())
    
    async def initialize(self) -> None:
        """初始化应用组件"""
        try:
            self.logger.info("Initializing MoltBot application...")
            
            # 创建数据目录
            await self._setup_directories()
            
            # 初始化技能系统
            await self._initialize_skills()
            
            # 初始化适配器
            await self._initialize_adapters()
            
            # 设置Web服务（如果需要）
            await self._setup_web_services()
            
            self.logger.info("MoltBot initialization completed successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize MoltBot", error=str(e))
            raise
    
    async def _setup_directories(self) -> None:
        """设置必要的目录"""
        storage_paths = self.config.get_storage_paths()
        
        for name, path in storage_paths.items():
            path.mkdir(parents=True, exist_ok=True)
            self.logger.debug("Created directory", name=name, path=str(path))
    
    async def _initialize_skills(self) -> None:
        """初始化技能系统"""
        self.logger.info("Initializing skill system...")
        
        self.skill_manager = SkillManager()
        
        # 技能配置（从配置文件中加载）
        skill_configs = {
            "test_skill": {
                "enabled": True,
                "timeout": 30,
                "max_concurrent": 5
            },
            "weather": {
                "enabled": True,
                "api_key": self.config.ai.openai_api_key,
                "timeout": 15
            },
            "summarize": {
                "enabled": True,
                "ai_model": self.config.ai.default_model,
                "temperature": self.config.ai.temperature
            }
        }
        
        await self.skill_manager.initialize(skill_configs)
        
        # 记录已初始化的技能
        skills = self.skill_manager.list_skills()
        self.logger.info("Skills initialized", count=len(skills), skills=skills)
    
    async def _initialize_adapters(self) -> None:
        """初始化消息适配器"""
        self.logger.info("Initializing message adapters...")
        
        # 从配置中读取启用的适配器
        adapter_configs = [
            ("test", AdapterConfig(
                name="test_adapter",
                adapter_type=AdapterType.WEB,
                enabled=True
            )),
            ("discord", AdapterConfig(
                name="discord_adapter",
                adapter_type=AdapterType.DISCORD,
                enabled=bool(self.config.message_platforms.discord_bot_token),
                credentials={
                    "bot_token": self.config.message_platforms.discord_bot_token or ""
                }
            )),
            ("telegram", AdapterConfig(
                name="telegram_adapter",
                adapter_type=AdapterType.TELEGRAM,
                enabled=bool(self.config.message_platforms.telegram_bot_token),
                credentials={
                    "bot_token": self.config.message_platforms.telegram_bot_token or ""
                }
            ))
        ]
        
        # 初始化启用的适配器
        for adapter_name, config in adapter_configs:
            if config.enabled:
                try:
                    adapter = AdapterRegistry.create_adapter(adapter_name, config)
                    await adapter.start()
                    self.adapters[adapter_name] = adapter
                    self.logger.info("Adapter initialized", adapter=adapter_name)
                except Exception as e:
                    self.logger.error("Failed to initialize adapter", 
                                    adapter=adapter_name, error=str(e))
        
        self.logger.info("Adapters initialization completed", 
                        count=len(self.adapters),
                        adapters=list(self.adapters.keys()))
    
    async def _setup_web_services(self) -> None:
        """设置Web服务（可选）"""
        # 这里可以设置FastAPI Web服务
        # 用于Web界面、Webhook处理等
        self.logger.info("Web services setup completed")
    
    async def run(self) -> None:
        """运行应用程序"""
        if not self.skill_manager:
            raise RuntimeError("Application not initialized. Call initialize() first.")
        
        self.running = True
        self.logger.info("Starting MoltBot application...")
        
        try:
            # 保持应用运行
            await self._shutdown_event.wait()
            
        except Exception as e:
            self.logger.error("Application runtime error", error=str(e))
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """关闭应用程序"""
        if not self.running:
            return
        
        self.logger.info("Shutting down MoltBot application...")
        self.running = False
        
        try:
            # 关闭所有适配器
            for adapter_name, adapter in self.adapters.items():
                try:
                    await adapter.stop()
                    self.logger.info("Adapter stopped", adapter=adapter_name)
                except Exception as e:
                    self.logger.error("Failed to stop adapter", 
                                    adapter=adapter_name, error=str(e))
            
            # 清理技能系统
            if self.skill_manager:
                await self.skill_manager.cleanup()
                self.logger.info("Skill system cleaned up")
            
            self.logger.info("MoltBot shutdown completed")
            
        except Exception as e:
            self.logger.error("Error during shutdown", error=str(e))
        
        finally:
            self._shutdown_event.set()
    
    def get_status(self) -> dict:
        """获取应用状态"""
        return {
            "running": self.running,
            "adapters": {
                name: adapter.get_info() 
                for name, adapter in self.adapters.items()
            },
            "skills": self.skill_manager.list_skills() if self.skill_manager else [],
            "config": {
                "environment": self.config.environment,
                "debug": self.config.debug,
                "version": self.config.app_version
            }
        }


async def main():
    """主函数"""
    try:
        # 初始化日志系统
        setup_logging()
        
        # 创建应用实例
        app = MoltBot()
        
        # 初始化应用
        await app.initialize()
        
        # 显示状态
        status = app.get_status()
        logger.info("Application status", status=status)
        
        # 运行应用
        await app.run()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error("Application failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())