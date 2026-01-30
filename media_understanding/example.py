"""
媒体理解系统配置和使用示例

演示如何配置和使用AgentBus媒体理解系统
"""

import asyncio
import os
from typing import Dict, List, Optional

from .core import MediaUnderstandingSystem, get_media_understanding_system
from .types import MediaUnderstandingContext, MediaAttachment, MediaUnderstandingConfig
from .image_understanding import (
    OpenAIImageProvider,
    AnthropicImageProvider,
    LocalImageProvider
)
from .audio_understanding import (
    OpenAIAudioProvider,
    LocalAudioProvider
)
from .video_understanding import (
    GoogleVideoProvider,
    LocalVideoProvider
)


def create_sample_config() -> Dict:
    """创建示例配置"""
    return {
        "enabled": True,
        "timeout": 30.0,
        "max_file_size": 10 * 1024 * 1024,  # 10MB
        "max_concurrent": 3,
        
        # 图像理解配置
        "image": {
            "enabled": True,
            "prompt": "请详细描述这张图片的内容，包括主要元素、文字信息、场景等",
            "max_tokens": 1000,
            "temperature": 0.1
        },
        
        # 音频理解配置
        "audio": {
            "enabled": True,
            "prompt": "请转录音频内容并提供详细说明",
            "language": "zh-CN",
            "temperature": 0.0
        },
        
        # 视频理解配置
        "video": {
            "enabled": True,
            "prompt": "请分析视频内容，包括主要场景、人物、动作和关键事件",
            "max_duration": 300  # 最大5分钟
        },
        
        # 文档理解配置
        "document": {
            "enabled": True,
            "extract_tables": True,
            "extract_images": False,
            "max_pages": 10
        },
        
        # Provider配置
        "providers": {
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "base_url": "https://api.openai.com/v1"
            },
            "anthropic": {
                "api_key": os.getenv("ANTHROPIC_API_KEY")
            },
            "google": {
                "api_key": os.getenv("GOOGLE_API_KEY")
            }
        }
    }


def setup_providers(system: MediaUnderstandingSystem):
    """设置媒体理解Provider"""
    
    # 设置图像Provider
    openai_image = OpenAIImageProvider(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://api.openai.com/v1"
    )
    
    anthropic_image = AnthropicImageProvider(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
    local_image = LocalImageProvider()
    
    system.register_provider("image", openai_image)
    system.register_provider("image", anthropic_image)
    system.register_provider("image", local_image)
    
    # 设置音频Provider
    openai_audio = OpenAIAudioProvider(
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    local_audio = LocalAudioProvider()
    
    system.register_provider("audio", openai_audio)
    system.register_provider("audio", local_audio)
    
    # 设置视频Provider
    google_video = GoogleVideoProvider(
        api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    local_video = LocalVideoProvider()
    
    system.register_provider("video", google_video)
    system.register_provider("video", local_video)
    
    print("✅ Providers配置完成")


def create_sample_context() -> MediaUnderstandingContext:
    """创建示例上下文"""
    
    # 创建配置
    config = MediaUnderstandingConfig(
        enabled=True,
        timeout=30.0,
        max_file_size=10 * 1024 * 1024,
        
        # 图像配置
        image_config={
            "enabled": True,
            "prompt": "请详细描述这张图片的内容",
            "max_tokens": 1000
        },
        
        # 音频配置
        audio_config={
            "enabled": True,
            "prompt": "请转录音频内容",
            "language": "zh-CN"
        },
        
        # 视频配置
        video_config={
            "enabled": True,
            "prompt": "请分析视频内容",
            "max_duration": 300
        },
        
        # 文档配置
        document_config={
            "enabled": True,
            "extract_tables": True,
            "extract_images": False
        }
    )
    
    # 创建附件（示例）
    attachments = [
        MediaAttachment(
            path="sample.jpg",  # 需要实际存在的文件
            mime="image/jpeg",
            index=0
        )
    ]
    
    return MediaUnderstandingContext(
        attachments=attachments,
        config=config,
        user_id="sample_user",
        session_id="sample_session"
    )


async def demo_single_media():
    """演示单个媒体文件理解"""
    print("🎯 演示：单个媒体文件理解")
    
    # 获取系统实例
    system = get_media_understanding_system()
    
    # 设置Provider
    setup_providers(system)
    
    # 创建示例附件
    # 注意：这里使用示例文件路径，实际使用时需要替换为真实文件
    sample_attachments = [
        # 图像文件示例
        MediaAttachment(
            path="/path/to/sample.jpg",  # 需要真实图片文件
            mime="image/jpeg",
            index=0
        ),
        
        # 音频文件示例
        MediaAttachment(
            path="/path/to/sample.wav",  # 需要真实音频文件
            mime="audio/wav",
            index=1
        ),
        
        # 视频文件示例
        MediaAttachment(
            path="/path/to/sample.mp4",  # 需要真实视频文件
            mime="video/mp4",
            index=2
        ),
        
        # 文档文件示例
        MediaAttachment(
            path="/path/to/sample.pdf",  # 需要真实PDF文件
            mime="application/pdf",
            index=3
        )
    ]
    
    # 过滤存在的文件
    existing_attachments = []
    for attachment in sample_attachments:
        if os.path.exists(attachment.path):
            existing_attachments.append(attachment)
            print(f"✅ 发现文件: {attachment.path}")
        else:
            print(f"❌ 文件不存在: {attachment.path}")
    
    if not existing_attachments:
        print("⚠️  没有找到任何示例文件，创建虚拟测试")
        # 创建虚拟测试
        existing_attachments = [
            MediaAttachment(
                path="virtual_test.txt",
                mime="text/plain",
                index=0
            )
        ]
    
    # 创建上下文
    config = MediaUnderstandingConfig(
        enabled=True,
        image_config={"enabled": True, "prompt": "描述图片内容"},
        audio_config={"enabled": True, "prompt": "转录音频"},
        video_config={"enabled": True, "prompt": "分析视频"},
        document_config={"enabled": True, "extract_tables": True}
    )
    
    context = MediaUnderstandingContext(
        attachments=existing_attachments,
        config=config,
        user_id="demo_user"
    )
    
    # 设置首选Provider
    preferred_providers = {
        "image": "local",
        "audio": "local",
        "video": "local",
        "document": "local"
    }
    
    try:
        # 执行媒体理解
        result = await system.understand_media(context, preferred_providers)
        
        print(f"📊 理解结果:")
        print(f"   成功: {result.success}")
        print(f"   输出数量: {len(result.outputs)}")
        print(f"   处理时间: {result.total_processing_time:.2f}秒")
        print(f"   应用能力: {[cap.value for cap in result.applied_capabilities]}")
        
        if result.error:
            print(f"   错误: {result.error}")
        
        # 显示输出结果
        for i, output in enumerate(result.outputs):
            print(f"\n📝 输出 {i+1}:")
            print(f"   类型: {output.kind.value}")
            print(f"   Provider: {output.provider}")
            print(f"   文本: {output.text[:200]}{'...' if len(output.text) > 200 else ''}")
        
        # 显示决策信息
        print(f"\n🎯 决策信息:")
        for decision in result.decisions:
            print(f"   {decision.capability.value}: {decision.outcome.value}")
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")


async def demo_batch_processing():
    """演示批量处理"""
    print("\n🚀 演示：批量媒体处理")
    
    system = get_media_understanding_system()
    
    # 模拟多个附件
    batch_attachments = [
        MediaAttachment(
            path=f"test_file_{i}.txt",
            mime="text/plain",
            index=i
        )
        for i in range(3)
    ]
    
    # 批量处理每个附件
    for attachment in batch_attachments:
        context = MediaUnderstandingContext(
            attachments=[attachment],
            config=MediaUnderstandingConfig(enabled=True),
            user_id="batch_user"
        )
        
        try:
            result = await system.understand_media(context)
            print(f"✅ 文件 {attachment.path}: {'成功' if result.success else '失败'}")
        except Exception as e:
            print(f"❌ 文件 {attachment.path}: {e}")


async def demo_system_info():
    """演示系统信息查询"""
    print("\nℹ️ 演示：系统信息查询")
    
    system = get_media_understanding_system()
    info = system.get_system_info()
    
    print(f"📋 系统信息:")
    print(f"   启用状态: {info['enabled']}")
    print(f"   超时时间: {info['timeout']}秒")
    print(f"   最大文件大小: {info['max_file_size']} 字节")
    print(f"   最大并发数: {info['max_concurrent']}")
    
    print(f"\n🔧 可用Provider:")
    for provider_type, providers in info['available_providers'].items():
        print(f"   {provider_type}: {', '.join(providers) if providers else '无'}")
    
    print(f"\n📊 处理统计:")
    stats = info['stats']
    print(f"   总处理数: {stats['total_processed']}")
    print(f"   成功数: {stats['successful']}")
    print(f"   失败数: {stats['failed']}")


async def main():
    """主演示函数"""
    print("🎉 AgentBus 媒体理解系统演示")
    print("=" * 50)
    
    # 设置环境变量（如果有的话）
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  未设置 OPENAI_API_KEY，将使用本地Provider")
    
    # 系统信息演示
    await demo_system_info()
    
    # 单文件处理演示
    await demo_single_media()
    
    # 批量处理演示
    await demo_batch_processing()
    
    print("\n✨ 演示完成！")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())