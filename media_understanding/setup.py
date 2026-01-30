#!/usr/bin/env python3
"""
AgentBus 媒体理解系统安装配置
"""

from setuptools import setup, find_packages

# 读取README文件
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# 读取requirements文件
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="agentbus-media-understanding",
    version="1.0.0",
    author="AgentBus Team",
    author_email="contact@agentbus.com",
    description="基于Moltbot架构的完整媒体理解功能",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/agentbus/media-understanding",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Text Processing :: General",
    ],
    python_requires=">=3.8",
    install_requires=[
        # 核心依赖
        "aiohttp>=3.8.0",
        "Pillow>=9.0.0",
        
        # 文档处理
        "PyPDF2>=3.0.0",
        "python-docx>=0.8.11",
        "pandas>=1.5.0",
        
        # 图像处理
        "numpy>=1.21.0",
        
        # 文本处理
        "beautifulsoup4>=4.11.0",
        
        # 异步支持
        "asyncio-mqtt>=0.11.0",
        
        # 日志
        "loguru>=0.6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "mypy>=1.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "jupyter>=1.0.0",
        ],
        "ocr": [
            "pytesseract>=0.3.10",
        ],
        "audio": [
            "SpeechRecognition>=3.10.0",
            "pydub>=0.25.0",
        ],
        "video": [
            "moviepy>=1.0.3",
            "ffmpeg-python>=0.2.0",
        ],
        "cloud": [
            "google-generativeai>=0.3.0",
            "openai>=0.28.0",
            "anthropic>=0.3.0",
        ],
        "excel": [
            "openpyxl>=3.0.10",
        ],
        "all": [
            # 包含所有可选依赖
            "pytesseract>=0.3.10",
            "SpeechRecognition>=3.10.0",
            "pydub>=0.25.0",
            "moviepy>=1.0.3",
            "ffmpeg-python>=0.2.0",
            "google-generativeai>=0.3.0",
            "openai>=0.28.0",
            "anthropic>=0.3.0",
            "openpyxl>=3.0.10",
        ],
    },
    entry_points={
        "console_scripts": [
            "agentbus-media=agentbus.media_understanding.example:main",
        ],
    },
    keywords=[
        "media-understanding",
        "image-analysis",
        "audio-transcription", 
        "video-analysis",
        "document-processing",
        "ai",
        "ml",
        "computer-vision",
        "nlp",
        "agentbus",
        "moltbot",
    ],
    project_urls={
        "Bug Reports": "https://github.com/agentbus/media-understanding/issues",
        "Source": "https://github.com/agentbus/media-understanding",
        "Documentation": "https://github.com/agentbus/media-understanding/wiki",
    },
    include_package_data=True,
    package_data={
        "agentbus.media_understanding": [
            "*.md",
            "*.txt",
            "*.yml",
            "*.yaml",
        ],
    },
)