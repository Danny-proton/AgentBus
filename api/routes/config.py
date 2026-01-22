"""
配置管理路由
"""

from fastapi import APIRouter, HTTPException
from typing import Dict

from api.schemas.message import (
    ModelConfig,
    ModelPointerConfig,
    ConfigUpdate,
    EnvironmentInfo
)
from config.settings import (
    get_settings,
    get_model_config,
    get_active_model_pointer
)
from runtime.abstract import EnvironmentFactory


config_router = APIRouter(prefix="/config", tags=["Config"])


@config_router.get("")
async def get_config():
    """获取当前配置"""
    settings = get_settings()
    
    return {
        "model_pointers": {
            "main": settings.model_pointers.main,
            "task": settings.model_pointers.task,
            "reasoning": settings.model_pointers.reasoning,
            "quick": settings.model_pointers.quick
        },
        "available_models": list(settings.model_profiles.keys()),
        "remote_enabled": settings.remote.enabled,
        "safe_mode": settings.security.safe_mode
    }


@config_router.get("/models")
async def list_models():
    """列出所有可用模型"""
    settings = get_settings()
    
    models = []
    for name, profile in settings.model_profiles.items():
        models.append({
            "name": name,
            "provider": profile.provider,
            "model": profile.model,
            "context_window": profile.context_window,
            "enabled": profile.enabled
        })
    
    return {"models": models}


@config_router.get("/models/{model_name}")
async def get_model(model_name: str):
    """获取特定模型配置"""
    profile = get_model_config(model_name)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return {
        "name": profile.name,
        "provider": profile.provider,
        "model": profile.model,
        "context_window": profile.context_window,
        "max_output_tokens": profile.max_output_tokens,
        "cost_per_input": profile.cost_per_input,
        "cost_per_output": profile.cost_per_output,
        "enabled": profile.enabled
    }


@config_router.get("/pointers")
async def get_pointers():
    """获取模型指针配置"""
    settings = get_settings()
    
    return {
        "main": settings.model_pointers.main,
        "task": settings.model_pointers.task,
        "reasoning": settings.model_pointers.reasoning,
        "quick": settings.model_pointers.quick
    }


@config_router.post("/pointers")
async def update_pointers(pointers: ModelPointerConfig):
    """更新模型指针配置"""
    # 这里应该更新配置文件
    # 暂时返回成功响应
    return {
        "status": "success",
        "pointers": pointers.model_dump()
    }


@config_router.get("/environment")
async def get_environment():
    """获取当前环境信息"""
    env = EnvironmentFactory.get_environment()
    info = await env.get_info()
    
    return info


@config_router.get("/safe-mode")
async def get_safe_mode():
    """获取安全模式状态"""
    settings = get_settings()
    
    return {
        "safe_mode": settings.security.safe_mode,
        "require_approval": settings.security.require_approval_for_dangerous
    }


@config_router.post("/safe-mode")
async def set_safe_mode(enabled: bool):
    """设置安全模式"""
    # 这里应该更新配置文件
    return {
        "status": "success",
        "safe_mode": enabled
    }
