"""
Gateway Base Handler

基础处理器类，为所有网关处理器提供通用功能
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from ..protocol import RequestFrame, ResponseFrame, EventFrame, ProtocolHandler, ErrorCode


class BaseHandler(ABC):
    """基础处理器"""
    
    def __init__(self, protocol_handler: ProtocolHandler):
        self.protocol_handler = protocol_handler
    
    @abstractmethod
    async def handle_request(self, frame: RequestFrame) -> ResponseFrame:
        """处理请求"""
        pass
    
    async def handle_event(self, frame: EventFrame) -> Optional[EventFrame]:
        """处理事件"""
        return None
    
    def create_success_response(self, frame: RequestFrame, payload: Optional[Dict] = None) -> ResponseFrame:
        """创建成功响应"""
        return self.protocol_handler.create_response(frame.id, ok=True, payload=payload)
    
    def create_error_response(self, frame: RequestFrame, code: ErrorCode, message: str, details: Optional[Dict] = None) -> ResponseFrame:
        """创建错误响应"""
        return self.protocol_handler.create_error_response(frame.id, code, message, details)