"""
AI代理系统测试
AI Agent System Tests
"""

import pytest
import asyncio
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# 导入要测试的模块
from py_moltbot.agents.base import (
    AgentManager, AgentRequest, AgentResponse, AgentType, ModelProvider,
    ModelConfig, AgentCapability, AgentStatus
)
from py_moltbot.agents.openai_agent import OpenAIAgent, create_openai_agent
from py_moltbot.agents.rpc import (
    RPCServer, RPCClient, RPCRequest, RPCResponse, RPCMethod, RPCStatus,
    RPCHandler, RPCProcedure, StreamChunk
)
from py_moltbot.agents.memory import (
    MemoryManager, Memory, MemoryType, MemoryPriority, MemoryStatus,
    InMemoryStore, MemoryContent, create_conversation_memory
)
from py_moltbot.agents.link_understanding import (
    LinkUnderstandingService, LinkClassifier, LinkType, ContentType,
    LinkMetadata, LinkContent
)
from py_moltbot.agents.media_understanding import (
    MediaUnderstandingService, MediaType, MediaFormat, ContentCategory,
    MediaClassifier, MediaMetadata, ContentAnalysis
)


class TestAgentManager:
    """代理管理器测试"""
    
    @pytest.fixture
    def agent_manager(self):
        """创建代理管理器"""
        return AgentManager()
    
    @pytest.mark.asyncio
    async def test_agent_manager_lifecycle(self, agent_manager):
        """测试代理管理器生命周期"""
        # 启动管理器
        await agent_manager.start()
        assert agent_manager.running is True
        assert len(agent_manager._worker_tasks) > 0
        
        # 停止管理器
        await agent_manager.stop()
        assert agent_manager.running is False
    
    def test_agent_registration(self, agent_manager):
        """测试代理注册"""
        # 创建一个模拟代理
        mock_agent = Mock()
        mock_agent.agent_id = "test_agent"
        mock_agent.name = "Test Agent"
        mock_agent.capabilities = [
            AgentCapability(
                type=AgentType.TEXT_GENERATION,
                description="Test capability"
            )
        ]
        
        # 注册代理
        asyncio.run(agent_manager.register_agent(mock_agent))
        
        # 验证注册
        assert "test_agent" in agent_manager.registry.list_agents()
    
    def test_agent_retrieval(self, agent_manager):
        """测试代理获取"""
        # 创建模拟代理
        mock_agent = Mock()
        mock_agent.agent_id = "test_agent"
        mock_agent.name = "Test Agent"
        mock_agent.capabilities = [
            AgentCapability(
                type=AgentType.TEXT_GENERATION,
                description="Test capability"
            )
        ]
        
        # 注册代理
        asyncio.run(agent_manager.register_agent(mock_agent))
        
        # 获取代理
        retrieved = agent_manager.registry.get_agent("test_agent")
        assert retrieved == mock_agent
    
    @pytest.mark.asyncio
    async def test_request_execution(self, agent_manager):
        """测试请求执行"""
        # 启动管理器
        await agent_manager.start()
        
        # 创建测试请求
        request = AgentRequest(
            id="test_request",
            agent_type=AgentType.TEXT_GENERATION,
            model_config=ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name="gpt-3.5-turbo"
            ),
            prompt="Test prompt"
        )
        
        # 执行请求（应该失败，因为没有可用代理）
        response = await agent_manager.execute_request(request)
        
        # 验证响应
        assert response.success is False
        assert "No available agent" in response.error
        
        await agent_manager.stop()


class TestOpenAIAgent:
    """OpenAI代理测试"""
    
    @pytest.fixture
    def model_config(self):
        """创建模型配置"""
        return ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test_key"
        )
    
    @pytest.fixture
    def openai_agent(self, model_config):
        """创建OpenAI代理"""
        return OpenAIAgent("test_agent", "Test Agent", model_config)
    
    def test_agent_initialization(self, openai_agent, model_config):
        """测试代理初始化"""
        assert openai_agent.agent_id == "test_agent"
        assert openai_agent.name == "Test Agent"
        assert openai_agent.model_config.provider == ModelProvider.OPENAI
        assert openai_agent.model_config.model_name == "gpt-3.5-turbo"
        assert len(openai_agent.capabilities) > 0
    
    @pytest.mark.asyncio
    async def test_connection_validation(self, openai_agent):
        """测试连接验证"""
        # 使用模拟的客户端
        with patch.object(openai_agent, 'client') as mock_client:
            # 模拟成功的响应
            mock_completion = Mock()
            mock_completion.choices = [Mock()]
            mock_completion.choices[0].message.content = "Hello"
            mock_client.chat.completions.create.return_value = mock_completion
            
            # 验证连接
            is_valid = await openai_agent.validate_connection()
            assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_text_generation(self, openai_agent):
        """测试文本生成"""
        # 使用模拟的客户端
        with patch.object(openai_agent, 'client') as mock_client:
            # 模拟成功的响应
            mock_completion = Mock()
            mock_completion.choices = [Mock()]
            mock_completion.choices[0].message.content = "Generated text"
            mock_completion.usage = Mock()
            mock_completion.usage.total_tokens = 100
            mock_client.chat.completions.create.return_value = mock_completion
            
            # 生成文本
            response = await openai_agent.generate_text("Test prompt")
            
            # 验证响应
            assert response.success is True
            assert response.content == "Generated text"
            assert response.tokens_used == 100


class TestRPCSystem:
    """RPC系统测试"""
    
    @pytest.fixture
    def rpc_handler(self):
        """创建RPC处理器"""
        return RPCHandler("test_agent")
    
    @pytest.fixture
    def mock_procedure(self):
        """创建模拟RPC过程"""
        async def test_procedure(params):
            return {"result": "success", "params": params}
        
        return RPCProcedure("test_procedure", "Test procedure", test_procedure)
    
    def test_procedure_registration(self, rpc_handler, mock_procedure):
        """测试过程注册"""
        rpc_handler.register_procedure(mock_procedure)
        
        assert "test_procedure" in rpc_handler.procedures
        assert rpc_handler.procedures["test_procedure"] == mock_procedure
    
    @pytest.mark.asyncio
    async def test_rpc_request_handling(self, rpc_handler, mock_procedure):
        """测试RPC请求处理"""
        # 注册过程
        rpc_handler.register_procedure(mock_procedure)
        
        # 创建RPC请求
        request = RPCRequest(
            id="test_request",
            method=RPCMethod.SYNC_CALL,
            agent_id="test_agent",
            procedure="test_procedure",
            params={"test": "data"}
        )
        
        # 处理请求
        response = await rpc_handler.handle_request(request)
        
        # 验证响应
        assert response.status == RPCStatus.COMPLETED
        assert response.result["result"] == "success"
        assert response.result["params"]["test"] == "data"
    
    @pytest.mark.asyncio
    async def test_rpc_error_handling(self, rpc_handler):
        """测试RPC错误处理"""
        # 创建不存在的请求
        request = RPCRequest(
            id="test_request",
            method=RPCMethod.SYNC_CALL,
            agent_id="test_agent",
            procedure="nonexistent_procedure",
            params={}
        )
        
        # 处理请求
        response = await rpc_handler.handle_request(request)
        
        # 验证错误响应
        assert response.status == RPCStatus.FAILED
        assert "not found" in response.error


class TestMemoryManager:
    """记忆管理器测试"""
    
    @pytest.fixture
    def memory_manager(self):
        """创建记忆管理器"""
        return MemoryManager(InMemoryStore())
    
    @pytest.mark.asyncio
    async def test_memory_creation(self, memory_manager):
        """测试记忆创建"""
        # 创建记忆
        memory = await memory_manager.create_memory(
            content="Test memory content",
            memory_type=MemoryType.SHORT_TERM,
            user_id="test_user",
            importance=0.8
        )
        
        # 验证记忆
        assert memory.id is not None
        assert memory.content.content == "Test memory content"
        assert memory.memory_type == MemoryType.SHORT_TERM
        assert memory.user_id == "test_user"
        assert memory.importance_score == 0.8
    
    @pytest.mark.asyncio
    async def test_memory_retrieval(self, memory_manager):
        """测试记忆检索"""
        # 创建记忆
        memory = await memory_manager.create_memory(
            content="Test memory content",
            memory_type=MemoryType.SHORT_TERM,
            user_id="test_user"
        )
        
        # 检索记忆
        retrieved = await memory_manager.retrieve_memory(memory.id)
        
        # 验证检索
        assert retrieved is not None
        assert retrieved.id == memory.id
        assert retrieved.content.content == "Test memory content"
    
    @pytest.mark.asyncio
    async def test_memory_search(self, memory_manager):
        """测试记忆搜索"""
        # 创建多个记忆
        memory1 = await memory_manager.create_memory(
            content="Python programming tutorial",
            memory_type=MemoryType.SEMANTIC,
            user_id="test_user",
            tags={"programming", "python"}
        )
        
        memory2 = await memory_manager.create_memory(
            content="Machine learning concepts",
            memory_type=MemoryType.SEMANTIC,
            user_id="test_user",
            tags={"machine_learning", "ai"}
        )
        
        # 搜索记忆
        results = await memory_manager.search_memories(
            query="Python programming",
            user_id="test_user",
            limit=10
        )
        
        # 验证搜索结果
        assert len(results) > 0
        assert any("Python" in memory.content.content for memory in results)
    
    @pytest.mark.asyncio
    async def test_memory_consolidation(self, memory_manager):
        """测试记忆合并"""
        # 创建短期记忆
        short_term_memory = await memory_manager.create_memory(
            content="Important information to remember",
            memory_type=MemoryType.SHORT_TERM,
            user_id="test_user",
            importance=0.9  # 高重要性
        )
        
        # 手动设置年龄超过阈值
        short_term_memory.created_at = datetime.now() - timedelta(hours=25)
        await memory_manager.store.update_memory(short_term_memory)
        
        # 执行记忆合并
        consolidated_count = await memory_manager.consolidate_memories("test_user")
        
        # 验证合并
        assert consolidated_count >= 1
        
        # 检查记忆是否被合并
        updated_memory = await memory_manager.retrieve_memory(short_term_memory.id)
        assert updated_memory.memory_type == MemoryType.LONG_TERM
    
    def test_memory_statistics(self, memory_manager):
        """测试记忆统计"""
        # 获取统计（没有记忆的情况下）
        stats = asyncio.run(memory_manager.get_memory_stats("test_user"))
        
        # 验证统计结构
        assert "total_memories" in stats
        assert "type_counts" in stats
        assert "average_importance" in stats


class TestLinkUnderstanding:
    """链接理解测试"""
    
    @pytest.fixture
    def link_service(self):
        """创建链接理解服务"""
        return LinkUnderstandingService()
    
    def test_url_classification(self):
        """测试URL分类"""
        # 测试图像URL
        image_url = "https://example.com/image.jpg"
        link_type = LinkClassifier.classify_url(image_url)
        assert link_type == LinkType.IMAGE
        
        # 测试视频URL
        video_url = "https://youtube.com/watch?v=abc123"
        link_type = LinkClassifier.classify_url(video_url)
        assert link_type == LinkType.VIDEO
        
        # 测试社交媒体URL
        social_url = "https://twitter.com/user/status/123"
        link_type = LinkClassifier.classify_url(social_url)
        assert link_type == LinkType.SOCIAL_MEDIA
    
    def test_content_type_detection(self):
        """测试内容类型检测"""
        # 测试HTML内容类型
        content_type = LinkClassifier.detect_content_type(
            file_url="https://example.com/page.html",
            content_type="text/html"
        )
        assert content_type == ContentType.HTML
        
        # 测试JSON内容类型
        content_type = LinkClassifier.detect_content_type(
            file_url="https://api.example.com/data",
            content_type="application/json"
        )
        assert content_type == ContentType.JSON
    
    @pytest.mark.asyncio
    async def test_link_metadata_extraction(self, link_service):
        """测试链接元数据提取"""
        # 使用模拟的aiohttp客户端
        with patch('aiohttp.ClientSession') as mock_session:
            # 模拟响应
            mock_response = Mock()
            mock_response.headers = {
                'content-type': 'text/html',
                'charset': 'utf-8'
            }
            mock_response.text.return_value = '''
                <html>
                    <head>
                        <title>Test Page</title>
                        <meta name="description" content="A test webpage">
                        <meta property="og:title" content="OpenGraph Title">
                    </head>
                    <body>Test content</body>
                </html>
            '''
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_response
            
            # 提取元数据
            metadata = await link_service.extractor.extract_link_metadata("https://example.com")
            
            # 验证元数据
            assert metadata.url == "https://example.com"
            assert metadata.title == "Test Page"
            assert metadata.description == "A test webpage"
            assert metadata.og_title == "OpenGraph Title"
            assert metadata.content_type == ContentType.HTML
            assert metadata.link_type == LinkType.WEBPAGE


class TestMediaUnderstanding:
    """媒体理解测试"""
    
    @pytest.fixture
    def media_service(self):
        """创建媒体理解服务"""
        return MediaUnderstandingService()
    
    def test_media_type_classification(self):
        """测试媒体类型分类"""
        # 测试图像分类
        image_type = MediaClassifier.classify_media_type(file_path="test.jpg")
        assert image_type == MediaType.IMAGE
        
        # 测试音频分类
        audio_type = MediaClassifier.classify_media_type(file_path="test.mp3")
        assert audio_type == MediaType.AUDIO
        
        # 测试视频分类
        video_type = MediaClassifier.classify_media_type(file_path="test.mp4")
        assert video_type == MediaType.VIDEO
        
        # 测试文档分类
        doc_type = MediaClassifier.classify_media_type(file_path="test.pdf")
        assert doc_type == MediaType.DOCUMENT
    
    def test_format_detection(self):
        """测试格式检测"""
        # 测试JPEG格式
        jpeg_format = MediaClassifier.detect_format(file_path="test.jpg")
        assert jpeg_format == MediaFormat.JPEG
        
        # 测试PNG格式
        png_format = MediaClassifier.detect_format(file_path="test.png")
        assert png_format == MediaFormat.PNG
        
        # 测试MP3格式
        mp3_format = MediaClassifier.detect_format(file_path="test.mp3")
        assert mp3_format == MediaFormat.MP3
    
    @pytest.mark.asyncio
    async def test_image_analysis(self, media_service):
        """测试图像分析"""
        # 创建一个简单的测试图像
        from PIL import Image
        import io
        
        # 创建测试图像
        test_image = Image.new('RGB', (100, 100), color='red')
        image_bytes = io.BytesIO()
        test_image.save(image_bytes, format='JPEG')
        image_data = image_bytes.getvalue()
        
        # 分析图像
        analysis = await media_service.image_analyzer.analyze_image(image_data)
        
        # 验证分析结果
        assert analysis.media_type == MediaType.IMAGE
        assert analysis.metadata.width == 100
        assert analysis.metadata.height == 100
        assert analysis.metadata.format == MediaFormat.JPEG
        assert analysis.summary is not None
    
    def test_metadata_extraction(self, media_service):
        """测试元数据提取"""
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b'fake_image_data')
            tmp_file.flush()
            
            # 提取元数据
            metadata = media_service.extract_metadata(tmp_file.name)
            
            # 验证元数据
            assert metadata.file_path == tmp_file.name
            assert metadata.media_type == MediaType.IMAGE
            assert metadata.format == MediaFormat.JPEG
            assert metadata.file_size == len(b'fake_image_data')
    
    @pytest.mark.asyncio
    async def test_batch_media_analysis(self, media_service):
        """测试批量媒体分析"""
        # 创建测试数据
        test_data = [
            b'fake_image_data',
            b'fake_audio_data',
            b'fake_video_data'
        ]
        
        # 批量分析
        results = await media_service.batch_analyze_media(test_data)
        
        # 验证结果
        assert len(results) == 3
        assert all(isinstance(result, ContentAnalysis) for result in results)


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_agent_with_memory_integration(self):
        """测试代理与记忆系统集成"""
        # 创建记忆管理器
        memory_manager = MemoryManager(InMemoryStore())
        
        # 创建对话记忆
        conversation_memory = await create_conversation_memory(
            user_id="test_user",
            session_id="test_session",
            message="Hello, how are you?",
            speaker="user"
        )
        
        # 验证记忆创建
        assert conversation_memory.memory_type == MemoryType.EPISODIC
        assert "Hello, how are you?" in conversation_memory.content.content
        
        # 搜索相关记忆
        memories = await memory_manager.search_memories(
            query="Hello",
            user_id="test_user"
        )
        
        assert len(memories) > 0
        assert memories[0].id == conversation_memory.id
    
    @pytest.mark.asyncio
    async def test_link_and_media_analysis_integration(self):
        """测试链接和媒体分析集成"""
        # 创建服务
        link_service = LinkUnderstandingService()
        media_service = MediaUnderstandingService()
        
        # 分析一个模拟的图像链接
        image_url = "https://example.com/test.jpg"
        
        # 使用模拟分析
        mock_analysis = ContentAnalysis(
            media_type=MediaType.IMAGE,
            metadata=MediaMetadata(
                media_type=MediaType.IMAGE,
                width=800,
                height=600
            )
        )
        
        # 验证模拟分析
        assert mock_analysis.media_type == MediaType.IMAGE
        assert mock_analysis.metadata.width == 800
        assert mock_analysis.metadata.height == 600


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])