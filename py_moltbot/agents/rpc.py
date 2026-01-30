"""
RPC通信系统
RPC Communication System

为AI代理系统提供远程过程调用通信能力
"""

from typing import Dict, List, Optional, Any, Callable, Union, Awaitable, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import json
import uuid
import hashlib
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager

from ..core.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class RPCMethod(Enum):
    """RPC方法枚举"""
    SYNC_CALL = "sync_call"           # 同步调用
    ASYNC_CALL = "async_call"         # 异步调用
    STREAM_CALL = "stream_call"       # 流式调用
    BATCH_CALL = "batch_call"         # 批量调用
    SUBSCRIPTION = "subscription"      # 订阅
    HEARTBEAT = "heartbeat"           # 心跳
    ERROR = "error"                   # 错误


class RPCStatus(Enum):
    """RPC状态枚举"""
    PENDING = "pending"               # 待处理
    RUNNING = "running"               # 运行中
    COMPLETED = "completed"           # 完成
    FAILED = "failed"                 # 失败
    CANCELLED = "cancelled"           # 取消
    TIMEOUT = "timeout"               # 超时


@dataclass
class RPCRequest:
    """RPC请求"""
    id: str
    method: RPCMethod
    agent_id: str
    procedure: str
    params: Dict[str, Any]
    timeout: float = 60.0
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_request_hash(self) -> str:
        """获取请求哈希"""
        content = f"{self.agent_id}:{self.procedure}:{json.dumps(self.params, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class RPCResponse:
    """RPC响应"""
    request_id: str
    status: RPCStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def success(cls, request_id: str, result: Any, **kwargs) -> 'RPCResponse':
        """创建成功响应"""
        return cls(
            request_id=request_id,
            status=RPCStatus.COMPLETED,
            result=result,
            **kwargs
        )
    
    @classmethod
    def error(cls, request_id: str, error: str, **kwargs) -> 'RPCResponse':
        """创建错误响应"""
        return cls(
            request_id=request_id,
            status=RPCStatus.FAILED,
            error=error,
            **kwargs
        )


@dataclass
class StreamChunk:
    """流式数据块"""
    request_id: str
    chunk_id: str
    data: Any
    sequence: int
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class RPCProcedure(ABC):
    """RPC过程抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """过程名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """过程描述"""
        pass
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行过程"""
        pass


class RPCAgentProcedure(RPCProcedure):
    """代理RPC过程"""
    
    def __init__(self, name: str, agent_method: Callable, description: str = ""):
        self._name = name
        self._agent_method = agent_method
        self._description = description
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行代理方法"""
        if asyncio.iscoroutinefunction(self._agent_method):
            return await self._agent_method(**params)
        else:
            return self._agent_method(**params)


class RPCHandler:
    """RPC处理器"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = get_logger(f"{self.__class__.__module__}.{agent_id}")
        
        # 注册的过程
        self.procedures: Dict[str, RPCProcedure] = {}
        
        # 活跃的调用
        self.active_calls: Dict[str, asyncio.Task] = {}
        
        # 流式订阅
        self.stream_subscriptions: Dict[str, asyncio.Queue] = {}
    
    def register_procedure(self, procedure: RPCProcedure) -> None:
        """注册RPC过程"""
        self.procedures[procedure.name] = procedure
        self.logger.debug("RPC procedure registered", 
                         procedure=procedure.name,
                         description=procedure.description)
    
    def register_agent_methods(self, agent_instance) -> None:
        """注册代理实例的方法"""
        # 获取所有公共方法
        for attr_name in dir(agent_instance):
            if not attr_name.startswith('_') and callable(getattr(agent_instance, attr_name)):
                attr = getattr(agent_instance, attr_name)
                if callable(attr):
                    procedure = RPCAgentProcedure(
                        name=attr_name,
                        agent_method=attr,
                        description=f"Agent method: {attr_name}"
                    )
                    self.register_procedure(procedure)
    
    async def handle_request(self, request: RPCRequest) -> RPCResponse:
        """处理RPC请求"""
        start_time = datetime.now()
        
        try:
            # 查找过程
            if request.procedure not in self.procedures:
                return RPCResponse.error(
                    request.id,
                    f"Procedure '{request.procedure}' not found"
                )
            
            procedure = self.procedures[request.procedure]
            
            # 执行过程
            result = await asyncio.wait_for(
                procedure.execute(request.params),
                timeout=request.timeout
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return RPCResponse.success(
                request_id=request.id,
                result=result,
                execution_time=execution_time
            )
            
        except asyncio.TimeoutError:
            return RPCResponse.error(
                request.id,
                f"Procedure '{request.procedure}' timed out after {request.timeout}s"
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error("RPC procedure execution failed", 
                            procedure=request.procedure,
                            error=str(e))
            return RPCResponse.error(
                request.id,
                f"Procedure execution failed: {str(e)}",
                execution_time=execution_time
            )
    
    async def handle_stream_request(
        self, 
        request: RPCRequest
    ) -> AsyncIterator[StreamChunk]:
        """处理流式RPC请求"""
        procedure_name = request.procedure
        request_id = request.id
        
        # 查找过程
        if procedure_name not in self.procedures:
            yield StreamChunk(
                request_id=request_id,
                chunk_id=str(uuid.uuid4()),
                data=f"Procedure '{procedure_name}' not found",
                sequence=0,
                is_final=True
            )
            return
        
        procedure = self.procedures[procedure_name]
        
        try:
            # 执行过程并流式返回结果
            if hasattr(procedure.execute, '__call__'):
                result = await asyncio.wait_for(
                    procedure.execute(request.params),
                    timeout=request.timeout
                )
                
                # 如果结果是异步迭代器
                if hasattr(result, '__aiter__'):
                    sequence = 0
                    async for chunk_data in result:
                        yield StreamChunk(
                            request_id=request_id,
                            chunk_id=str(uuid.uuid4()),
                            data=chunk_data,
                            sequence=sequence,
                            is_final=False
                        )
                        sequence += 1
                else:
                    # 单个结果
                    yield StreamChunk(
                        request_id=request_id,
                        chunk_id=str(uuid.uuid4()),
                        data=result,
                        sequence=0,
                        is_final=True
                    )
            
        except asyncio.TimeoutError:
            yield StreamChunk(
                request_id=request_id,
                chunk_id=str(uuid.uuid4()),
                data=f"Procedure '{procedure_name}' timed out",
                sequence=0,
                is_final=True
            )
        except Exception as e:
            self.logger.error("RPC stream execution failed", 
                            procedure=procedure_name,
                            error=str(e))
            yield StreamChunk(
                request_id=request_id,
                chunk_id=str(uuid.uuid4()),
                data=f"Stream execution failed: {str(e)}",
                sequence=0,
                is_final=True
            )


class RPCClient:
    """RPC客户端"""
    
    def __init__(self, agent_id: str, connection):
        self.agent_id = agent_id
        self.connection = connection
        self.logger = get_logger(f"{self.__class__.__module__}.{agent_id}")
        
        # 等待响应的调用
        self.pending_calls: Dict[str, asyncio.Future] = {}
        
        # 流式调用
        self.stream_calls: Dict[str, asyncio.Queue] = {}
        
        # 请求超时时间
        self.default_timeout = 60.0
    
    async def call(
        self,
        procedure: str,
        params: Dict[str, Any] = None,
        timeout: float = None,
        priority: int = 0
    ) -> RPCResponse:
        """发起RPC调用"""
        params = params or {}
        timeout = timeout or self.default_timeout
        request_id = str(uuid.uuid4())
        
        request = RPCRequest(
            id=request_id,
            method=RPCMethod.SYNC_CALL,
            agent_id=self.agent_id,
            procedure=procedure,
            params=params,
            timeout=timeout,
            priority=priority
        )
        
        # 创建future等待响应
        future = asyncio.Future()
        self.pending_calls[request_id] = future
        
        try:
            # 发送请求
            await self.connection.send_request(request)
            
            # 等待响应
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            self.logger.warning("RPC call timeout", 
                              procedure=procedure,
                              timeout=timeout)
            return RPCResponse.error(request_id, "Call timeout")
        except Exception as e:
            self.logger.error("RPC call failed", 
                            procedure=procedure,
                            error=str(e))
            return RPCResponse.error(request_id, f"Call failed: {str(e)}")
        finally:
            # 清理pending调用
            self.pending_calls.pop(request_id, None)
    
    async def stream_call(
        self,
        procedure: str,
        params: Dict[str, Any] = None,
        timeout: float = None
    ) -> AsyncIterator[Any]:
        """发起流式RPC调用"""
        params = params or {}
        timeout = timeout or self.default_timeout
        request_id = str(uuid.uuid4())
        
        request = RPCRequest(
            id=request_id,
            method=RPCMethod.STREAM_CALL,
            agent_id=self.agent_id,
            procedure=procedure,
            params=params,
            timeout=timeout
        )
        
        # 创建队列收集流式数据
        stream_queue = asyncio.Queue()
        self.stream_calls[request_id] = stream_queue
        
        try:
            # 发送请求
            await self.connection.send_request(request)
            
            # 收集流式数据
            while True:
                try:
                    chunk = await asyncio.wait_for(stream_queue.get(), timeout=1.0)
                    
                    if chunk.is_final:
                        break
                    
                    yield chunk.data
                    
                except asyncio.TimeoutError:
                    continue
                    
        except Exception as e:
            self.logger.error("RPC stream call failed", 
                            procedure=procedure,
                            error=str(e))
            yield f"Stream call failed: {str(e)}"
        finally:
            # 清理流式调用
            self.stream_calls.pop(request_id, None)
    
    async def batch_call(
        self,
        calls: List[Dict[str, Any]],
        timeout: float = None
    ) -> List[RPCResponse]:
        """发起批量RPC调用"""
        timeout = timeout or self.default_timeout
        
        tasks = []
        for call in calls:
            task = asyncio.create_task(
                self.call(
                    call["procedure"],
                    call.get("params", {}),
                    call.get("timeout", timeout),
                    call.get("priority", 0)
                )
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                processed_responses.append(
                    RPCResponse.error(str(uuid.uuid4()), str(response))
                )
            else:
                processed_responses.append(response)
        
        return processed_responses
    
    async def subscribe(
        self,
        event_type: str,
        params: Dict[str, Any] = None
    ) -> AsyncIterator[Any]:
        """订阅事件"""
        params = params or {}
        request_id = str(uuid.uuid4())
        
        request = RPCRequest(
            id=request_id,
            method=RPCMethod.SUBSCRIPTION,
            agent_id=self.agent_id,
            procedure="subscribe",
            params={
                "event_type": event_type,
                "event_params": params
            }
        )
        
        # 创建队列收集事件
        event_queue = asyncio.Queue()
        self.stream_calls[request_id] = event_queue
        
        try:
            # 发送订阅请求
            await self.connection.send_request(request)
            
            # 收集事件
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                    yield event
                except asyncio.TimeoutError:
                    continue
                    
        except Exception as e:
            self.logger.error("RPC subscription failed", 
                            event_type=event_type,
                            error=str(e))
        finally:
            # 清理订阅
            self.stream_calls.pop(request_id, None)
    
    def handle_response(self, response: RPCResponse) -> None:
        """处理响应"""
        if response.request_id in self.pending_calls:
            future = self.pending_calls[response.request_id]
            future.set_result(response)
    
    def handle_stream_chunk(self, chunk: StreamChunk) -> None:
        """处理流式数据块"""
        if chunk.request_id in self.stream_calls:
            queue = self.stream_calls[chunk.request_id]
            queue.put_nowait(chunk)


class RPCServer:
    """RPC服务器"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = get_logger(f"{self.__class__.__module__}.{agent_id}")
        
        # 处理器
        self.handler = RPCHandler(agent_id)
        
        # 活跃连接
        self.connections: Dict[str, Any] = {}
        
        # 消息队列
        self.message_queue = asyncio.Queue()
    
    def register_agent(self, agent_instance) -> None:
        """注册代理实例"""
        self.handler.register_agent_methods(agent_instance)
        self.logger.info("Agent registered for RPC", 
                        agent_id=self.agent_id,
                        procedures=list(self.handler.procedures.keys()))
    
    def register_procedure(self, procedure: RPCProcedure) -> None:
        """注册RPC过程"""
        self.handler.register_procedure(procedure)
    
    async def start(self) -> None:
        """启动RPC服务器"""
        # 创建工作协程
        asyncio.create_task(self._message_processor())
        self.logger.info("RPC server started", agent_id=self.agent_id)
    
    async def stop(self) -> None:
        """停止RPC服务器"""
        # 清理活跃连接
        self.connections.clear()
        self.logger.info("RPC server stopped", agent_id=self.agent_id)
    
    async def handle_request(self, request: RPCRequest) -> RPCResponse:
        """处理RPC请求"""
        return await self.handler.handle_request(request)
    
    async def handle_stream_request(
        self, 
        request: RPCRequest
    ) -> AsyncIterator[StreamChunk]:
        """处理流式RPC请求"""
        async for chunk in self.handler.handle_stream_request(request):
            yield chunk
    
    def add_connection(self, connection_id: str, connection) -> None:
        """添加连接"""
        self.connections[connection_id] = connection
        self.logger.debug("RPC connection added", 
                        connection_id=connection_id,
                        agent_id=self.agent_id)
    
    def remove_connection(self, connection_id: str) -> None:
        """移除连接"""
        self.connections.pop(connection_id, None)
        self.logger.debug("RPC connection removed", 
                        connection_id=connection_id,
                        agent_id=self.agent_id)
    
    async def broadcast(self, event: str, data: Any) -> None:
        """广播事件"""
        # 这里可以向所有连接广播事件
        # 实际实现需要根据连接类型处理
        self.logger.debug("Broadcasting event", 
                        event=event,
                        agent_id=self.agent_id)
    
    async def _message_processor(self) -> None:
        """消息处理器"""
        while True:
            try:
                # 处理队列中的消息
                message = await self.message_queue.get()
                
                # 这里可以处理心跳、监控等消息
                if message.get("type") == "heartbeat":
                    await self._handle_heartbeat(message)
                    
            except Exception as e:
                self.logger.error("Message processor error", error=str(e))
    
    async def _handle_heartbeat(self, message: Dict[str, Any]) -> None:
        """处理心跳"""
        connection_id = message.get("connection_id")
        if connection_id and connection_id in self.connections:
            # 发送心跳响应
            # 这里需要根据连接类型发送响应
            pass


class RPCConnection(ABC):
    """RPC连接抽象基类"""
    
    @abstractmethod
    async def send_request(self, request: RPCRequest) -> None:
        """发送请求"""
        pass
    
    @abstractmethod
    async def send_response(self, response: RPCResponse) -> None:
        """发送响应"""
        pass
    
    @abstractmethod
    async def send_stream_chunk(self, chunk: StreamChunk) -> None:
        """发送流式数据"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        pass


# 便利函数
def create_rpc_request(
    agent_id: str,
    procedure: str,
    params: Dict[str, Any] = None,
    timeout: float = 60.0
) -> RPCRequest:
    """创建RPC请求"""
    return RPCRequest(
        id=str(uuid.uuid4()),
        method=RPCMethod.SYNC_CALL,
        agent_id=agent_id,
        procedure=procedure,
        params=params or {},
        timeout=timeout
    )


def create_stream_request(
    agent_id: str,
    procedure: str,
    params: Dict[str, Any] = None,
    timeout: float = 60.0
) -> RPCRequest:
    """创建流式RPC请求"""
    return RPCRequest(
        id=str(uuid.uuid4()),
        method=RPCMethod.STREAM_CALL,
        agent_id=agent_id,
        procedure=procedure,
        params=params or {},
        timeout=timeout
    )


def create_batch_request(
    agent_id: str,
    calls: List[Dict[str, Any]],
    timeout: float = 60.0
) -> RPCRequest:
    """创建批量RPC请求"""
    return RPCRequest(
        id=str(uuid.uuid4()),
        method=RPCMethod.BATCH_CALL,
        agent_id=agent_id,
        procedure="batch_call",
        params={"calls": calls},
        timeout=timeout
    )