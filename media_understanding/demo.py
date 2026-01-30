#!/usr/bin/env python3
"""
AgentBus 媒体理解系统演示脚本

这是一个简单的演示脚本，展示了媒体理解系统的基本使用方法。
"""

import asyncio
import os
import tempfile
from pathlib import Path

# 导入媒体理解系统
try:
    from agentbus.media_understanding import (
        MediaUnderstandingSystem,
        MediaUnderstandingContext,
        MediaAttachment,
        MediaUnderstandingConfig,
        get_media_understanding_system
    )
    from agentbus.media_understanding.types import MediaUnderstandingCapability, MediaType
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保已正确安装媒体理解系统")
    exit(1)


def create_demo_files():
    """创建演示文件"""
    demo_files = {}
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="agentbus_demo_")
    
    # 创建示例文本文件
    text_content = """AgentBus 媒体理解系统演示

这是一个演示文档，用于测试文档理解功能。

内容包括：
- 系统介绍
- 功能特性
- 使用示例

文档格式：Markdown
创建时间：2024年
"""
    
    text_file = os.path.join(temp_dir, "demo.txt")
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(text_content)
    demo_files["text"] = text_file
    
    # 创建示例JSON文件
    json_content = {
        "name": "AgentBus 媒体理解系统",
        "version": "1.0.0",
        "features": [
            "图像理解",
            "音频转录", 
            "视频分析",
            "文档解析"
        ],
        "supported_formats": {
            "images": ["jpg", "png", "gif", "webp"],
            "audio": ["mp3", "wav", "ogg"],
            "video": ["mp4", "avi", "mov"],
            "documents": ["pdf", "docx", "txt"]
        }
    }
    
    json_file = os.path.join(temp_dir, "demo.json")
    with open(json_file, "w", encoding="utf-8") as f:
        import json
        json.dump(json_content, f, ensure_ascii=False, indent=2)
    demo_files["json"] = json_file
    
    # 创建示例CSV文件
    csv_content = """功能,支持状态,优先级
图像理解,已支持,高
音频转录,已支持,高  
视频分析,已支持,中
文档解析,已支持,高
OCR识别,计划中,中
语音合成,计划中,低
"""
    
    csv_file = os.path.join(temp_dir, "demo.csv")
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write(csv_content)
    demo_files["csv"] = csv_file
    
    return demo_files, temp_dir


async def demo_basic_functionality():
    """演示基本功能"""
    print("🎯 AgentBus 媒体理解系统演示")
    print("=" * 50)
    
    # 获取系统实例
    system = get_media_understanding_system()
    
    # 显示系统信息
    print("📋 系统信息:")
    info = system.get_system_info()
    print(f"   启用状态: {info['enabled']}")
    print(f"   超时时间: {info['timeout']}秒")
    print(f"   最大文件大小: {info['max_file_size'] / 1024 / 1024:.1f}MB")
    print(f"   最大并发数: {info['max_concurrent']}")
    
    # 显示可用Provider
    print("\n🔧 可用Provider:")
    for provider_type, providers in info['available_providers'].items():
        print(f"   {provider_type}: {', '.join(providers) if providers else '无'}")
    
    # 创建演示文件
    print("\n📁 创建演示文件...")
    demo_files, temp_dir = create_demo_files()
    
    try:
        # 测试文档理解功能
        await demo_document_understanding(system, demo_files)
        
        # 测试批量处理
        await demo_batch_processing(system, demo_files)
        
        # 显示统计信息
        await demo_statistics(system)
        
    finally:
        # 清理演示文件
        cleanup_demo_files(temp_dir, demo_files)


async def demo_document_understanding(system, demo_files):
    """演示文档理解功能"""
    print("\n📄 文档理解演示:")
    
    # 创建文档附件
    document_files = [
        demo_files["text"],
        demo_files["json"], 
        demo_files["csv"]
    ]
    
    attachments = []
    for i, file_path in enumerate(document_files):
        attachment = MediaAttachment(
            path=file_path,
            mime="text/plain",  # 这里可以改进为更准确的MIME检测
            index=i
        )
        attachments.append(attachment)
        print(f"   📎 文件 {i+1}: {Path(file_path).name}")
    
    # 创建配置
    config = MediaUnderstandingConfig(
        enabled=True,
        document_config={
            "enabled": True,
            "extract_tables": True,
            "extract_images": False
        }
    )
    
    # 创建上下文
    context = MediaUnderstandingContext(
        attachments=attachments,
        config=config,
        user_id="demo_user",
        session_id="demo_session"
    )
    
    # 执行文档理解
    print("\n⏳ 正在处理文档...")
    try:
        result = await system.understand_media(context)
        
        print(f"✅ 处理完成:")
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
            preview = output.text[:150] + ("..." if len(output.text) > 150 else "")
            print(f"   内容预览: {preview}")
            
    except Exception as e:
        print(f"❌ 处理失败: {e}")


async def demo_batch_processing(system, demo_files):
    """演示批量处理功能"""
    print("\n🚀 批量处理演示:")
    
    # 逐个处理文件
    for file_name, file_path in demo_files.items():
        print(f"\n📄 处理文件: {file_name}")
        
        attachment = MediaAttachment(
            path=file_path,
            mime="text/plain",
            index=0
        )
        
        context = MediaUnderstandingContext(
            attachments=[attachment],
            config=MediaUnderstandingConfig(enabled=True),
            user_id="batch_demo"
        )
        
        try:
            result = await system.understand_media(context)
            status = "✅ 成功" if result.success else "❌ 失败"
            print(f"   {status} - {result.total_processing_time:.2f}秒")
            
            if result.outputs:
                print(f"   输出: {result.outputs[0].kind.value}")
            
        except Exception as e:
            print(f"   ❌ 错误: {e}")


async def demo_statistics(system):
    """演示统计功能"""
    print("\n📊 系统统计:")
    
    stats = system.get_system_info()["stats"]
    print(f"   总处理数: {stats['total_processed']}")
    print(f"   成功数: {stats['successful']}")
    print(f"   失败数: {stats['failed']}")
    print(f"   成功率: {(stats['successful'] / max(stats['total_processed'], 1) * 100):.1f}%")
    
    # 按类型统计
    print("\n📈 按媒体类型统计:")
    for media_type, count in stats['by_type'].items():
        print(f"   {media_type}: {count}")
    
    # 按能力统计
    print("\n🎯 按处理能力统计:")
    for capability, count in stats['by_capability'].items():
        print(f"   {capability}: {count}")


def cleanup_demo_files(temp_dir, demo_files):
    """清理演示文件"""
    print("\n🧹 清理演示文件...")
    
    # 删除演示文件
    for file_path in demo_files.values():
        try:
            os.unlink(file_path)
            print(f"   ✅ 已删除: {Path(file_path).name}")
        except FileNotFoundError:
            print(f"   ⚠️  文件不存在: {Path(file_path).name}")
    
    # 删除临时目录
    try:
        os.rmdir(temp_dir)
        print(f"   ✅ 已删除临时目录: {temp_dir}")
    except OSError:
        print(f"   ⚠️  目录非空: {temp_dir}")


async def demo_error_handling():
    """演示错误处理"""
    print("\n🚨 错误处理演示:")
    
    system = get_media_understanding_system()
    
    # 测试空附件
    print("   测试1: 空附件列表")
    context = MediaUnderstandingContext(
        attachments=[],
        config=MediaUnderstandingConfig(enabled=True)
    )
    
    result = await system.understand_media(context)
    print(f"   结果: {'成功' if result.success else '失败'} - {result.error}")
    
    # 测试禁用系统
    print("\n   测试2: 禁用系统")
    context = MediaUnderstandingContext(
        attachments=[
            MediaAttachment(path="nonexistent.txt", index=0)
        ],
        config=MediaUnderstandingConfig(enabled=False)
    )
    
    result = await system.understand_media(context)
    print(f"   结果: {'成功' if result.success else '失败'} - {result.error}")


def main():
    """主演示函数"""
    print("🎉 欢迎使用 AgentBus 媒体理解系统!")
    print("\n本演示将展示:")
    print("1. 系统基本信息和配置")
    print("2. 文档理解功能")
    print("3. 批量处理能力")
    print("4. 统计和监控")
    print("5. 错误处理机制")
    
    input("\n按 Enter 键开始演示...")
    
    # 运行演示
    asyncio.run(demo_basic_functionality())
    
    # 错误处理演示
    asyncio.run(demo_error_handling())
    
    print("\n✨ 演示完成!")
    print("\n💡 使用提示:")
    print("   - 查看 README.md 了解详细使用方法")
    print("   - 查看 example.py 了解更多示例")
    print("   - 查看 test_media_understanding.py 了解测试用例")
    print("   - 根据需要安装相应的云服务SDK")


if __name__ == "__main__":
    main()