"""
AgentBus Plugin System Example
Agent系统插件示例
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime

from ..core.types import PluginType, AgentMessage, MessageType, Priority


# 示例插件清单
EXAMPLE_PLUGIN_MANIFEST = {
    "plugin_id": "example_capability",
    "name": "Example Capability Plugin",
    "version": "1.0.0",
    "description": "An example plugin that adds custom capabilities to agents",
    "plugin_type": PluginType.CAPABILITY.value,
    "author": "AgentBus Team",
    "license": "MIT",
    "capabilities": ["custom_text_processing", "data_analysis"],
    "permissions": ["read", "write", "execute"],
    "dependencies": [],
    "entry_point": "main"
}


class ExampleCapabilityPlugin:
    """示例能力插件"""
    
    def __init__(self, manifest: dict, config: Dict[str, Any]):
        self.manifest = manifest
        self.config = config
        self.logger = f"plugin.{manifest['plugin_id']}"
        self.enabled = False
    
    async def on_load(self) -> bool:
        """插件加载"""
        print(f"[{self.logger}] Loading example capability plugin...")
        
        # 模拟插件初始化
        await asyncio.sleep(0.1)
        
        print(f"[{self.logger}] Plugin loaded successfully")
        return True
    
    async def on_unload(self) -> bool:
        """插件卸载"""
        print(f"[{self.logger}] Unloading example capability plugin...")
        
        # 清理资源
        await asyncio.sleep(0.1)
        
        print(f"[{self.logger}] Plugin unloaded")
        return True
    
    async def on_enable(self) -> bool:
        """启用插件"""
        self.enabled = True
        print(f"[{self.logger}] Plugin enabled")
        return True
    
    async def on_disable(self) -> bool:
        """禁用插件"""
        self.enabled = False
        print(f"[{self.logger}] Plugin disabled")
        return True
    
    async def on_message(self, message: AgentMessage):
        """处理消息"""
        if not self.enabled:
            return
        
        print(f"[{self.logger}] Received message: {message.message_type}")
        
        # 处理自定义能力请求
        if message.message_type == MessageType.DIRECT:
            content = message.content
            if isinstance(content, dict) and content.get("action") == "custom_processing":
                response = await self._process_custom_request(content)
                
                # 发送响应
                response_message = AgentMessage(
                    message_type=MessageType.DIRECT,
                    sender_id=self.manifest['plugin_id'],
                    receiver_id=message.sender_id,
                    content=response,
                    correlation_id=message.message_id
                )
                
                # 这里应该发送到通信总线
                print(f"[{self.logger}] Sending response: {response}")
    
    async def _process_custom_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理自定义请求"""
        action = request.get("action")
        
        if action == "custom_text_processing":
            text = request.get("text", "")
            processed_text = f"[PROCESSED] {text.upper()}"
            
            return {
                "success": True,
                "result": processed_text,
                "metadata": {
                    "processing_time": 0.1,
                    "original_length": len(text),
                    "processed_length": len(processed_text)
                }
            }
        
        elif action == "data_analysis":
            data = request.get("data", [])
            
            if not isinstance(data, list):
                return {
                    "success": False,
                    "error": "Data must be a list"
                }
            
            analysis = {
                "count": len(data),
                "sum": sum(data) if data else 0,
                "average": sum(data) / len(data) if data else 0,
                "min": min(data) if data else None,
                "max": max(data) if data else None
            }
            
            return {
                "success": True,
                "result": analysis,
                "metadata": {
                    "analysis_time": 0.05
                }
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
    
    def get_capabilities(self) -> List[str]:
        """获取插件能力"""
        return self.manifest.get("capabilities", [])


# 示例通信插件
COMMUNICATION_PLUGIN_MANIFEST = {
    "plugin_id": "example_communication",
    "name": "Example Communication Plugin",
    "version": "1.0.0",
    "description": "An example plugin that enhances communication between agents",
    "plugin_type": PluginType.COMMUNICATION.value,
    "author": "AgentBus Team",
    "license": "MIT",
    "capabilities": ["message_routing", "broadcast_management"],
    "permissions": ["read", "write", "send", "receive"],
    "dependencies": []
}


class ExampleCommunicationPlugin:
    """示例通信插件"""
    
    def __init__(self, manifest: dict, config: Dict[str, Any]):
        self.manifest = manifest
        self.config = config
        self.logger = f"plugin.{manifest['plugin_id']}"
        self.enabled = False
        self.message_history: List[Dict[str, Any]] = []
    
    async def on_load(self) -> bool:
        """插件加载"""
        print(f"[{self.logger}] Loading communication plugin...")
        await asyncio.sleep(0.1)
        print(f"[{self.logger}] Communication plugin loaded")
        return True
    
    async def on_unload(self) -> bool:
        """插件卸载"""
        print(f"[{self.logger}] Unloading communication plugin...")
        await asyncio.sleep(0.1)
        print(f"[{self.logger}] Communication plugin unloaded")
        return True
    
    async def on_enable(self) -> bool:
        """启用插件"""
        self.enabled = True
        print(f"[{self.logger}] Communication plugin enabled")
        return True
    
    async def on_disable(self) -> bool:
        """禁用插件"""
        self.enabled = False
        print(f"[{self.logger}] Communication plugin disabled")
        return True
    
    async def on_message(self, message: AgentMessage):
        """处理消息"""
        if not self.enabled:
            return
        
        # 记录消息历史
        self.message_history.append({
            "timestamp": datetime.now().isoformat(),
            "sender": message.sender_id,
            "receiver": message.receiver_id,
            "type": message.message_type.value,
            "priority": message.priority.value
        })
        
        # 保持历史记录在合理大小
        if len(self.message_history) > 1000:
            self.message_history = self.message_history[-500:]
        
        print(f"[{self.logger}] Message logged: {message.sender_id} -> {message.receiver_id}")
    
    def get_message_statistics(self) -> Dict[str, Any]:
        """获取消息统计"""
        if not self.message_history:
            return {}
        
        total_messages = len(self.message_history)
        by_type = {}
        by_priority = {}
        
        for msg in self.message_history:
            msg_type = msg["type"]
            priority = msg["priority"]
            
            by_type[msg_type] = by_type.get(msg_type, 0) + 1
            by_priority[priority] = by_priority.get(priority, 0) + 1
        
        return {
            "total_messages": total_messages,
            "by_type": by_type,
            "by_priority": by_priority,
            "recent_messages": self.message_history[-10:]
        }


# 示例监控插件
MONITORING_PLUGIN_MANIFEST = {
    "plugin_id": "example_monitoring",
    "name": "Example Monitoring Plugin",
    "version": "1.0.0",
    "description": "An example plugin that provides custom monitoring capabilities",
    "plugin_type": PluginType.MONITORING.value,
    "author": "AgentBus Team",
    "license": "MIT",
    "capabilities": ["performance_tracking", "resource_monitoring"],
    "permissions": ["read", "monitor"],
    "dependencies": []
}


class ExampleMonitoringPlugin:
    """示例监控插件"""
    
    def __init__(self, manifest: dict, config: Dict[str, Any]):
        self.manifest = manifest
        self.config = config
        self.logger = f"plugin.{manifest['plugin_id']}"
        self.enabled = False
        self.performance_data: List[Dict[str, Any]] = []
    
    async def on_load(self) -> bool:
        """插件加载"""
        print(f"[{self.logger}] Loading monitoring plugin...")
        await asyncio.sleep(0.1)
        print(f"[{self.logger}] Monitoring plugin loaded")
        return True
    
    async def on_unload(self) -> bool:
        """插件卸载"""
        print(f"[{self.logger}] Unloading monitoring plugin...")
        await asyncio.sleep(0.1)
        print(f"[{self.logger}] Monitoring plugin unloaded")
        return True
    
    async def on_enable(self) -> bool:
        """启用插件"""
        self.enabled = True
        # 启动性能监控循环
        asyncio.create_task(self._performance_monitoring_loop())
        print(f"[{self.logger}] Monitoring plugin enabled")
        return True
    
    async def on_disable(self) -> bool:
        """禁用插件"""
        self.enabled = False
        print(f"[{self.logger}] Monitoring plugin disabled")
        return True
    
    async def _performance_monitoring_loop(self):
        """性能监控循环"""
        while self.enabled:
            try:
                # 收集性能数据
                performance_data = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_usage": await self._get_cpu_usage(),
                    "memory_usage": await self._get_memory_usage(),
                    "active_threads": asyncio.get_event_loop()._default_executor._threads if hasattr(asyncio.get_event_loop()._default_executor, '_threads') else 0
                }
                
                self.performance_data.append(performance_data)
                
                # 保持数据在合理大小
                if len(self.performance_data) > 100:
                    self.performance_data = self.performance_data[-50:]
                
                await asyncio.sleep(5)  # 每5秒收集一次
                
            except Exception as e:
                print(f"[{self.logger}] Performance monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except:
            return 0.0
    
    async def _get_memory_usage(self) -> float:
        """获取内存使用率"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except:
            return 0.0
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        if not self.performance_data:
            return {"message": "No performance data available"}
        
        latest_data = self.performance_data[-1]
        
        # 计算平均值
        cpu_values = [d["cpu_usage"] for d in self.performance_data]
        memory_values = [d["memory_usage"] for d in self.performance_data]
        
        return {
            "current_performance": latest_data,
            "averages": {
                "cpu_usage": sum(cpu_values) / len(cpu_values),
                "memory_usage": sum(memory_values) / len(memory_values)
            },
            "data_points": len(self.performance_data)
        }


# 插件工厂函数
def create_example_capability_plugin(manifest: dict, config: dict) -> ExampleCapabilityPlugin:
    """创建示例能力插件"""
    return ExampleCapabilityPlugin(manifest, config)


def create_example_communication_plugin(manifest: dict, config: dict) -> ExampleCommunicationPlugin:
    """创建示例通信插件"""
    return ExampleCommunicationPlugin(manifest, config)


def create_example_monitoring_plugin(manifest: dict, config: dict) -> ExampleMonitoringPlugin:
    """创建示例监控插件"""
    return ExampleMonitoringPlugin(manifest, config)


# 插件映射
PLUGIN_FACTORIES = {
    "example_capability": create_example_capability_plugin,
    "example_communication": create_example_communication_plugin,
    "example_monitoring": create_example_monitoring_plugin
}


# 示例使用代码
async def demonstrate_plugins():
    """演示插件功能"""
    from ..plugins.system import PluginSystem, PluginBase
    
    # 创建插件系统
    plugin_system = PluginSystem("demo")
    
    try:
        # 启动插件系统
        await plugin_system.start()
        
        # 创建并加载示例插件
        examples = [
            (EXAMPLE_PLUGIN_MANIFEST, {}),
            (COMMUNICATION_PLUGIN_MANIFEST, {}),
            (MONITORING_PLUGIN_MANIFEST, {})
        ]
        
        for manifest, config in examples:
            # 模拟插件文件路径
            plugin_path = f"./plugins/{manifest['plugin_id']}.py"
            
            # 创建模拟模块
            class MockModule:
                PLUGIN_MANIFEST = manifest
                
                if manifest['plugin_id'] == "example_capability":
                    Plugin = create_example_capability_plugin(manifest, config)
                elif manifest['plugin_id'] == "example_communication":
                    Plugin = create_example_communication_plugin(manifest, config)
                elif manifest['plugin_id'] == "example_monitoring":
                    Plugin = create_example_monitoring_plugin(manifest, config)
            
            # 模拟加载插件
            success = await plugin_system.load_plugin(plugin_path, config)
            if success:
                print(f"✓ Plugin {manifest['name']} loaded successfully")
                
                # 启用插件
                await plugin_system.enable_plugin(manifest['plugin_id'])
                
                # 测试插件功能
                plugin_instance = plugin_system.get_plugin(manifest['plugin_id'])
                if plugin_instance:
                    await test_plugin_functionality(plugin_instance, manifest['plugin_id'])
            else:
                print(f"✗ Failed to load plugin {manifest['name']}")
        
        # 显示插件列表
        plugins = plugin_system.list_plugins()
        print(f"\nLoaded plugins: {len(plugins)}")
        for plugin in plugins:
            print(f"  - {plugin['name']} v{plugin['version']} ({plugin['type']})")
        
        # 显示统计信息
        stats = plugin_system.get_plugin_stats()
        print(f"\nPlugin statistics:")
        print(f"  Total plugins: {stats['total_plugins']}")
        print(f"  Loaded plugins: {stats['loaded_plugins']}")
        print(f"  Failed loads: {stats['failed_loads']}")
        
    finally:
        # 停止插件系统
        await plugin_system.stop()


async def test_plugin_functionality(plugin_instance, plugin_id: str):
    """测试插件功能"""
    try:
        if plugin_id == "example_capability":
            # 测试能力插件
            print(f"  Testing capabilities: {plugin_instance.get_capabilities()}")
            
            # 模拟发送处理请求
            message = AgentMessage(
                message_type=MessageType.DIRECT,
                sender_id="test_agent",
                receiver_id=plugin_id,
                content={
                    "action": "custom_text_processing",
                    "text": "hello world"
                }
            )
            
            await plugin_instance.handle_message(message)
            
        elif plugin_id == "example_communication":
            # 测试通信插件
            print(f"  Testing communication features...")
            
            # 模拟消息
            message = AgentMessage(
                message_type=MessageType.BROADCAST,
                sender_id="test_agent",
                receiver_id="all",
                content={"message": "test broadcast"}
            )
            
            await plugin_instance.handle_message(message)
            
            # 获取统计
            stats = plugin_instance.get_message_statistics()
            print(f"  Message stats: {stats}")
            
        elif plugin_id == "example_monitoring":
            # 测试监控插件
            print(f"  Testing monitoring features...")
            
            # 等待一些性能数据收集
            await asyncio.sleep(2)
            
            # 获取性能报告
            report = plugin_instance.get_performance_report()
            print(f"  Performance report: {report}")
    
    except Exception as e:
        print(f"  Error testing plugin {plugin_id}: {e}")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demonstrate_plugins())