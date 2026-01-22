"""
多模型管理器
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from config.settings import get_settings, get_active_model_pointer


logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """模型信息"""
    name: str
    provider: str
    model: str
    context_window: int
    max_output_tokens: int


class ModelManager:
    """
    多模型管理器
    管理多个 AI 模型的配置和切换
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._model_profiles: Dict[str, ModelInfo] = {}
        self._current_model: Optional[str] = None
        self._model_locks: Dict[str, asyncio.Lock] = {}
    
    async def initialize(self):
        """初始化模型管理器"""
        # 加载所有配置的模型
        for name, profile in self.settings.model_profiles.items():
            if profile.enabled:
                self._model_profiles[name] = ModelInfo(
                    name=name,
                    provider=profile.provider,
                    model=profile.model,
                    context_window=profile.context_window,
                    max_output_tokens=profile.max_output_tokens
                )
                
                self._model_locks[name] = asyncio.Lock()
        
        # 设置默认模型
        default_model = get_active_model_pointer("main")
        if default_model in self._model_profiles:
            self._current_model = default_model
        
        logger.info(
            f"ModelManager initialized with {len(self._model_profiles)} models"
        )
    
    def get_model(self, model_name: Optional[str] = None) -> Optional[ModelInfo]:
        """获取模型信息"""
        if model_name is None:
            model_name = self._current_model
        
        return self._model_profiles.get(model_name)
    
    def get_current_model(self) -> Optional[str]:
        """获取当前使用的模型"""
        return self._current_model
    
    async def switch_model(self, model_name: str) -> bool:
        """切换当前模型"""
        if model_name not in self._model_profiles:
            logger.warning(f"Model not found: {model_name}")
            return False
        
        old_model = self._current_model
        self._current_model = model_name
        
        logger.info(f"Switched model: {old_model} -> {model_name}")
        return True
    
    def get_model_for_task(self, task_type: str) -> str:
        """
        根据任务类型获取最适合的模型
        
        Args:
            task_type: 任务类型 (main, task, reasoning, quick)
        
        Returns:
            str: 模型名称
        """
        pointer = get_active_model_pointer(task_type)
        
        if pointer in self._model_profiles:
            return pointer
        
        # 回退到主模型
        return self._current_model or self.settings.llm.default_model
    
    def list_models(self) -> list[ModelInfo]:
        """列出所有可用模型"""
        return list(self._model_profiles.values())
    
    def is_available(self, model_name: str) -> bool:
        """检查模型是否可用"""
        return model_name in self._model_profiles
    
    async def get_lock(self, model_name: str) -> asyncio.Lock:
        """获取模型锁（用于并发控制）"""
        return self._model_locks.get(model_name, asyncio.Lock())
    
    def get_provider(self, model_name: str) -> Optional[str]:
        """获取模型提供商"""
        model = self.get_model(model_name)
        return model.provider if model else None
    
    def get_context_window(self, model_name: str) -> int:
        """获取模型上下文窗口大小"""
        model = self.get_model(model_name)
        return model.context_window if model else 128000
