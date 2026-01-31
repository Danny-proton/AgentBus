"""
AgentBus 插件开发示例

演示如何创建一个简单的插件,注册工具和Hook
"""

from plugins.core import AgentBusPlugin, PluginContext
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ExamplePlugin(AgentBusPlugin):
    """示例插件 - 演示基本功能"""
    
    # 插件元信息
    NAME = "example_plugin"
    VERSION = "1.0.0"
    DESCRIPTION = "示例插件,演示工具注册和Hook使用"
    AUTHOR = "AgentBus Team"
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self.call_count = 0
    
    def get_info(self) -> Dict[str, Any]:
        """返回插件信息"""
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "description": self.DESCRIPTION,
            "author": self.AUTHOR,
            "status": self.status.value,
            "call_count": self.call_count
        }
    
    async def activate(self) -> bool:
        """激活插件"""
        try:
            # 注册工具1: 文本处理
            self.register_tool(
                name="process_text",
                description="处理文本,转换为大写并添加前缀",
                function=self.process_text,
                parameters={
                    "text": {
                        "type": "string",
                        "description": "要处理的文本"
                    },
                    "prefix": {
                        "type": "string",
                        "description": "添加的前缀",
                        "default": "PROCESSED: "
                    }
                }
            )
            
            # 注册工具2: 数据统计
            self.register_tool(
                name="calculate_stats",
                description="计算数字列表的统计信息",
                function=self.calculate_stats,
                parameters={
                    "numbers": {
                        "type": "array",
                        "description": "数字列表"
                    }
                }
            )
            
            # 注册Hook: 消息处理
            self.register_hook(
                event="message.process",
                handler=self.on_message_process,
                priority=10
            )
            
            # 注册Hook: 系统启动
            self.register_hook(
                event="system.startup",
                handler=self.on_system_startup,
                priority=5
            )
            
            self.logger.info(f"插件 {self.NAME} 激活成功")
            return True
            
        except Exception as e:
            self.logger.error(f"插件激活失败: {e}")
            return False
    
    async def deactivate(self) -> bool:
        """停用插件"""
        self.logger.info(f"插件 {self.NAME} 已停用,总调用次数: {self.call_count}")
        return True
    
    # ========== 工具函数 ==========
    
    async def process_text(self, text: str, prefix: str = "PROCESSED: ") -> Dict[str, Any]:
        """处理文本工具"""
        self.call_count += 1
        
        result = prefix + text.upper()
        
        self.logger.info(f"处理文本: {text} -> {result}")
        
        return {
            "success": True,
            "original": text,
            "processed": result,
            "length": len(result)
        }
    
    async def calculate_stats(self, numbers: list) -> Dict[str, Any]:
        """计算统计信息工具"""
        self.call_count += 1
        
        if not numbers:
            return {
                "success": False,
                "error": "数字列表为空"
            }
        
        stats = {
            "count": len(numbers),
            "sum": sum(numbers),
            "average": sum(numbers) / len(numbers),
            "min": min(numbers),
            "max": max(numbers)
        }
        
        self.logger.info(f"计算统计: {stats}")
        
        return {
            "success": True,
            "stats": stats
        }
    
    # ========== Hook处理器 ==========
    
    async def on_message_process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """消息处理Hook"""
        self.logger.info(f"[Hook] 处理消息: {message.get('content', '')[:50]}")
        
        # 可以修改消息内容
        message["processed_by"] = self.NAME
        message["processed_at"] = self.call_count
        
        return message
    
    async def on_system_startup(self, **kwargs) -> None:
        """系统启动Hook"""
        self.logger.info(f"[Hook] 系统启动,插件 {self.NAME} 已就绪")


# ========== 使用示例 ==========

async def main():
    """示例主函数"""
    from plugins.manager import PluginManager
    
    # 创建插件管理器
    plugin_manager = PluginManager()
    
    # 加载插件
    plugin = await plugin_manager.load_plugin(
        plugin_id="example_plugin",
        module_path="examples.plugin_example",
        class_name="ExamplePlugin"
    )
    
    # 激活插件
    await plugin_manager.activate_plugin("example_plugin")
    
    # 执行工具1
    result1 = await plugin_manager.execute_tool(
        "process_text",
        text="hello world",
        prefix=">>> "
    )
    print(f"工具1结果: {result1}")
    
    # 执行工具2
    result2 = await plugin_manager.execute_tool(
        "calculate_stats",
        numbers=[1, 2, 3, 4, 5, 10, 20]
    )
    print(f"工具2结果: {result2}")
    
    # 触发Hook
    await plugin_manager.execute_hook(
        "message.process",
        message={"content": "测试消息"}
    )
    
    # 获取插件信息
    info = plugin.get_info()
    print(f"插件信息: {info}")
    
    # 停用插件
    await plugin_manager.deactivate_plugin("example_plugin")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
