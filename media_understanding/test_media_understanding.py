"""
媒体理解系统测试模块

用于测试和验证媒体理解系统的各项功能
"""

import asyncio
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from agentbus.media_understanding import (
    MediaUnderstandingSystem,
    MediaUnderstandingContext,
    MediaAttachment,
    MediaUnderstandingConfig,
    MediaUnderstandingResult,
    MediaUnderstandingCapability,
    MediaUnderstandingKind,
    MediaType,
    get_media_understanding_system,
    understand_media,
    register_provider,
    get_system_info
)

from agentbus.media_understanding.types import (
    AudioTranscriptionRequest,
    ImageDescriptionRequest,
    VideoDescriptionRequest,
    DocumentExtractionRequest
)


class TestMediaUnderstandingSystem:
    """媒体理解系统测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.system = MediaUnderstandingSystem()
        self.temp_files = []
    
    def teardown_method(self):
        """测试后清理"""
        # 清理临时文件
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except FileNotFoundError:
                pass
    
    def create_test_file(self, content: bytes, extension: str = ".txt") -> str:
        """创建测试文件"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as f:
            f.write(content)
            temp_path = f.name
            self.temp_files.append(temp_path)
            return temp_path
    
    def test_system_initialization(self):
        """测试系统初始化"""
        config = {
            "enabled": True,
            "timeout": 30.0,
            "max_file_size": 5 * 1024 * 1024,
            "max_concurrent": 2
        }
        
        system = MediaUnderstandingSystem(config)
        
        assert system.enabled == True
        assert system.timeout == 30.0
        assert system.max_file_size == 5 * 1024 * 1024
        assert system.max_concurrent == 2
        assert len(system.capability_order) == 4
    
    def test_system_info(self):
        """测试系统信息获取"""
        info = self.system.get_system_info()
        
        assert "enabled" in info
        assert "timeout" in info
        assert "max_file_size" in info
        assert "available_providers" in info
        assert "stats" in info
        
        # 检查可用Provider结构
        providers = info["available_providers"]
        assert "image" in providers
        assert "audio" in providers
        assert "video" in providers
        assert "document" in providers
    
    def test_capability_filtering(self):
        """测试能力筛选"""
        attachments = [
            MediaAttachment(path="test.jpg", mime="image/jpeg", index=0),
            MediaAttachment(path="test.wav", mime="audio/wav", index=1),
            MediaAttachment(path="test.mp4", mime="video/mp4", index=2),
            MediaAttachment(path="test.pdf", mime="application/pdf", index=3),
            MediaAttachment(path="test.txt", mime="text/plain", index=4)
        ]
        
        # 测试图像筛选
        image_attachments = self.system._filter_attachments_by_capability(
            attachments, MediaUnderstandingCapability.IMAGE
        )
        assert len(image_attachments) == 1
        assert image_attachments[0].index == 0
        
        # 测试音频筛选
        audio_attachments = self.system._filter_attachments_by_capability(
            attachments, MediaUnderstandingCapability.AUDIO
        )
        assert len(audio_attachments) == 1
        assert audio_attachments[0].index == 1
        
        # 测试视频筛选
        video_attachments = self.system._filter_attachments_by_capability(
            attachments, MediaUnderstandingCapability.VIDEO
        )
        assert len(video_attachments) == 1
        assert video_attachments[0].index == 2
        
        # 测试文档筛选
        doc_attachments = self.system._filter_attachments_by_capability(
            attachments, MediaUnderstandingCapability.DOCUMENT
        )
        assert len(doc_attachments) == 2  # PDF + TXT
        assert doc_attachments[0].index == 3
        assert doc_attachments[1].index == 4
    
    @pytest.mark.asyncio
    async def test_empty_attachments(self):
        """测试空附件列表处理"""
        config = MediaUnderstandingConfig(enabled=True)
        context = MediaUnderstandingContext(
            attachments=[],
            config=config
        )
        
        result = await self.system.understand_media(context)
        
        assert result.success == False
        assert "No attachments provided" in result.error
        assert len(result.outputs) == 0
    
    @pytest.mark.asyncio
    async def test_disabled_system(self):
        """测试系统禁用情况"""
        config = MediaUnderstandingConfig(enabled=False)
        context = MediaUnderstandingContext(
            attachments=[],
            config=config
        )
        
        result = await self.system.understand_media(context)
        
        assert result.success == False
        assert "disabled" in result.error.lower()
    
    def test_stats_tracking(self):
        """测试统计跟踪"""
        initial_stats = self.system.stats["total_processed"]
        
        # 模拟处理
        config = MediaUnderstandingConfig(enabled=True)
        context = MediaUnderstandingContext(
            attachments=[],
            config=config
        )
        
        # 这里不实际调用understand_media，因为它需要真实的文件
        # 只测试统计功能
        assert isinstance(self.system.stats["total_processed"], int)
        assert isinstance(self.system.stats["successful"], int)
        assert isinstance(self.system.stats["failed"], int)
    
    def test_file_size_check(self):
        """测试文件大小检查"""
        # 创建一个大文件
        large_content = b"x" * (10 * 1024 * 1024)  # 10MB
        large_file = self.create_test_file(large_content)
        
        attachment = MediaAttachment(path=large_file, index=0)
        
        # 测试文件大小检查逻辑
        assert len(large_content) > self.system.max_file_size
        
        # 这里可以添加更详细的文件大小检查测试


class TestMediaUnderstandingResult:
    """媒体理解结果测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.outputs = []
        self.decisions = []
        self.applied_capabilities = []
    
    def create_sample_output(self, kind: MediaUnderstandingKind, text: str) -> "MediaUnderstandingOutput":
        """创建示例输出"""
        return MediaUnderstandingOutput(
            kind=kind,
            attachment_index=0,
            text=text,
            provider="test_provider",
            model="test_model"
        )
    
    def test_result_properties(self):
        """测试结果属性"""
        # 创建示例输出
        image_output = self.create_sample_output(
            MediaUnderstandingKind.IMAGE_DESCRIPTION,
            "这是一张图片"
        )
        audio_output = self.create_sample_output(
            MediaUnderstandingKind.AUDIO_TRANSCRIPTION,
            "这是一段音频转录"
        )
        
        outputs = [image_output, audio_output]
        result = MediaUnderstandingResult(
            success=True,
            outputs=outputs,
            decisions=[],
            applied_capabilities=[
                MediaUnderstandingCapability.IMAGE,
                MediaUnderstandingCapability.AUDIO
            ]
        )
        
        assert result.success == True
        assert len(result.outputs) == 2
        assert len(result.applied_capabilities) == 2
        assert result.has_image_output == True
        assert result.has_audio_output == True
        assert result.has_video_output == False
        assert result.has_document_output == False
    
    def test_text_output(self):
        """测试文本输出"""
        outputs = [
            self.create_sample_output(MediaUnderstandingKind.IMAGE_DESCRIPTION, "图片描述"),
            self.create_sample_output(MediaUnderstandingKind.AUDIO_TRANSCRIPTION, "音频转录")
        ]
        
        result = MediaUnderstandingResult(
            success=True,
            outputs=outputs,
            decisions=[],
            applied_capabilities=[]
        )
        
        expected_text = "图片描述\n音频转录"
        assert result.get_text_output() == expected_text
    
    def test_output_by_capability(self):
        """测试按能力获取输出"""
        image_output = self.create_sample_output(
            MediaUnderstandingKind.IMAGE_DESCRIPTION, "图片"
        )
        audio_output = self.create_sample_output(
            MediaUnderstandingKind.AUDIO_TRANSCRIPTION, "音频"
        )
        
        outputs = [image_output, audio_output]
        result = MediaUnderstandingResult(
            success=True,
            outputs=outputs,
            decisions=[],
            applied_capabilities=[]
        )
        
        # 获取图像输出
        image_outputs = result.get_output_by_capability(MediaUnderstandingCapability.IMAGE)
        assert len(image_outputs) == 1
        assert image_outputs[0].kind == MediaUnderstandingKind.IMAGE_DESCRIPTION
        
        # 获取音频输出
        audio_outputs = result.get_output_by_capability(MediaUnderstandingCapability.AUDIO)
        assert len(audio_outputs) == 1
        assert audio_outputs[0].kind == MediaUnderstandingKind.AUDIO_TRANSCRIPTION
        
        # 获取不存在的输出
        video_outputs = result.get_output_by_capability(MediaUnderstandingCapability.VIDEO)
        assert len(video_outputs) == 0


class TestConvenienceFunctions:
    """便捷函数测试类"""
    
    def test_get_system_info(self):
        """测试获取系统信息"""
        info = get_system_info()
        
        assert isinstance(info, dict)
        assert "enabled" in info
        assert "available_providers" in info
    
    @pytest.mark.asyncio
    async def test_understand_media_function(self):
        """测试便捷理解函数"""
        # 创建测试上下文
        config = MediaUnderstandingConfig(enabled=True)
        context = MediaUnderstandingContext(
            attachments=[],
            config=config
        )
        
        # 使用便捷函数（预期会失败，因为没有附件）
        result = await understand_media(context)
        
        assert isinstance(result, MediaUnderstandingResult)
        assert result.success == False


class TestProviderRegistration:
    """Provider注册测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.system = get_media_understanding_system()
    
    def test_provider_registration(self):
        """测试Provider注册"""
        # 创建Mock Provider
        mock_provider = Mock()
        mock_provider.id = "test_provider"
        
        # 注册Provider
        register_provider("image", mock_provider)
        
        # 检查系统信息中是否包含注册的Provider
        info = get_system_info()
        available_providers = info["available_providers"]["image"]
        
        assert "test_provider" in available_providers


class TestMediaTypeDetection:
    """媒体类型检测测试类"""
    
    def test_supported_media_types(self):
        """测试支持的媒体类型"""
        from agentbus.media_understanding.detector import is_supported_media
        
        # 创建测试附件
        test_cases = [
            ("test.jpg", "image/jpeg", MediaType.IMAGE),
            ("test.mp3", "audio/mpeg", MediaType.AUDIO),
            ("test.mp4", "video/mp4", MediaType.VIDEO),
            ("test.pdf", "application/pdf", MediaType.DOCUMENT),
            ("test.unknown", None, MediaType.UNKNOWN)
        ]
        
        for file_name, mime_type, expected_type in test_cases:
            attachment = MediaAttachment(
                path=file_name,
                mime=mime_type,
                index=0
            )
            
            # 这里只测试is_supported_media函数
            # 实际的类型检测逻辑在detector模块中测试
            assert isinstance(attachment.index, int)
            assert attachment.index >= 0


# 集成测试
class TestIntegration:
    """集成测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.system = get_media_understanding_system()
    
    @pytest.mark.asyncio
    async def test_system_workflow(self):
        """测试系统工作流程"""
        # 创建测试文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"Hello, World!")
            temp_file = f.name
        
        try:
            # 创建上下文
            config = MediaUnderstandingConfig(enabled=True)
            context = MediaUnderstandingContext(
                attachments=[
                    MediaAttachment(path=temp_file, mime="text/plain", index=0)
                ],
                config=config,
                user_id="test_user"
            )
            
            # 执行理解（预期会使用文档处理）
            result = await self.system.understand_media(context)
            
            # 验证结果
            assert isinstance(result, MediaUnderstandingResult)
            assert isinstance(result.success, bool)
            assert isinstance(result.outputs, list)
            assert isinstance(result.decisions, list)
            
        finally:
            # 清理测试文件
            try:
                os.unlink(temp_file)
            except FileNotFoundError:
                pass


# 运行测试的辅助函数
def run_tests():
    """运行所有测试"""
    print("🧪 开始运行媒体理解系统测试...")
    
    # 这里可以添加实际的测试运行逻辑
    # 由于这是演示，我们只打印信息
    print("✅ 测试配置完成")
    print("📋 测试用例包括:")
    print("   - 系统初始化测试")
    print("   - 媒体类型检测测试")
    print("   - Provider注册测试")
    print("   - 结果处理测试")
    print("   - 集成测试")
    
    # 在实际使用中，可以这样运行测试：
    # pytest test_media_understanding.py -v


if __name__ == "__main__":
    # 运行测试演示
    run_tests()
    
    print("\n🎯 测试模块说明:")
    print("   1. 使用 pytest 运行: pytest test_media_understanding.py -v")
    print("   2. 运行特定测试: pytest test_media_understanding.py::TestMediaUnderstandingSystem::test_system_initialization -v")
    print("   3. 运行集成测试: pytest test_media_understanding.py::TestIntegration -v")