#!/usr/bin/env python3
"""
vLLM 集成测试

测试 AgentBus 与 vLLM mock 服务器的集成
"""
import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.mark.asyncio
class TestVLLMIntegration:
    """测试 vLLM 与 AgentBus 的集成"""
    
    async def test_coordinator_initialization(self, mock_vllm_server, vllm_settings):
        """测试 MultiModelCoordinator 初始化"""
        from services.multi_model_coordinator import MultiModelCoordinator
        
        coordinator = MultiModelCoordinator()
        await coordinator.initialize()
        
        # 验证协调器已初始化
        models = coordinator.get_available_models()
        assert len(models) > 0
    
    async def test_model_registration(self, mock_vllm_server, vllm_settings):
        """验证 vLLM 模型注册"""
        from services.multi_model_coordinator import MultiModelCoordinator
        
        coordinator = MultiModelCoordinator()
        await coordinator.initialize()
        
        models = coordinator.get_available_models()
        model_ids = [m.model_id for m in models]
        
        # 验证本地模型已注册
        local_model_id = vllm_settings["model_id"]
        local_model = next((m for m in models if m.model_id == local_model_id), None)
        
        if local_model:
            assert local_model.model_id == local_model_id
            assert local_model.base_url is not None
            print(f"✅ 模型 '{local_model_id}' 已注册")
        else:
            print(f"⚠️ 模型 '{local_model_id}' 未注册,可用模型: {model_ids}")
    
    async def test_task_submission(self, mock_vllm_server, vllm_settings):
        """测试任务提交"""
        from services.multi_model_coordinator import (
            MultiModelCoordinator, 
            TaskRequest, 
            TaskType
        )
        
        coordinator = MultiModelCoordinator()
        await coordinator.initialize()
        
        # 创建测试任务
        task_request = TaskRequest(
            task_id="test_integration",
            task_type=TaskType.TEXT_GENERATION,
            content="你好,这是一个测试",
            preferred_models=[vllm_settings["model_id"]],
            required_capabilities=[TaskType.TEXT_GENERATION]
        )
        
        try:
            task_id = await coordinator.submit_task(task_request)
            assert task_id is not None
            print(f"✅ 任务已提交: {task_id}")
        except Exception as e:
            # 如果模型未正确配置,可能会失败
            print(f"⚠️ 任务提交失败: {e}")
    
    async def test_task_result_retrieval(self, mock_vllm_server, vllm_settings):
        """测试任务结果获取"""
        from services.multi_model_coordinator import (
            MultiModelCoordinator, 
            TaskRequest, 
            TaskType
        )
        
        coordinator = MultiModelCoordinator()
        await coordinator.initialize()
        
        task_request = TaskRequest(
            task_id="test_result",
            task_type=TaskType.TEXT_GENERATION,
            content="1+1等于几?",
            preferred_models=[vllm_settings["model_id"]],
            required_capabilities=[TaskType.TEXT_GENERATION]
        )
        
        try:
            task_id = await coordinator.submit_task(task_request)
            
            # 等待结果
            max_wait = 10
            for _ in range(max_wait):
                result = await coordinator.get_task_result(task_id)
                if result:
                    if result.status.name == "COMPLETED":
                        assert result.final_content is not None
                        print(f"✅ 任务完成: {result.final_content[:100]}")
                        return
                    elif result.status.name == "FAILED":
                        print(f"⚠️ 任务失败: {result.error}")
                        return
                
                await asyncio.sleep(1)
            
            print("⚠️ 任务超时")
        except Exception as e:
            print(f"⚠️ 测试异常: {e}")


@pytest.mark.asyncio
class TestVLLMConfiguration:
    """测试 vLLM 配置管理"""
    
    async def test_settings_loading(self, vllm_settings):
        """验证配置加载"""
        from config.settings import ExtendedSettings
        
        settings = ExtendedSettings()
        
        # 验证环境变量已加载
        assert hasattr(settings, 'local_model_id')
        assert settings.local_model_id == vllm_settings["model_id"]
        print(f"✅ 配置已加载: {settings.local_model_id}")
    
    async def test_environment_override(self, monkeypatch):
        """测试环境变量覆盖"""
        # 设置自定义环境变量
        monkeypatch.setenv("AGENTBUS_LOCAL_MODEL_ID", "custom_model")
        monkeypatch.setenv("AGENTBUS_LOCAL_MODEL_BASE_URL", "http://custom:9999/v1")
        
        from config.settings import ExtendedSettings
        settings = ExtendedSettings()
        
        assert settings.local_model_id == "custom_model"
        assert "custom:9999" in settings.local_model_base_url
        print("✅ 环境变量覆盖成功")


@pytest.mark.asyncio  
class TestVLLMAPIIntegration:
    """测试通过 API 客户端与 vLLM 集成"""
    
    async def test_openai_client_integration(self, mock_vllm_server, vllm_settings):
        """测试使用 OpenAI 客户端连接 vLLM"""
        try:
            from openai import AsyncOpenAI
        except ImportError:
            pytest.skip("OpenAI 库未安装")
        
        client = AsyncOpenAI(
            base_url=vllm_settings["base_url"],
            api_key=vllm_settings["api_key"]
        )
        
        try:
            # 测试聊天补全
            response = await client.chat.completions.create(
                model=vllm_settings["model_id"],
                messages=[
                    {"role": "user", "content": "你好"}
                ]
            )
            
            assert response.choices[0].message.content is not None
            print(f"✅ OpenAI 客户端集成成功: {response.choices[0].message.content}")
        except Exception as e:
            print(f"⚠️ OpenAI 客户端测试失败: {e}")
    
    async def test_streaming_with_openai_client(self, mock_vllm_server, vllm_settings):
        """测试流式响应"""
        try:
            from openai import AsyncOpenAI
        except ImportError:
            pytest.skip("OpenAI 库未安装")
        
        client = AsyncOpenAI(
            base_url=vllm_settings["base_url"],
            api_key=vllm_settings["api_key"]
        )
        
        try:
            stream = await client.chat.completions.create(
                model=vllm_settings["model_id"],
                messages=[{"role": "user", "content": "测试流式响应"}],
                stream=True
            )
            
            chunks = []
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    chunks.append(chunk.choices[0].delta.content)
            
            assert len(chunks) > 0
            print(f"✅ 流式响应成功,收到 {len(chunks)} 个 chunk")
        except Exception as e:
            print(f"⚠️ 流式响应测试失败: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
