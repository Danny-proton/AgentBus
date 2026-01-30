"""
AgentBus插件框架示例插件

此文件展示了如何创建自定义AgentBus插件。示例插件包含工具、钩子和命令。
"""

import asyncio
from typing import Dict, Any
from agentbus.plugins import AgentBusPlugin, PluginContext


class ExamplePlugin(AgentBusPlugin):
    """
    示例插件类
    
    演示了AgentBusPlugin的基本用法，包括：
    - 自定义插件信息
    - 注册工具
    - 注册事件钩子
    - 注册命令
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self.message_count = 0
    
    def get_info(self) -> Dict[str, Any]:
        """
        返回插件信息
        """
        return {
            'id': self.plugin_id,
            'name': 'Example Plugin',
            'version': '1.0.0',
            'description': '一个示例插件，演示AgentBus插件框架的基本功能',
            'author': 'AgentBus Team',
            'dependencies': []
        }
    
    async def activate(self):
        """
        激活插件时注册工具、钩子和命令
        """
        # 先调用父类方法
        await super().activate()
        
        # 注册工具
        self.register_tool(
            name='count_messages',
            description='统计处理的消息数量',
            function=self.count_messages
        )
        
        self.register_tool(
            name='echo',
            description='回显输入的文本',
            function=self.echo_message
        )
        
        self.register_tool(
            name='async_task',
            description='执行异步任务',
            function=self.async_task
        )
        
        # 注册事件钩子
        self.register_hook(
            event='message_received',
            handler=self.on_message_received,
            priority=10
        )
        
        self.register_hook(
            event='message_sent',
            handler=self.on_message_sent,
            priority=5
        )
        
        # 注册命令
        self.register_command(
            command='/count',
            handler=self.handle_count_command,
            description='显示消息统计'
        )
        
        self.register_command(
            command='/status',
            handler=self.handle_status_command,
            description='显示插件状态'
        )
        
        self.context.logger.info(f"Example plugin {self.plugin_id} activated")
    
    def count_messages(self) -> int:
        """统计消息数量"""
        return self.message_count
    
    def echo_message(self, text: str) -> str:
        """回显消息"""
        return f"Echo: {text}"
    
    async def async_task(self, duration: int = 1) -> str:
        """执行异步任务"""
        await asyncio.sleep(duration)
        return f"Task completed after {duration} seconds"
    
    async def on_message_received(self, message: str, sender: str):
        """消息接收钩子"""
        self.message_count += 1
        self.context.logger.info(f"Received message from {sender}: {message}")
    
    async def on_message_sent(self, message: str, recipient: str):
        """消息发送钩子"""
        self.context.logger.info(f"Sent message to {recipient}: {message}")
    
    async def handle_count_command(self, args: str) -> str:
        """处理计数命令"""
        return f"已处理 {self.message_count} 条消息"
    
    async def handle_status_command(self, args: str) -> str:
        """处理状态命令"""
        status_info = {
            'plugin_id': self.plugin_id,
            'status': self.status.value,
            'message_count': self.message_count,
            'tools': len(self.get_tools()),
            'hooks': sum(len(hooks) for hooks in self.get_hooks().values()),
            'commands': len(self.get_commands())
        }
        return f"插件状态: {status_info}"