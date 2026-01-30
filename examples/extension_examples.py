"""
AgentBus示例扩展
AgentBus Example Extension

这个文件演示了如何创建和使用AgentBus扩展系统。

This file demonstrates how to create and use the AgentBus extension system.

Author: MiniMax Agent
License: MIT
"""

import logging
from typing import Dict, List, Set, Any
from agentbus.extensions import (
    Extension, ExtensionId, ExtensionName, ExtensionType, CapabilityName,
    ExtensionDependency, ExtensionVersion, ExtensionState, ExtensionType as ExtType
)


class HelloWorldExtension(Extension):
    """Hello World 示例扩展"""
    
    def __init__(self):
        super().__init__(
            extension_id="hello_world",
            name="Hello World Extension",
            version="1.0.0",
            description="一个简单的Hello World示例扩展",
            author="MiniMax Agent",
            extension_type=ExtType.CUSTOM,
            capabilities={"greeting", "hello_world"},
            dependencies=[]
        )
        self._greeting_count = 0
    
    def _do_initialize(self) -> bool:
        """初始化扩展"""
        self._logger.info("Hello World扩展正在初始化...")
        return True
    
    def _do_activate(self) -> bool:
        """激活扩展"""
        self._logger.info("Hello World扩展已激活！")
        return True
    
    def _do_deactivate(self) -> bool:
        """停用扩展"""
        self._logger.info("Hello World扩展已停用")
        return True
    
    def _do_cleanup(self) -> bool:
        """清理扩展"""
        self._logger.info("Hello World扩展已清理")
        return True
    
    def say_hello(self, name: str = "World") -> str:
        """说Hello的方法"""
        self._greeting_count += 1
        message = f"Hello, {name}! (第{self._greeting_count}次问候)"
        self._logger.info(f"说Hello: {message}")
        return message
    
    def get_greeting_count(self) -> int:
        """获取问候次数"""
        return self._greeting_count
    
    def get_capabilities_info(self) -> Dict[str, Any]:
        """获取能力信息"""
        return {
            "greeting": {
                "description": "提供问候功能",
                "methods": ["say_hello"]
            },
            "hello_world": {
                "description": "Hello World示例功能",
                "methods": ["get_greeting_count"]
            }
        }


class CalculatorExtension(Extension):
    """计算器扩展"""
    
    def __init__(self):
        super().__init__(
            extension_id="calculator",
            name="Calculator Extension", 
            version="1.0.0",
            description="提供基础计算功能的扩展",
            author="MiniMax Agent",
            extension_type=ExtType.TOOL,
            capabilities={"math_operations", "calculator"},
            dependencies=[]
        )
        self._operations_count = 0
    
    def _do_initialize(self) -> bool:
        """初始化扩展"""
        self._logger.info("Calculator扩展正在初始化...")
        return True
    
    def _do_activate(self) -> bool:
        """激活扩展"""
        self._logger.info("Calculator扩展已激活！")
        return True
    
    def _do_deactivate(self) -> bool:
        """停用扩展"""
        self._logger.info("Calculator扩展已停用")
        return True
    
    def _do_cleanup(self) -> bool:
        """清理扩展"""
        self._logger.info("Calculator扩展已清理")
        return True
    
    def add(self, a: float, b: float) -> float:
        """加法"""
        result = a + b
        self._operations_count += 1
        self._logger.info(f"加法计算: {a} + {b} = {result}")
        return result
    
    def subtract(self, a: float, b: float) -> float:
        """减法"""
        result = a - b
        self._operations_count += 1
        self._logger.info(f"减法计算: {a} - {b} = {result}")
        return result
    
    def multiply(self, a: float, b: float) -> float:
        """乘法"""
        result = a * b
        self._operations_count += 1
        self._logger.info(f"乘法计算: {a} * {b} = {result}")
        return result
    
    def divide(self, a: float, b: float) -> float:
        """除法"""
        if b == 0:
            raise ValueError("除数不能为零")
        result = a / b
        self._operations_count += 1
        self._logger.info(f"除法计算: {a} / {b} = {result}")
        return result
    
    def get_operations_count(self) -> int:
        """获取操作次数"""
        return self._operations_count


class DataProcessorExtension(Extension):
    """数据处理器扩展"""
    
    def __init__(self):
        super().__init__(
            extension_id="data_processor",
            name="Data Processor Extension",
            version="1.0.0", 
            description="提供数据处理功能的扩展",
            author="MiniMax Agent",
            extension_type=ExtType.TOOL,
            capabilities={"data_processing", "text_operations"},
            dependencies=[
                ExtensionDependency("calculator", version_constraint=">=1.0.0", optional=False)
            ]
        )
        self._processed_items = 0
    
    def _do_initialize(self) -> bool:
        """初始化扩展"""
        self._logger.info("Data Processor扩展正在初始化...")
        return True
    
    def _do_activate(self) -> bool:
        """激活扩展"""
        self._logger.info("Data Processor扩展已激活！")
        return True
    
    def _do_deactivate(self) -> bool:
        """停用扩展"""
        self._logger.info("Data Processor扩展已停用")
        return True
    
    def _do_cleanup(self) -> bool:
        """清理扩展"""
        self._logger.info("Data Processor扩展已清理")
        return True
    
    def process_text(self, text: str) -> Dict[str, Any]:
        """处理文本数据"""
        words = text.split()
        chars = len(text)
        
        result = {
            "original_text": text,
            "word_count": len(words),
            "char_count": chars,
            "first_word": words[0] if words else "",
            "last_word": words[-1] if words else "",
            "processed_at": "2024-01-01T00:00:00Z"
        }
        
        self._processed_items += 1
        self._logger.info(f"文本处理完成: {result}")
        return result
    
    def process_numbers(self, numbers: List[float]) -> Dict[str, Any]:
        """处理数字数据"""
        if not numbers:
            raise ValueError("数字列表不能为空")
        
        import statistics
        
        result = {
            "original_numbers": numbers,
            "count": len(numbers),
            "sum": sum(numbers),
            "average": statistics.mean(numbers),
            "median": statistics.median(numbers),
            "min": min(numbers),
            "max": max(numbers),
            "processed_at": "2024-01-01T00:00:00Z"
        }
        
        self._processed_items += 1
        self._logger.info(f"数字处理完成: 平均值={result['average']:.2f}")
        return result
    
    def get_processed_count(self) -> int:
        """获取已处理项目数量"""
        return self._processed_items


def create_hello_world_extension():
    """创建Hello World扩展实例"""
    return HelloWorldExtension()


def create_calculator_extension():
    """创建计算器扩展实例"""
    return CalculatorExtension()


def create_data_processor_extension():
    """创建数据处理器扩展实例"""
    return DataProcessorExtension()


# 扩展工厂函数
EXTENSION_FACTORIES = {
    "hello_world": create_hello_world_extension,
    "calculator": create_calculator_extension,
    "data_processor": create_data_processor_extension
}


def get_extension_factory(extension_id: str):
    """获取扩展工厂函数"""
    return EXTENSION_FACTORIES.get(extension_id)


def list_available_extensions() -> List[Dict[str, str]]:
    """列出可用的扩展"""
    return [
        {
            "id": "hello_world",
            "name": "Hello World Extension",
            "description": "一个简单的Hello World示例扩展",
            "type": "custom"
        },
        {
            "id": "calculator", 
            "name": "Calculator Extension",
            "description": "提供基础计算功能的扩展",
            "type": "tool"
        },
        {
            "id": "data_processor",
            "name": "Data Processor Extension", 
            "description": "提供数据处理功能的扩展",
            "type": "tool"
        }
    ]


if __name__ == "__main__":
    # 演示扩展使用
    print("=== AgentBus 扩展系统演示 ===\n")
    
    # 创建扩展管理器
    from agentbus.extensions import ExtensionManager, ExtensionRegistry, ExtensionSandbox
    
    registry = ExtensionRegistry()
    sandbox = ExtensionSandbox()
    manager = ExtensionManager(sandbox=sandbox)
    
    # 创建并加载扩展
    extensions = [
        HelloWorldExtension(),
        CalculatorExtension(),
        DataProcessorExtension()
    ]
    
    print("1. 创建扩展实例...")
    for ext in extensions:
        print(f"   - {ext.name} ({ext.id})")
    
    print("\n2. 加载扩展...")
    for ext in extensions:
        if manager.load_extension(ext):
            print(f"   ✓ {ext.name} 加载成功")
        else:
            print(f"   ✗ {ext.name} 加载失败")
    
    print("\n3. 激活扩展...")
    for ext in extensions:
        if manager.activate_extension(ext.id):
            print(f"   ✓ {ext.name} 激活成功")
        else:
            print(f"   ✗ {ext.name} 激活失败")
    
    print("\n4. 测试扩展功能...")
    
    # 测试Hello World扩展
    hello_ext = manager.get_extension("hello_world")
    if hello_ext:
        result = hello_ext.say_hello("AgentBus")
        print(f"   Hello World: {result}")
    
    # 测试计算器扩展
    calc_ext = manager.get_extension("calculator")
    if calc_ext:
        result = calc_ext.add(10, 5)
        print(f"   计算器: 10 + 5 = {result}")
    
    # 测试数据处理器扩展
    data_ext = manager.get_extension("data_processor")
    if data_ext:
        result = data_ext.process_text("Hello, AgentBus Extension System!")
        print(f"   数据处理: {result['word_count']} words, {result['char_count']} chars")
    
    print("\n5. 扩展统计信息...")
    stats = manager.get_statistics()
    print(f"   总扩展数: {stats['registry_stats']['total_extensions']}")
    print(f"   活跃扩展数: {stats['registry_stats']['active_extensions']}")
    
    print("\n6. 停用并清理扩展...")
    for ext in extensions:
        if manager.deactivate_extension(ext.id):
            print(f"   ✓ {ext.name} 停用成功")
    
    print("\n=== 演示完成 ===")