"""
人在回路 (Human-in-the-Loop) 模块

核心设计理念：
- Agent 可以将人类视为一个强大的"工具"来调用
- 支持多种交互模式：bash操作、桌面操作、浏览器操作、反馈
- 人类操作完成后，Agent 会总结其行为并继续执行
- 支持超时机制和操作取消
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from agent_hard_tool import (
    BaseTool,
    ToolResult,
    ToolStatus,
    Parameter,
    ParameterType
)
from config.settings import get_settings
from services.log_service import get_logger

logger = get_logger(__name__)


class HumanActionType(str, Enum):
    """人在回路支持的操作类型"""
    BASH = "bash"           # Bash命令操作
    DESKTOP = "desktop"     # 桌面操作
    BROWSER = "browser"     # 浏览器操作
    FEEDBACK = "feedback"   # 简单反馈/建议


class HumanActionStatus(str, Enum):
    """操作状态"""
    PENDING = "pending"     # 等待人类开始
    IN_PROGRESS = "in_progress"  # 人类正在执行
    COMPLETED = "completed"  # 人类完成操作
    FAILED = "failed"       # 操作失败
    CANCELLED = "cancelled" # 被取消
    TIMEOUT = "timeout"     # 超时


class HumanLoopError(Exception):
    """人在回路基础异常"""
    pass


class HumanOperationNotFoundError(HumanLoopError):
    """操作不存在"""
    pass


class HumanOperationStatusError(HumanLoopError):
    """操作状态错误"""
    pass


@dataclass
class HumanOperation:
    """
    记录一次人类操作请求
    
    Attributes:
        operation_id: 唯一操作ID
        action_type: 操作类型 (bash/desktop/browser/feedback)
        request_content: 请求内容
        status: 当前状态
        created_at: 创建时间
        completed_at: 完成时间
        result: 操作结果
        summary: 操作总结（Agent汇总人类行为后生成）
    """
    operation_id: str
    action_type: HumanActionType
    request_content: str
    status: HumanActionStatus = HumanActionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "operation_id": self.operation_id,
            "action_type": self.action_type.value,
            "request_content": self.request_content,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "summary": self.summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HumanOperation':
        """从字典创建"""
        return cls(
            operation_id=data["operation_id"],
            action_type=HumanActionType(data["action_type"]),
            request_content=data["request_content"],
            status=HumanActionStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            result=data.get("result"),
            summary=data.get("summary")
        )


class HumanInTheLoopManager:
    """
    人在回路管理器
    
    负责：
    - 管理所有待处理的人类操作
    - 处理操作的创建、更新、查询
    - 维护操作历史
    """
    
    def __init__(self):
        """初始化管理器"""
        self._operations: Dict[str, HumanOperation] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._config = get_settings().human_loop
        logger.info("HumanInTheLoopManager initialized")
    
    def _get_lock(self, operation_id: str) -> asyncio.Lock:
        """获取操作锁（每个操作独立锁）"""
        if operation_id not in self._locks:
            self._locks[operation_id] = asyncio.Lock()
        return self._locks[operation_id]
    
    async def create_operation(
        self,
        action_type: HumanActionType,
        request_content: str,
        timeout: Optional[int] = None
    ) -> HumanOperation:
        """
        创建新的人类操作请求
        
        Args:
            action_type: 操作类型
            request_content: 请求内容
            timeout: 超时时间（秒），使用配置默认值
        
        Returns:
            创建的操作对象
        """
        timeout = timeout or self._config.default_timeout
        
        operation = HumanOperation(
            operation_id=f"{self._config.operation_id_prefix}{uuid.uuid4().hex[:8]}",
            action_type=action_type,
            request_content=request_content
        )
        
        async with self._get_lock(operation.operation_id):
            self._operations[operation.operation_id] = operation
        
        logger.info(
            f"Human operation created: {operation.operation_id} "
            f"(type={action_type.value}, timeout={timeout}s)"
        )
        
        # 启动超时监控任务
        asyncio.create_task(self._monitor_timeout(operation.operation_id, timeout))
        
        return operation
    
    async def start_operation(self, operation_id: str) -> HumanOperation:
        """标记操作开始执行"""
        async with self._get_lock(operation_id):
            operation = self._get_operation(operation_id)
            if operation.status != HumanActionStatus.PENDING:
                raise HumanOperationStatusError(
                    f"Operation {operation_id} is not pending (current: {operation.status.value})"
                )
            operation.status = HumanActionStatus.IN_PROGRESS
            logger.info(f"Human operation started: {operation_id}")
            return operation
    
    async def complete_operation(
        self,
        operation_id: str,
        result: str,
        summary: Optional[str] = None
    ) -> HumanOperation:
        """
        完成操作
        
        Args:
            operation_id: 操作ID
            result: 操作结果
            summary: 操作总结（Agent生成的摘要）
        """
        async with self._get_lock(operation_id):
            operation = self._get_operation(operation_id)
            operation.status = HumanActionStatus.COMPLETED
            operation.completed_at = datetime.now()
            operation.result = result
            operation.summary = summary or f"Human performed {operation.action_type.value} operation"
            
            logger.info(f"Human operation completed: {operation_id}")
            return operation
    
    async def fail_operation(self, operation_id: str, error: str) -> HumanOperation:
        """标记操作失败"""
        async with self._get_lock(operation_id):
            operation = self._get_operation(operation_id)
            operation.status = HumanActionStatus.FAILED
            operation.completed_at = datetime.now()
            operation.result = error
            
            logger.warning(f"Human operation failed: {operation_id} - {error}")
            return operation
    
    async def cancel_operation(self, operation_id: str) -> HumanOperation:
        """取消操作"""
        async with self._get_lock(operation_id):
            operation = self._get_operation(operation_id)
            operation.status = HumanActionStatus.CANCELLED
            operation.completed_at = datetime.now()
            
            logger.info(f"Human operation cancelled: {operation_id}")
            return operation
    
    async def get_operation(self, operation_id: str) -> Optional[HumanOperation]:
        """获取操作信息（非异步锁版本，用于查询）"""
        return self._operations.get(operation_id)
    
    async def check_result(self, operation_id: str) -> Dict[str, Any]:
        """
        检查操作结果
        
        Returns:
            操作状态和结果
        """
        operation = self._get_operation(operation_id)
        
        return {
            "operation_id": operation.operation_id,
            "status": operation.status.value,
            "action_type": operation.action_type.value,
            "request_content": operation.request_content,
            "result": operation.result,
            "summary": operation.summary,
            "created_at": operation.created_at.isoformat(),
            "completed_at": operation.completed_at.isoformat() if operation.completed_at else None
        }
    
    def _get_operation(self, operation_id: str) -> HumanOperation:
        """获取操作，不存在则抛出异常"""
        if operation_id not in self._operations:
            raise HumanOperationNotFoundError(f"Operation {operation_id} not found")
        return self._operations[operation_id]
    
    async def _monitor_timeout(self, operation_id: str, timeout: int):
        """监控操作超时"""
        try:
            await asyncio.sleep(timeout)
            
            async with self._get_lock(operation_id):
                operation = self._get_operation(operation_id)
                if operation.status in [HumanActionStatus.PENDING, HumanActionStatus.IN_PROGRESS]:
                    operation.status = HumanActionStatus.TIMEOUT
                    operation.completed_at = datetime.now()
                    operation.result = f"Operation timed out after {timeout} seconds"
                    logger.warning(f"Human operation timed out: {operation_id}")
                    
        except asyncio.CancelledError:
            # 操作已完成，取消超时监控
            pass
        except Exception as e:
            logger.error(f"Error in timeout monitor for {operation_id}: {e}")
    
    async def cleanup_completed(self, max_age_hours: int = 24):
        """清理已完成的历史操作"""
        now = datetime.now()
        to_remove = []
        
        for op_id, operation in self._operations.items():
            if operation.completed_at:
                age = (now - operation.completed_at).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(op_id)
        
        for op_id in to_remove:
            del self._operations[op_id]
            if op_id in self._locks:
                del self._locks[op_id]
        
        logger.info(f"Cleaned up {len(to_remove)} completed operations")
    
    def get_pending_operations(self) -> list:
        """获取所有待处理的操作"""
        return [
            op.to_dict() 
            for op in self._operations.values() 
            if op.status in [HumanActionStatus.PENDING, HumanActionStatus.IN_PROGRESS]
        ]


# ========== 抽象汇总组件（用户可自定义实现）==========
class DesktopActionSummarizer:
    """
    桌面操作汇总器（抽象基类）
    
    用户可继承此类实现桌面操作的汇总逻辑。
    Agent 会在人类完成桌面操作后调用此类来生成操作摘要。
    """
    
    async def summarize(self, action_type: str, action_details: Dict[str, Any]) -> str:
        """
        汇总桌面操作
        
        Args:
            action_type: 操作类型
            action_details: 操作详情
        
        Returns:
            操作摘要文本
        """
        raise NotImplementedError("Subclasses must implement summarize()")


class BrowserActionSummarizer:
    """
    浏览器操作汇总器（抽象基类）
    
    用户可继承此类实现浏览器操作的汇总逻辑。
    Agent 会在人类完成浏览器操作后调用此类来生成操作摘要。
    """
    
    async def summarize(self, url: str, actions_performed: list, screenshots: Optional[list] = None) -> str:
        """
        汇总浏览器操作
        
        Args:
            url: 访问的URL
            actions_performed: 执行的浏览器操作列表
            screenshots: 截图列表（可选）
        
        Returns:
            操作摘要文本
        """
        raise NotImplementedError("Subclasses must implement summarize()")


class HumanTool(BaseTool):
    """
    人在回路工具 - Agent调用人类的接口
    
    Agent 可以通过此工具请求人类介入：
    1. 执行bash操作
    2. 执行桌面操作
    3. 执行浏览器操作
    4. 获取人类反馈
    
    使用方式：
    - invoke: 创建新的操作请求
    - check_result: 检查操作结果
    - cancel: 取消操作
    """
    
    def __init__(
        self,
        operation_manager: Optional[HumanInTheLoopManager] = None,
        desktop_summarizer: Optional[DesktopActionSummarizer] = None,
        browser_summarizer: Optional[BrowserActionSummarizer] = None
    ):
        """
        初始化人在回路工具
        
        Args:
            operation_manager: 操作管理器（可选，懒加载）
            desktop_summarizer: 桌面操作汇总器
            browser_summarizer: 浏览器操作汇总器
        """
        super().__init__()
        self._manager = operation_manager
        self._desktop_summarizer = desktop_summarizer
        self._browser_summarizer = browser_summarizer
        self._config = get_settings().human_loop
    
    @property
    def manager(self) -> HumanInTheLoopManager:
        """懒加载获取管理器"""
        if self._manager is None:
            self._manager = HumanInTheLoopManager()
        return self._manager
    
    @property
    def name(self) -> str:
        return "human_in_the_loop"
    
    @property
    def description(self) -> str:
        return (
            "人在回路工具：Agent可以请求人类介入执行复杂操作。\n"
            "支持操作类型：\n"
            "  - bash: 请人类执行bash命令操作\n"
            "  - desktop: 请人类执行桌面操作\n"
            "  - browser: 请人类执行浏览器操作\n"
            "  - feedback: 请人类提供反馈或建议\n\n"
            "使用方式：\n"
            "1. invoke: 创建操作请求，等待人类完成\n"
            "2. check_result: 检查操作结果\n"
            "3. cancel: 取消待处理的请求"
        )
    
    @property
    def parameters(self) -> list[Parameter]:
        return [
            Parameter(
                name="action",
                type=ParameterType.STRING,
                description="操作类型: invoke(创建请求) | check_result(检查结果) | cancel(取消)",
                required=True,
                enum=["invoke", "check_result", "cancel"]
            ),
            Parameter(
                name="action_type",
                type=ParameterType.STRING,
                description="操作类型 (仅invoke需要): bash | desktop | browser | feedback",
                required=False,
                enum=["bash", "desktop", "browser", "feedback"]
            ),
            Parameter(
                name="request_content",
                type=ParameterType.STRING,
                description="请求内容，描述需要人类做什么 (仅invoke需要)",
                required=False
            ),
            Parameter(
                name="operation_id",
                type=ParameterType.STRING,
                description="操作ID (check_result和cancel需要)",
                required=False
            ),
            Parameter(
                name="timeout",
                type=ParameterType.INTEGER,
                description="超时时间（秒），默认使用配置值",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行人在回路操作
        """
        action = kwargs.get("action", "invoke")
        
        try:
            if action == "invoke":
                return await self._invoke(
                    action_type=kwargs.get("action_type", "feedback"),
                    request_content=kwargs.get("request_content", ""),
                    timeout=kwargs.get("timeout")
                )
            elif action == "check_result":
                return await self._check_result(kwargs.get("operation_id"))
            elif action == "cancel":
                return await self._cancel(kwargs.get("operation_id"))
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Unknown action: {action}"
                )
        except HumanOperationNotFoundError as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
        except HumanOperationStatusError as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
        except Exception as e:
            logger.error(f"Human tool error: {e}")
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
    
    async def _invoke(
        self,
        action_type: str,
        request_content: str,
        timeout: Optional[int]
    ) -> ToolResult:
        """创建新的操作请求"""
        if not request_content:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="request_content is required for invoke action"
            )
        
        # 验证操作类型
        try:
            action_enum = HumanActionType(action_type)
        except ValueError:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Invalid action_type: {action_type}"
            )
        
        # 创建操作
        operation = await self.manager.create_operation(
            action_type=action_enum,
            request_content=request_content,
            timeout=timeout
        )
        
        # 构建提示信息
        timeout_display = timeout or self._config.default_timeout
        
        if action_enum == HumanActionType.BASH:
            prompt = (
                f"**Agent请求人类执行Bash操作**\n\n"
                f"**操作ID**: `{operation.operation_id}`\n"
                f"**超时时间**: {timeout_display}秒\n\n"
                f"**请求内容**:\n{request_content}\n\n"
                f"请执行上述bash操作，完成后告诉我结果。"
            )
        elif action_enum == HumanActionType.DESKTOP:
            prompt = (
                f"**Agent请求人类执行桌面操作**\n\n"
                f"**操作ID**: `{operation.operation_id}`\n"
                f"**超时时间**: {timeout_display}秒\n\n"
                f"**请求内容**:\n{request_content}\n\n"
                f"请执行上述桌面操作，完成后告诉我你做了什么。"
            )
        elif action_enum == HumanActionType.BROWSER:
            prompt = (
                f"**Agent请求人类执行浏览器操作**\n\n"
                f"**操作ID**: `{operation.operation_id}`\n"
                f"**超时时间**: {timeout_display}秒\n\n"
                f"**请求内容**:\n{request_content}\n\n"
                f"请执行上述浏览器操作，完成后告诉我你访问了哪些页面、执行了什么操作。"
            )
        else:  # FEEDBACK
            prompt = (
                f"**Agent请求人类反馈**\n\n"
                f"**操作ID**: `{operation.operation_id}`\n"
                f"**超时时间**: {timeout_display}秒\n\n"
                f"**请求内容**:\n{request_content}\n\n"
                f"请提供你的反馈或建议。"
            )
        
        return ToolResult(
            status=ToolStatus.REQUIRE_INPUT,
            output=prompt,
            metadata={
                "operation_id": operation.operation_id,
                "action_type": action_type,
                "timeout": timeout_display,
                "message": "等待人类响应..."
            }
        )
    
    async def _check_result(self, operation_id: str) -> ToolResult:
        """检查操作结果"""
        if not operation_id:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="operation_id is required for check_result action"
            )
        
        result = await self.manager.check_result(operation_id)
        status = result["status"]
        
        # 根据状态返回不同结果
        if status in [HumanActionStatus.PENDING.value, HumanActionStatus.IN_PROGRESS.value]:
            # 仍在等待
            return ToolResult(
                status=ToolStatus.REQUIRE_INPUT,
                output=f"操作 {operation_id} 仍在进行中，请等待人类完成...",
                metadata=result
            )
        
        elif status == HumanActionStatus.COMPLETED.value:
            # 获取总结
            summary = result.get("summary")
            
            if not summary and result.get("result"):
                # 如果没有预生成的总结，根据操作类型尝试生成
                action_type = result.get("action_type")
                summary = await self._generate_summary(
                    action_type, 
                    result["request_content"], 
                    result["result"]
                )
            
            return ToolResult(
                status=ToolStatus.DONE,
                output=f"人类已完成操作！\n\n**总结**: {summary}",
                metadata=result
            )
        
        elif status == HumanActionStatus.TIMEOUT.value:
            return ToolResult(
                status=ToolStatus.DONE,
                output=f"操作 {operation_id} 已超时，人类未能在规定时间内完成。",
                metadata=result
            )
        
        elif status == HumanActionStatus.CANCELLED.value:
            return ToolResult(
                status=ToolStatus.DONE,
                output=f"操作 {operation_id} 已被取消。",
                metadata=result
            )
        
        elif status == HumanActionStatus.FAILED.value:
            return ToolResult(
                status=ToolStatus.DONE,
                output=f"操作 {operation_id} 失败：{result.get('result', '未知错误')}",
                metadata=result
            )
        
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown status: {status}"
            )
    
    async def _cancel(self, operation_id: str) -> ToolResult:
        """取消操作"""
        if not operation_id:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="operation_id is required for cancel action"
            )
        
        await self.manager.cancel_operation(operation_id)
        
        return ToolResult(
            status=ToolStatus.DONE,
            output=f"操作 {operation_id} 已取消",
            metadata={"operation_id": operation_id, "status": "cancelled"}
        )
    
    async def _generate_summary(
        self,
        action_type: str,
        request: str,
        result: str
    ) -> str:
        """根据操作类型生成总结"""
        if action_type == "bash" and self._desktop_summarizer:
            try:
                return await self._desktop_summarizer.summarize("bash", {
                    "request": request,
                    "result": result
                })
            except NotImplementedError:
                pass
        
        elif action_type == "desktop" and self._desktop_summarizer:
            try:
                return await self._desktop_summarizer.summarize("desktop", {
                    "request": request,
                    "result": result
                })
            except NotImplementedError:
                pass
        
        elif action_type == "browser" and self._browser_summarizer:
            try:
                return await self._browser_summarizer.summarize(
                    url="",
                    actions_performed=[result],
                    screenshots=None
                )
            except NotImplementedError:
                pass
        
        # 默认总结
        return f"人类执行了{action_type}操作：{result}"
