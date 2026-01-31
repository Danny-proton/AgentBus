# AgentBus 媒体理解系统

基于Moltbot架构的完整媒体理解功能实现，支持图像、音频、视频和文档的智能分析。

## 🚀 功能特性

### 媒体类型支持
- **图像理解**: 使用GPT-4V、Claude等先进模型分析图像内容
- **音频转录**: 支持Whisper、Speech-to-Text等引擎进行语音识别
- **视频理解**: 通过关键帧提取和视觉模型分析视频内容
- **文档解析**: 智能提取PDF、Word、Excel、PPT等文档的文本和结构信息

### 核心能力
- 🔍 **自动媒体检测**: 智能识别文件类型和格式
- 🧠 **多Provider支持**: 支持云端和本地多种AI服务
- ⚡ **并发处理**: 高效处理多个媒体文件
- 📊 **详细统计**: 完整的处理统计和分析报告
- 🔧 **灵活配置**: 可定制化的处理策略和参数

## 📦 系统架构

```
agentbus/media_understanding/
├── __init__.py           # 模块入口
├── types.py              # 类型定义
├── core.py               # 核心系统
├── detector.py           # 媒体检测
├── image_understanding.py  # 图像理解
├── audio_understanding.py  # 音频理解
├── video_understanding.py  # 视频理解
├── document_understanding.py # 文档理解
├── example.py            # 使用示例
└── README.md             # 本文档
```

## 🛠️ 安装依赖

```bash
# 基础依赖
pip install asyncio aiohttp pillow

# PDF处理
pip install PyPDF2 pdfplumber

# Office文档处理
pip install python-docx pandas openpyxl

# 图像处理（可选，用于OCR）
pip install pytesseract

# 语音识别（可选）
pip install SpeechRecognition
```

## 🚀 快速开始

### 1. 基本使用

```python
import asyncio
from agentbus.media_understanding import (
    MediaUnderstandingContext,
    MediaAttachment,
    MediaUnderstandingConfig,
    get_media_understanding_system
)

async def basic_example():
    # 创建系统实例
    system = get_media_understanding_system()
    
    # 创建上下文
    context = MediaUnderstandingContext(
        attachments=[
            MediaAttachment(
                path="sample.jpg",
                mime="image/jpeg",
                index=0
            )
        ],
        config=MediaUnderstandingConfig(enabled=True),
        user_id="user123"
    )
    
    # 执行理解
    result = await system.understand_media(context)
    
    print(f"成功: {result.success}")
    print(f"输出: {result.get_text_output()}")

# 运行
asyncio.run(basic_example())
```

### 2. 配置Provider

```python
from agentbus.media_understanding import (
    OpenAIImageProvider,
    OpenAIAudioProvider,
    GoogleVideoProvider
)
from agentbus.media_understanding.core import get_media_understanding_system

# 获取系统
system = get_media_understanding_system()

# 注册Provider
system.register_provider("image", OpenAIImageProvider(
    api_key="your_openai_key"
))

system.register_provider("audio", OpenAIAudioProvider(
    api_key="your_openai_key"
))

system.register_provider("video", GoogleVideoProvider(
    api_key="your_google_key"
))
```

### 3. 批量处理

```python
async def batch_example():
    system = get_media_understanding_system()
    
    # 多个附件
    attachments = [
        MediaAttachment(path="image1.jpg", index=0),
        MediaAttachment(path="audio1.wav", index=1),
        MediaAttachment(path="document1.pdf", index=2)
    ]
    
    context = MediaUnderstandingContext(
        attachments=attachments,
        config=MediaUnderstandingConfig(enabled=True)
    )
    
    result = await system.understand_media(context)
    
    # 检查各种输出
    if result.has_image_output:
        images = result.get_output_by_capability(MediaUnderstandingCapability.IMAGE)
        print(f"图像分析结果: {images}")
    
    if result.has_audio_output:
        audios = result.get_output_by_capability(MediaUnderstandingCapability.AUDIO)
        print(f"音频转录结果: {audios}")
```

## 📚 API参考

### MediaUnderstandingSystem

主要的媒体理解系统类。

#### 方法

- `understand_media(context, preferred_providers)`: 执行媒体理解
- `register_provider(type, provider)`: 注册Provider
- `get_system_info()`: 获取系统信息
- `reset_stats()`: 重置统计信息

### MediaUnderstandingContext

媒体理解上下文，包含所有必要的处理信息。

#### 属性

- `attachments`: 媒体附件列表
- `config`: 理解配置
- `user_id`: 用户ID（可选）
- `session_id`: 会话ID（可选）
- `metadata`: 附加元数据

### MediaUnderstandingResult

理解结果对象，包含所有输出和统计信息。

#### 属性

- `success`: 是否成功
- `outputs`: 输出列表
- `decisions`: 决策列表
- `applied_capabilities`: 应用的能力
- `total_processing_time`: 处理时间
- `error`: 错误信息（如果有）

#### 方法

- `has_image_output`: 是否有图像输出
- `has_audio_output`: 是否有音频输出
- `has_video_output`: 是否有视频输出
- `has_document_output`: 是否有文档输出
- `get_text_output()`: 获取所有文本输出
- `get_output_by_capability(capability)`: 根据能力获取输出

## 🔧 Provider开发

### 自定义图像Provider

```python
from agentbus.media_understanding.image_understanding import BaseImageUnderstandingProvider
from agentbus.types import ImageDescriptionRequest, ImageDescriptionResult

class MyImageProvider(BaseImageUnderstandingProvider):
    def __init__(self):
        super().__init__("my_provider")
    
    async def describe_image(self, request: ImageDescriptionRequest) -> ImageDescriptionResult:
        # 实现图像理解逻辑
        return ImageDescriptionResult(
            text="分析结果",
            model="my_model",
            confidence=0.9
        )
```

### 自定义音频Provider

```python
from agentbus.media_understanding.audio_understanding import BaseAudioUnderstandingProvider
from agentbus.types import AudioTranscriptionRequest, AudioTranscriptionResult

class MyAudioProvider(BaseAudioUnderstandingProvider):
    def __init__(self):
        super().__init__("my_audio_provider")
    
    async def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        # 实现音频转录逻辑
        return AudioTranscriptionResult(
            text="转录结果",
            model="my_model",
            language="zh-CN"
        )
```

## 📊 配置选项

### 系统配置

```python
config = {
    "enabled": True,
    "timeout": 30.0,                    # 超时时间（秒）
    "max_file_size": 10 * 1024 * 1024, # 最大文件大小（字节）
    "max_concurrent": 3                  # 最大并发数
}
```

### 能力配置

```python
# 图像配置
image_config = {
    "enabled": True,
    "prompt": "请详细描述图片内容",
    "max_tokens": 1000,
    "temperature": 0.1
}

# 音频配置
audio_config = {
    "enabled": True,
    "prompt": "请转录音频内容",
    "language": "zh-CN",
    "temperature": 0.0
}

# 视频配置
video_config = {
    "enabled": True,
    "prompt": "请分析视频内容",
    "max_duration": 300  # 最大时长（秒）
}

# 文档配置
document_config = {
    "enabled": True,
    "extract_tables": True,
    "extract_images": False,
    "max_pages": 10
}
```

## 🧪 运行示例

```bash
# 运行完整示例
python -m agentbus.media_understanding.example

# 或者直接运行
python example.py
```

## 📈 性能监控

系统提供详细的性能统计：

```python
info = system.get_system_info()
print("处理统计:", info['stats'])

# 输出示例:
# {
#     "total_processed": 10,
#     "successful": 8,
#     "failed": 2,
#     "by_type": {
#         "image": 5,
#         "audio": 3,
#         "video": 1,
#         "document": 1
#     },
#     "by_capability": {
#         "image": 5,
#         "audio": 3,
#         "video": 1,
#         "document": 1
#     }
# }
```

## 🔍 支持的文件格式

### 图像格式
- JPEG/JPG, PNG, GIF, WebP
- BMP, TIFF, SVG

### 音频格式
- MP3, WAV, OGG, AAC
- FLAC, M4A, WebM

### 视频格式
- MP4, AVI, MOV, WMV
- WebM, MKV, FLV

### 文档格式
- PDF, TXT, MD
- DOC/DOCX, XLS/XLSX, PPT/PPTX
- CSV, JSON, XML

## 🤝 贡献指南

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启Pull Request

## 📄 许可证

本项目基于MIT许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Moltbot](https://github.com/moltbot) - 架构灵感来源
- [OpenAI](https://openai.com) - GPT-4 Vision API
- [Anthropic](https://anthropic.com) - Claude API
- [Google](https://google.com) - Gemini API
- [Deepgram](https://deepgram.com) - 语音识别服务

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 [Issue](../../issues)
- 发送邮件至: [your-email@example.com]
- 查看 [Wiki](../../wiki) 获取更多文档

---

⭐ 如果这个项目对你有帮助，请给我们一个Star！