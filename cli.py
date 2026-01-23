#!/usr/bin/env python3
"""
AgentBus CLI 启动脚本
支持两种模式：
1. Server 模式：启动 FastAPI 服务（默认）
2. Direct 模式：直接执行任务（--task）
"""

import argparse
import sys
import os
import asyncio
import logging
from uuid import uuid4

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def run_direct_task(task: str, model: str = None):
    """直接执行任务"""
    from config.settings import get_settings
    from core.memory.short_term import ShortTermMemory
    from services.cost_tracker import CostTracker
    from services.log_service import init_log_service, start_log_service, stop_log_service
    from services.workspace import init_workspace
    from tools.knowledge_bus import init_knowledge_bus
    from core.llm.client import LLMClient
    from core.llm.manager import ModelManager
    from tools.registry import ToolRegistry
    from core.agent.loop import AgentLoop
    from tools.human_in_loop import init_human_loop

    # 配置简易日志
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger("agentbus.cli")
    logger.setLevel(logging.INFO)
    
    print(f"🚀 Starting AgentBus Direct Mode...")
    print(f"📋 Task: {task}")
    
    # 初始化服务
    settings = get_settings()
    
    # 1. 基础服务
    workspace = init_workspace(settings.workspace.path)
    log_service = init_log_service(workspace.get_logs_path(), enabled=True)
    await start_log_service()
    
    knowledge_bus = init_knowledge_bus(settings.workspace.path)
    
    # 2. 核心组件
    llm_client = LLMClient(settings)
    model_manager = ModelManager(settings, llm_client)
    cost_tracker = CostTracker()
    
    # 3. 工具注册
    tool_registry = ToolRegistry()
    
    # 注册基础工具
    from tools.terminal import register_terminal_tools
    from tools.knowledge_bus import create_knowledge_bus_tool
    
    # 注册 Knowledge Bus 工具
    kb_tool = create_knowledge_bus_tool(knowledge_bus)
    await tool_registry.register(kb_tool, category="memory")
    
    # 注册 Terminal 工具 (Safe Mode = False for CLI)
    # TODO: 以后可以从 Runtime/Env 获取 environment
    from runtime.local import LocalEnvironment
    env = LocalEnvironment(workspace)
    await register_terminal_tools(tool_registry, env, safe_mode=False)
    
    # 注册 Skills (如果存在)
    try:
        from tools.skills import register_skills_tools
        await register_skills_tools(tool_registry, env)
    except ImportError:
        pass

    # 4. Agent Loop
    memory = ShortTermMemory(max_messages=settings.memory.max_messages)
    
    loop = AgentLoop(
        session_id=str(uuid4()),
        memory=memory,
        llm_client=llm_client,
        model_manager=model_manager,
        tool_registry=tool_registry,
        workspace=workspace.get_path()
    )
    
    # 5. 执行循环
    try:
        print("\n🤖 Agent is thinking...\n")
        
        async for chunk in loop.process(task, model=model, stream=True):
            if chunk.chunk:
                print(chunk.chunk, end="", flush=True)
                
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
    finally:
        await stop_log_service()
        print("\n\n✅ Done.")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="AgentBus AI Programming Assistant"
    )
    
    # Direct Mode Arguments
    parser.add_argument(
        "--task", "-t",
        type=str,
        help="Execute a task directly without starting the server"
    )
    
    parser.add_argument(
        "--model", "-m",
        type=str,
        help="Specify model for direct execution"
    )

    # Server Mode Arguments
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Server host (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of workers"
    )
    
    args = parser.parse_args()
    
    if args.task:
        # Direct Mode
        try:
            asyncio.run(run_direct_task(args.task, args.model))
        except ImportError as e:
            print(f"❌ Import Error: {e}")
            print("Make sure you are in the correct directory and dependencies are installed.")
            sys.exit(1)
    else:
        # Server Mode
        import uvicorn
        from main import app
        
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1
        )


if __name__ == "__main__":
    main()
