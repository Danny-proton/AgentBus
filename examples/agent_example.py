"""
AgentBus Agent开发示例

演示如何创建一个简单的Agent,执行任务和管理状态
"""

from agents.core.base import BaseAgent
from agents.core.types import (
    AgentConfig, AgentMetadata, AgentType, 
    AgentCapability, AgentStatus
)
from typing import Dict, Any, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class ExampleAgent(BaseAgent):
    """示例Agent - 演示基本功能"""
    
    def __init__(self, config: AgentConfig):
        # 创建元数据
        metadata = AgentMetadata(
            agent_id="example_agent",
            name="Example Agent",
            agent_type=AgentType.CUSTOM,
            description="示例Agent,演示任务执行和状态管理",
            version="1.0.0"
        )
        
        super().__init__(config, metadata)
        
        # 自定义属性
        self.task_history = []
        
        # 注册能力
        self._register_capabilities()
    
    def _register_capabilities(self):
        """注册Agent能力"""
        self.state.capabilities.add(
            AgentCapability(
                name="text_processing",
                description="文本处理能力",
                enabled=True
            )
        )
        
        self.state.capabilities.add(
            AgentCapability(
                name="data_analysis",
                description="数据分析能力",
                enabled=True
            )
        )
    
    async def initialize(self) -> bool:
        """初始化Agent"""
        try:
            self.logger.info("初始化 ExampleAgent")
            
            # 这里可以初始化资源
            # 例如: 连接数据库、加载模型等
            
            return await super().initialize()
            
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            return False
    
    async def shutdown(self):
        """关闭Agent"""
        self.logger.info(f"关闭 ExampleAgent,共执行 {len(self.task_history)} 个任务")
        
        # 清理资源
        self.task_history.clear()
        
        await super().shutdown()
    
    async def generate_text(self, prompt: str,
                           system_prompt: Optional[str] = None,
                           context: Optional[List[Dict]] = None) -> str:
        """生成文本(使用LLM)"""
        # 这里应该调用实际的LLM服务
        # 简化实现
        self.logger.info(f"生成文本: {prompt[:50]}...")
        return f"AI回复: 这是对'{prompt}'的响应"
    
    async def _handle_custom_task(self, task_type: str,
                                  parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理自定义任务"""
        self.logger.info(f"执行任务: {task_type}")
        
        # 记录任务历史
        self.task_history.append({
            "type": task_type,
            "params": parameters
        })
        
        # 根据任务类型分发
        if task_type == "process_text":
            return await self._task_process_text(parameters)
        
        elif task_type == "analyze_data":
            return await self._task_analyze_data(parameters)
        
        elif task_type == "generate_report":
            return await self._task_generate_report(parameters)
        
        else:
            raise ValueError(f"未知任务类型: {task_type}")
    
    # ========== 任务处理函数 ==========
    
    async def _task_process_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """文本处理任务"""
        text = params.get("text", "")
        operation = params.get("operation", "upper")
        
        if operation == "upper":
            result = text.upper()
        elif operation == "lower":
            result = text.lower()
        elif operation == "reverse":
            result = text[::-1]
        elif operation == "count":
            result = {
                "length": len(text),
                "words": len(text.split()),
                "chars": len(text.replace(" ", ""))
            }
        else:
            result = text
        
        return {
            "success": True,
            "operation": operation,
            "result": result
        }
    
    async def _task_analyze_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """数据分析任务"""
        data = params.get("data", [])
        
        if not data:
            return {
                "success": False,
                "error": "数据为空"
            }
        
        # 简单分析
        analysis = {
            "count": len(data),
            "sum": sum(data) if all(isinstance(x, (int, float)) for x in data) else None,
            "unique": len(set(data)),
            "sample": data[:5]
        }
        
        return {
            "success": True,
            "analysis": analysis
        }
    
    async def _task_generate_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成报告任务"""
        title = params.get("title", "报告")
        
        # 使用LLM生成报告
        prompt = f"生成一份关于'{title}'的报告"
        content = await self.generate_text(prompt)
        
        report = {
            "title": title,
            "content": content,
            "task_count": len(self.task_history),
            "agent_status": self.state.status.value
        }
        
        return {
            "success": True,
            "report": report
        }


# ========== 使用示例 ==========

async def main():
    """示例主函数"""
    
    # 1. 创建Agent配置
    config = AgentConfig(
        agent_id="example_001",
        model_provider="openai",
        model_name="gpt-4",
        max_tokens=1000,
        temperature=0.7
    )
    
    # 2. 创建Agent实例
    agent = ExampleAgent(config)
    
    # 3. 初始化
    success = await agent.initialize()
    if not success:
        print("Agent初始化失败")
        return
    
    # 4. 启动
    await agent.start()
    
    print(f"Agent状态: {agent.state.status}")
    print(f"Agent能力: {[c.name for c in agent.state.capabilities]}")
    
    # 5. 执行任务1: 文本处理
    result1 = await agent.execute_task(
        task_type="process_text",
        parameters={
            "text": "Hello AgentBus",
            "operation": "upper"
        }
    )
    print(f"\n任务1结果: {result1}")
    
    # 6. 执行任务2: 数据分析
    result2 = await agent.execute_task(
        task_type="analyze_data",
        parameters={
            "data": [1, 2, 3, 4, 5, 3, 2, 1]
        }
    )
    print(f"\n任务2结果: {result2}")
    
    # 7. 执行任务3: 生成报告
    result3 = await agent.execute_task(
        task_type="generate_report",
        parameters={
            "title": "AgentBus使用情况"
        }
    )
    print(f"\n任务3结果: {result3}")
    
    # 8. 获取Agent信息
    info = agent.get_info()
    print(f"\nAgent信息: {info}")
    
    # 9. 暂停和恢复
    await agent.pause()
    print(f"Agent状态: {agent.state.status}")
    
    await agent.resume()
    print(f"Agent状态: {agent.state.status}")
    
    # 10. 停止和关闭
    await agent.stop()
    await agent.shutdown()
    
    print("\nAgent已关闭")


if __name__ == "__main__":
    asyncio.run(main())
