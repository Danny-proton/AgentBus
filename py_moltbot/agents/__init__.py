"""
AI代理系统模块
AI Agent System Module

包含代理管理、RPC通信、记忆管理、链接理解、媒体理解等功能
"""

# 核心代理系统
from .base import (
    AgentType, AgentStatus, ModelProvider, ModelConfig,
    AgentCapability, AgentMetrics, AgentRequest, AgentResponse,
    BaseAgent, AgentRegistry, AgentManager,
    get_agent_manager, start_agent_manager, stop_agent_manager,
    execute_agent_request, batch_execute_agent_requests
)

# OpenAI代理
from .openai_agent import (
    OpenAIAgent, create_openai_agent, create_preconfigured_openai_agent,
    OPENAI_MODEL_CONFIGS
)

# RPC通信系统
from .rpc import (
    RPCMethod, RPCStatus, RPCRequest, RPCResponse, StreamChunk,
    RPCProcedure, RPCAgentProcedure, RPCHandler, RPCClient, RPCServer,
    RPCConnection, create_rpc_request, create_stream_request, create_batch_request
)

# 记忆管理系统
from .memory import (
    MemoryType, MemoryPriority, MemoryStatus, MemoryContent, Memory,
    MemoryStore, InMemoryStore, MemoryManager,
    get_memory_manager, create_conversation_memory, 
    create_fact_memory, create_procedure_memory
)

# 链接理解系统
from .link_understanding import (
    LinkType, ContentType, LinkMetadata, LinkContent, LinkAnalysis,
    LinkClassifier, LinkExtractor, LinkAnalyzer, LinkUnderstandingService,
    get_link_service, understand_url, batch_understand_urls
)

# 媒体理解系统
from .media_understanding import (
    MediaType, MediaFormat, ContentCategory, MediaMetadata, ContentAnalysis,
    MediaClassifier, ImageAnalyzer, AudioAnalyzer, VideoAnalyzer, 
    DocumentAnalyzer, MediaUnderstandingService,
    get_media_service, analyze_media_content, analyze_image_content,
    analyze_audio_content, analyze_video_content, batch_analyze_media_files
)

__all__ = [
    # 核心代理系统
    "AgentType",
    "AgentStatus", 
    "ModelProvider",
    "ModelConfig",
    "AgentCapability",
    "AgentMetrics",
    "AgentRequest",
    "AgentResponse",
    "BaseAgent",
    "AgentRegistry",
    "AgentManager",
    "get_agent_manager",
    "start_agent_manager",
    "stop_agent_manager",
    "execute_agent_request",
    "batch_execute_agent_requests",
    
    # OpenAI代理
    "OpenAIAgent",
    "create_openai_agent",
    "create_preconfigured_openai_agent",
    "OPENAI_MODEL_CONFIGS",
    
    # RPC通信系统
    "RPCMethod",
    "RPCStatus",
    "RPCRequest",
    "RPCResponse",
    "StreamChunk",
    "RPCProcedure",
    "RPCAgentProcedure",
    "RPCHandler",
    "RPCClient",
    "RPCServer",
    "RPCConnection",
    "create_rpc_request",
    "create_stream_request",
    "create_batch_request",
    
    # 记忆管理系统
    "MemoryType",
    "MemoryPriority",
    "MemoryStatus",
    "MemoryContent",
    "Memory",
    "MemoryStore",
    "InMemoryStore",
    "MemoryManager",
    "get_memory_manager",
    "create_conversation_memory",
    "create_fact_memory",
    "create_procedure_memory",
    
    # 链接理解系统
    "LinkType",
    "ContentType",
    "LinkMetadata",
    "LinkContent",
    "LinkAnalysis",
    "LinkClassifier",
    "LinkExtractor",
    "LinkAnalyzer",
    "LinkUnderstandingService",
    "get_link_service",
    "understand_url",
    "batch_understand_urls",
    
    # 媒体理解系统
    "MediaType",
    "MediaFormat",
    "ContentCategory",
    "MediaMetadata",
    "ContentAnalysis",
    "MediaClassifier",
    "ImageAnalyzer",
    "AudioAnalyzer",
    "VideoAnalyzer",
    "DocumentAnalyzer",
    "MediaUnderstandingService",
    "get_media_service",
    "analyze_media_content",
    "analyze_image_content",
    "analyze_audio_content",
    "analyze_video_content",
    "batch_analyze_media_files"
]