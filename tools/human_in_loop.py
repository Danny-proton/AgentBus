"""
Human-in-the-Loop 工具
核心设计：把人类当作一个强大的工具，支持多种操作模式
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from uuid import uuid4
from dataclasses import dataclass, field, asdict
from enum import Enum


logger = logging.getLogger(__name__)


class HumanActionType(Enum):
    """人类操作类型"""
    FEEDBACK = "feedback"           # 人类提出意见/建议
    BASH = "bash"                   # 人类执行bash命令
    DESKTOP = "desktop"             # 人类执行桌面操作
    BROWSER = "browser"             # 人类执行浏览器操作
    REVIEW = "review"               # 人类审查代码/内容
    APPROVE = "approve"             # 人类批准操作


class HumanOperationStatus(Enum):
    """操作状态"""
    PENDING = "pending"             # 待处理
    IN_PROGRESS = "in_progress"     # 进行中
    COMPLETED = "completed"         # 已完成
    CANCELLED = "cancelled"         # 已取消
    FAILED = "failed"               # 失败


@dataclass
class HumanOperation:
    """人类操作记录"""
    operation_id: str
    agent_id: str                    # 调用人类的 Agent ID
    action_type: HumanActionType     # 操作类型
    description: str                 # 操作描述
    request_params: Dict[str, Any]   # 请求参数
    status: HumanOperationStatus     # 状态
    
    # 执行信息
    human_input: Optional[str] = None  # 人类输入
    execution_result: Optional[str] = None  # 执行结果
    
    # 总结信息（Agent需要记录）
    summary: Optional[str] = None       # 操作总结
    key_findings: List[str] = field(default_factory=list)  # 关键发现
    
    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HumanCallbackManager:
    """
    人类回调管理器
    用于处理桌面操作和浏览器操作的结果总结
    （用户会提供具体的总结组件，这里留好接口）
    """
    
    def __init__(self):
        self._desktop_summarizer: Optional[Callable] = None
        self._browser_summarizer: Optional[Callable] = None
    
    def set_desktop_summarizer(self, callback: Callable[[Dict[str, Any]], str]):
        """
        设置桌面操作总结回调
        
        Args:
            callback: 接收桌面操作结果，返回总结文本
        """
        self._desktop_summarizer = callback
    
    def set_browser_summarizer(self, callback: Callable[[Dict[str, Any]], str]):
        """
        设置浏览器操作总结回调
        
        Args:
            callback: 接收浏览器操作结果，返回总结文本
        """
        self._browser_summarizer = callback
    
    async def summarize_desktop_action(self, action_result: Dict[str, Any]) -> str:
        """
        总结桌面操作结果
        
        Args:
            action_result: 桌面操作结果
        
        Returns:
            str: 总结文本
        """
        if self._desktop_summarizer:
            return self._desktop_summarizer(action_result)
        
        # 默认总结逻辑
        summary = "桌面操作执行完成"
        if "screenshot" in action_result:
            summary += f"，已截取屏幕截图"
        if "clicked_element" in action_result:
            summary += f"，点击了元素: {action_result['clicked_element']}"
        if "window_focus" in action_result:
            summary += f"，切换窗口焦点"
        
        return summary
    
    async def summarize_browser_action(self, action_result: Dict[str, Any]) -> str:
        """
        总结浏览器操作结果
        
        Args:
            action_result: 浏览器操作结果
        
        Returns:
            str: 总结文本
        """
        if self._browser_summarizer:
            return self._browser_summarizer(action_result)
        
        # 默认总结逻辑
        summary = "浏览器操作执行完成"
        if "url" in action_result:
            summary += f"，访问了: {action_result['url']}"
        if "page_title" in action_result:
            summary += f"，页面标题: {action_result['page_title']}"
        if "clicked_element" in action_result:
            summary += f"，点击了: {action_result['clicked_element']}"
        if "extracted_content" in action_result:
            summary += f"，提取了内容"
        
        return summary


class HumanInTheLoopManager:
    """
    人在回路管理器
    核心设计：把人类当作一个强大的工具，支持多种操作模式
    """
    
    def __init__(self):
        self._operations: Dict[str, HumanOperation] = {}
        self._operation_queue: List[str] = []  # 待处理的操作队列
        self._lock = asyncio.Lock()
        
        # WebSocket 连接用于通知前端
        self._websocket = None
        
        # 回调管理器
        self._callback_manager = HumanCallbackManager()
        
        # 操作历史（用于记忆）
        self._operation_history: List[HumanOperation] = []
        self._max_history = 100
    
    def set_websocket(self, websocket):
        """设置 WebSocket 连接"""
        self._websocket = websocket
    
    def get_callback_manager(self) -> HumanCallbackManager:
        """获取回调管理器"""
        return self._callback_manager
    
    async def invoke_human(
        self,
        agent_id: str,
        action_type: HumanActionType,
        description: str,
        request_params: Dict[str, Any],
        timeout: float = 300.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> HumanOperation:
        """
        调用人类（就像调用工具一样）
        
        Args:
            agent_id: 调用人类的 Agent ID
            action_type: 操作类型
            description: 操作描述
            request_params: 请求参数
            timeout: 超时时间
            metadata: 元数据
        
        Returns:
            HumanOperation: 操作记录
        """
        operation_id = str(uuid4())[:12]
        
        operation = HumanOperation(
            operation_id=operation_id,
            agent_id=agent_id,
            action_type=action_type,
            description=description,
            request_params=request_params,
            status=HumanOperationStatus.PENDING,
            metadata=metadata or {}
        )
        
        async with self._lock:
            self._operations[operation_id] = operation
            self._operation_queue.append(operation_id)
        
        # 通过 WebSocket 通知前端
        await self._notify_human(operation)
        
        logger.info(f"Human invoked [ID: {operation_id}]: {description}")
        
        return operation
    
    async def _notify_human(self, operation: HumanOperation):
        """通知人类有新的请求"""
        if self._websocket:
            try:
                await self._websocket.send_json({
                    "type": "human_invocation",
                    "operation_id": operation.operation_id,
                    "action_type": operation.action_type.value,
                    "description": operation.description,
                    "request_params": operation.request_params,
                    "context": {
                        "agent_id": operation.agent_id,
                        "created_at": operation.created_at
                    }
                })
            except Exception as e:
                logger.error(f"Failed to notify human: {e}")
    
    async def submit_human_input(
        self,
        operation_id: str,
        human_input: str,
        action_type: HumanActionType = HumanActionType.FEEDBACK
    ) -> bool:
        """
        提交人类输入
        
        Args:
            operation_id: 操作 ID
            human_input: 人类输入
            action_type: 操作类型
        
        Returns:
            bool: 是否成功
        """
        async with self._lock:
            if operation_id not in self._operations:
                return False
            
            operation = self._operations[operation_id]
            operation.human_input = human_input
            operation.status = HumanOperationStatus.IN_PROGRESS
            operation.started_at = datetime.now().isoformat()
        
        logger.info(f"Human input received [ID: {operation_id}]: {human_input[:100]}")
        
        return True
    
    async def complete_operation(
        self,
        operation_id: str,
        execution_result: Optional[str] = None,
        summary: Optional[str] = None,
        key_findings: Optional[List[str]] = None
    ) -> bool:
        """
        完成操作（人类操作完成后调用）
        
        Args:
            operation_id: 操作 ID
            execution_result: 执行结果
            summary: 总结
            key_findings: 关键发现
        
        Returns:
            bool: 是否成功
        """
        async with self._lock:
            if operation_id not in self._operations:
                return False
            
            operation = self._operations[operation_id]
            operation.execution_result = execution_result
            operation.summary = summary
            operation.key_findings = key_findings or []
            operation.status = HumanOperationStatus.COMPLETED
            operation.completed_at = datetime.now().isoformat()
            
            # 移出队列
            if operation_id in self._operation_queue:
                self._operation_queue.remove(operation_id)
            
            # 添加到历史
            self._operation_history.append(operation)
            if len(self._operation_history) > self._max_history:
                self._operation_history = self._operation_history[-self._max_history:]
        
        logger.info(f"Operation completed [ID: {operation_id}]: {summary or 'Done'}")
        
        return True
    
    async def get_operation_result(
        self,
        operation_id: str,
        timeout: float = 300.0
    ) -> Optional[HumanOperation]:
        """
        获取操作结果（等待完成）
        
        Args:
            operation_id: 操作 ID
            timeout: 超时时间
        
        Returns:
            HumanOperation: 操作记录，None 表示超时
        """
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            async with self._lock:
                operation = self._operations.get(operation_id)
                if operation and operation.status == HumanOperationStatus.COMPLETED:
                    return operation
            
            await asyncio.sleep(0.5)
        
        logger.warning(f"Operation timeout [ID: {operation_id}]")
        return None
    
    def get_operation(self, operation_id: str) -> Optional[HumanOperation]:
        """获取操作记录"""
        return self._operations.get(operation_id)
    
    def get_pending_operations(self) -> List[HumanOperation]:
        """获取待处理的操作"""
        async with self._lock:
            return [
                self._operations[op_id]
                for op_id in self._operation_queue
                if op_id in self._operations
            ]
    
    def get_operation_history(
        self,
        agent_id: Optional[str] = None,
        action_type: Optional[HumanActionType] = None,
        limit: int = 20
    ) -> List[HumanOperation]:
        """
        获取操作历史
        
        Args:
            agent_id: 按 Agent 过滤
            action_type: 按操作类型过滤
            limit: 返回数量
        
        Returns:
            List[HumanOperation]: 操作历史
        """
        history = self._operation_history
        
        if agent_id:
            history = [op for op in history if op.agent_id == agent_id]
        
        if action_type:
            history = [op for op in history if op.action_type == action_type]
        
        return history[-limit:]
    
    def summarize_human_actions(
        self,
        agent_id: Optional[str] = None,
        since_minutes: Optional[int] = None
    ) -> str:
        """
        总结人类的操作（供 Agent 参考）
        
        Args:
            agent_id: 指定 Agent 的操作
            since_minutes: 最近多少分钟
        
        Returns:
            str: 总结文本
        """
        history = self.get_operation_history(agent_id=agent_id)
        
        if not history:
            return "近期无人类操作记录"
        
        # 按时间分组
        summary_lines = ["## 近期人类操作总结\n"]
        
        for op in reversed(history):
            status_icon = "✅" if op.status == HumanOperationStatus.COMPLETED else "⏳"
            summary_lines.append(
                f"{status_icon} [{op.action_type.value}] {op.description}"
            )
            if op.summary:
                summary_lines.append(f"   总结: {op.summary}")
            if op.key_findings:
                for finding in op.key_findings[:3]:
                    summary_lines.append(f"   发现: {finding}")
            summary_lines.append("")
        
        return "\n".join(summary_lines)
    
    async def cancel_operation(self, operation_id: str) -> bool:
        """取消操作"""
        async with self._lock:
            if operation_id not in self._operations:
                return False
            
            operation = self._operations[operation_id]
            operation.status = HumanOperationStatus.CANCELLED
            operation.completed_at = datetime.now().isoformat()
            
            if operation_id in self._operation_queue:
                self._operation_queue.remove(operation_id)
        
        return True
    
    def is_main_agent(self) -> bool:
        """此工具仅主 Agent 可用"""
        return True


class HumanTool(BaseTool):
    """
    人类工具
    把人类当作一个强大的工具，支持多种操作模式：
    - 提出意见/建议
    - 执行bash命令
    - 执行桌面操作
    - 执行浏览器操作
    - 审查代码/内容
    - 批准操作
    """
    
    name = "human"
    description = """Invoke human assistance as a powerful tool.
Use this tool when you need:
- Human feedback or suggestions on your approach
- Human to execute bash commands manually
- Human to perform desktop operations (click, type, etc.)
- Human to perform browser operations (navigate, click, extract)
- Human to review code or content you created
- Human to approve critical operations

The human is a powerful collaborator who can:
- Provide expert feedback on your work
- Execute complex bash commands you can't
- Perform GUI operations you can't automate
- Browse websites and extract information
- Review and approve your code before production

After human completes their action, summarize what they did and continue your work.
The human's input will be remembered for context."""
    
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "invoke",           # 调用人类
                    "check_result",     # 检查结果
                    "get_summary",      # 获取总结
                    "list_pending",     # 列出待处理
                    "cancel"            # 取消
                ],
                "description": "Operation type"
            },
            "action_type": {
                "type": "string",
                "enum": [
                    "feedback",     # 提出意见
                    "bash",         # 执行bash
                    "desktop",      # 桌面操作
                    "browser",      # 浏览器操作
                    "review",       # 审查
                    "approve"       # 批准
                ],
                "description": "Type of human action needed"
            },
            "description": {
                "type": "string",
                "description": "Description of what you need the human to do"
            },
            "details": {
                "type": "object",
                "description": "Detailed parameters for the human action"
            },
            "operation_id": {
                "type": "string",
                "description": "Operation ID (for check_result/cancel actions)"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 300
            },
            "context": {
                "type": "object",
                "description": "Additional context for the human"
            }
        },
        "required": ["action"]
    }
    
    def __init__(
        self,
        environment,
        human_manager: HumanInTheLoopManager,
        is_main_agent: bool = False,
        agent_id: str = "main_agent"
    ):
        super().__init__(environment)
        self.human_manager = human_manager
        self._is_main_agent = is_main_agent
        self._agent_id = agent_id
        
        # 如果不是主 Agent，禁用工具
        if not self._is_main_agent:
            self._enabled = False
    
    async def execute(
        self,
        action: str,
        action_type: str = "feedback",
        description: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        operation_id: Optional[str] = None,
        timeout: int = 300,
        context: Optional[Dict[str, Any]] = None
    ) -> "ToolResult":
        """执行人类工具调用"""
        try:
            from tools.base import ToolResult
            
            if action == "invoke":
                if not self._is_main_agent:
                    return ToolResult(
                        success=False,
                        content="",
                        error="human tool is only available to main agent"
                    )
                
                if not description:
                    return ToolResult(
                        success=False,
                        content="",
                        error="description is required for invoke action"
                    )
                
                # 转换 action_type
                type_map = {
                    "feedback": HumanActionType.FEEDBACK,
                    "bash": HumanActionType.BASH,
                    "desktop": HumanActionType.DESKTOP,
                    "browser": HumanActionType.BROWSER,
                    "review": HumanActionType.REVIEW,
                    "approve": HumanActionType.APPROVE
                }
                human_type = type_map.get(action_type, HumanActionType.FEEDBACK)
                
                # 构建请求参数
                request_params = details or {}
                request_params["description"] = description
                if context:
                    request_params["context"] = context
                
                # 调用人类
                operation = await self.human_manager.invoke_human(
                    agent_id=self._agent_id,
                    action_type=human_type,
                    description=description,
                    request_params=request_params,
                    timeout=timeout,
                    metadata=context
                )
                
                # 根据操作类型给出不同提示
                type_hint = {
                    HumanActionType.FEEDBACK: "人类将提供意见/建议",
                    HumanActionType.BASH: "人类将手动执行bash命令",
                    HumanActionType.DESKTOP: "人类将执行桌面操作",
                    HumanActionType.BROWSER: "人类将执行浏览器操作",
                    HumanActionType.REVIEW: "人类将审查代码/内容",
                    HumanActionType.APPROVE: "人类将批准操作"
                }
                
                return ToolResult(
                    success=True,
                    content=f"🧑 人类工具已调用 [ID: {operation.operation_id}]\n"
                            f"类型: {type_hint.get(human_type, '协助')}\n"
                            f"描述: {description}\n\n"
                            f"✅ 人类完成操作后，请使用 'check_result' 检查结果，\n"
                            f"然后总结人类的行为，继续你的工作。"
                )
            
            elif action == "check_result":
                if not operation_id:
                    return ToolResult(
                        success=False,
                        content="",
                        error="operation_id is required for check_result action"
                    )
                
                operation = self.human_manager.get_operation(operation_id)
                
                if not operation:
                    return ToolResult(
                        success=True,
                        content=f"未找到操作: {operation_id}"
                    )
                
                if operation.status.value == "pending":
                    return ToolResult(
                        success=True,
                        content=f"⏳ 等待人类响应 [ID: {operation_id}]\n"
                                f"类型: {operation.action_type.value}\n"
                                f"描述: {operation.description}"
                    )
                
                elif operation.status.value == "in_progress":
                    return ToolResult(
                        success=True,
                        content=f"🔄 人类正在操作中 [ID: {operation_id}]\n"
                                f"输入: {operation.human_input or '处理中...'}"
                    )
                
                elif operation.status.value == "completed":
                    # 生成总结提示
                    summary_prompt = ""
                    if operation.summary:
                        summary_prompt = f"\n\n人类总结: {operation.summary}"
                    
                    if operation.key_findings:
                        summary_prompt += f"\n关键发现:\n" + "\n".join(
                            f"- {f}" for f in operation.key_findings
                        )
                    
                    return ToolResult(
                        success=True,
                        content=f"✅ 人类操作完成 [ID: {operation_id}]\n\n"
                                f"类型: {operation.action_type.value}\n"
                                f"描述: {operation.description}\n"
                                f"人类输入: {operation.human_input or 'N/A'}\n"
                                f"执行结果: {operation.execution_result or 'N/A'}"
                                f"{summary_prompt}\n\n"
                                f"💡 请总结人类的行为，将总结添加到上下文，然后继续你的工作。"
                    )
                
                elif operation.status.value == "cancelled":
                    return ToolResult(
                        success=True,
                        content=f"❌ 操作已取消 [ID: {operation_id}]"
                    )
            
            elif action == "get_summary":
                # 获取最近的总结
                history = self.human_manager.get_operation_history(
                    agent_id=self._agent_id if self._is_main_agent else None,
                    limit=10
                )
                
                if not history:
                    return ToolResult(
                        success=True,
                        content="近期无人类操作记录"
                    )
                
                summary = self.human_manager.summarize_human_actions(
                    agent_id=self._agent_id if self._is_main_agent else None
                )
                
                return ToolResult(
                    success=True,
                    content=summary
                )
            
            elif action == "list_pending":
                pending = self.human_manager.get_pending_operations()
                
                if not pending:
                    return ToolResult(
                        success=True,
                        content="✅ 无待处理的人类操作"
                    )
                
                content = f"⏳ 待处理的人类操作 ({len(pending)}):\n\n"
                for op in pending:
                    content += f"[{op.operation_id}] {op.description}\n"
                    content += f"   类型: {op.action_type.value}\n"
                    content += f"   创建时间: {op.created_at}\n\n"
                
                return ToolResult(success=True, content=content)
            
            elif action == "cancel":
                if not operation_id:
                    return ToolResult(
                        success=False,
                        content="",
                        error="operation_id is required for cancel action"
                    )
                
                success = await self.human_manager.cancel_operation(operation_id)
                
                if success:
                    return ToolResult(
                        success=True,
                        content=f"✅ 操作已取消: {operation_id}"
                    )
                else:
                    return ToolResult(
                        success=True,
                        content=f"❌ 操作不存在或已完成: {operation_id}"
                    )
            
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Unknown action: {action}"
                )
        
        except Exception as e:
            logger.exception(f"HumanTool error: {e}")
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )
    
    @property
    def enabled(self) -> bool:
        """工具是否启用"""
        return self._enabled and self._is_main_agent


# ============ 桌面和浏览器操作总结组件占位符 ============

class DesktopActionSummarizer:
    """
    桌面操作总结组件
    用户需要实现这个类来总结桌面操作
    """
    
    def __init__(self, manager: HumanCallbackManager):
        """
        Args:
            manager: HumanCallbackManager 实例
        """
        # 注册到回调管理器
        manager.set_desktop_summarizer(self.summarize)
    
    async def summarize(self, action_result: Dict[str, Any]) -> str:
        """
        总结桌面操作结果
        
        用户需要实现此方法，根据实际需求返回总结文本
        
        Args:
            action_result: 桌面操作结果，可能包含:
                - screenshot: 截图路径
                - clicked_element: 点击的元素
                - typed_text: 输入的文本
                - window_focus: 窗口焦点变化
                - opened_application: 打开的应用程序
                - file_operations: 文件操作列表
                - error: 错误信息
        
        Returns:
            str: 操作总结
        """
        # TODO: 用户实现具体总结逻辑
        # 示例实现:
        summary_parts = []
        
        if "clicked_element" in action_result:
            summary_parts.append(f"点击了元素: {action_result['clicked_element']}")
        
        if "typed_text" in action_result:
            summary_parts.append(f"输入了文本")
        
        if "screenshot" in action_result:
            summary_parts.append("已截取屏幕截图")
        
        if "opened_application" in action_result:
            summary_parts.append(f"打开了应用: {action_result['opened_application']}")
        
        if "file_operations" in action_result:
            ops = action_result["file_operations"]
            summary_parts.append(f执行了 {len(ops)} 个文件操作")
        
        if not summary_parts:
            return "桌面操作执行完成"
        
        return "，".join(summary_parts)


class BrowserActionSummarizer:
    """
    浏览器操作总结组件
    用户需要实现这个类来总结浏览器操作
    """
    
    def __init__(self, manager: HumanCallbackManager):
        """
        Args:
            manager: HumanCallbackManager 实例
        """
        # 注册到回调管理器
        manager.set_browser_summarizer(self.summarize)
    
    async def summarize(self, action_result: Dict[str, Any]) -> str:
        """
        总结浏览器操作结果
        
        用户需要实现此方法，根据实际需求返回总结文本
        
        Args:
            action_result: 浏览器操作结果，可能包含:
                - url: 访问的URL
                - page_title: 页面标题
                - clicked_element: 点击的元素
                - filled_form: 表单填写
                - extracted_content: 提取的内容
                - screenshot: 截图路径
                - console_logs: 控制台日志
                - network_requests: 网络请求
        
        Returns:
            str: 操作总结
        """
        # TODO: 用户实现具体总结逻辑
        # 示例实现:
        summary_parts = []
        
        if "url" in action_result:
            summary_parts.append(f"访问了: {action_result['url']}")
        
        if "page_title" in action_result:
            summary_parts.append(f"页面: {action_result['page_title']}")
        
        if "clicked_element" in action_result:
            summary_parts.append(f"点击了: {action_result['clicked_element']}")
        
        if "extracted_content" in action_result:
            content = action_result["extracted_content"]
            if isinstance(content, str):
                summary_parts.append(f"提取了文本 ({len(content)} 字符)")
            else:
                summary_parts.append(f"提取了内容")
        
        if "screenshot" in action_result:
            summary_parts.append("已截图")
        
        if not summary_parts:
            return "浏览器操作执行完成"
        
        return "，".join(summary_parts)


# 全局实例
_human_manager: Optional[HumanInTheLoopManager] = None


def get_human_manager() -> HumanInTheLoopManager:
    """获取全局人类管理器"""
    global _human_manager
    if _human_manager is None:
        _human_manager = HumanInTheLoopManager()
    return _human_manager


def create_human_tool(
    is_main_agent: bool = True,
    agent_id: str = "main_agent"
) -> HumanTool:
    """创建人类工具实例"""
    global _human_manager
    if _human_manager is None:
        _human_manager = HumanInTheLoopManager()
    
    return HumanTool(None, _human_manager, is_main_agent, agent_id)


def init_human_callbacks() -> HumanCallbackManager:
    """
    初始化人类回调（桌面和浏览器总结组件）
    调用此函数注册用户的总结组件
    
    Usage:
        # 在应用启动时调用
        init_human_callbacks()
        
        # 或自定义总结组件
        manager = get_human_manager().get_callback_manager()
        manager.set_desktop_summarizer(my_desktop_summary_function)
        manager.set_browser_summarizer(my_browser_summary_function)
    """
    global _human_manager
    if _human_manager is None:
        _human_manager = HumanInTheLoopManager()
    
    # 用户可以替换这些实现
    # DesktopActionSummarizer(_human_manager._callback_manager)
    # BrowserActionSummarizer(_human_manager._callback_manager)
    
    return _human_manager._callback_manager
