"""
WebExplorer Agent - 使用示例

演示如何使用WebExplorer Agent进行网页探索
"""

import asyncio
import logging
from pathlib import Path

from agents.web_explorer import WebExplorerAgent, ExplorerConfig


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def example_basic_exploration():
    """示例1: 基础网页探索"""
    logger.info("=== 示例1: 基础网页探索 ===")
    
    # 创建配置
    config = ExplorerConfig(
        agent_id="explorer_001",
        start_url="http://127.0.0.1:8080",  # Mock Server地址
        max_depth=3,
        max_nodes=20,
        headless=False,  # 显示浏览器
        atlas_root="project_memory"
    )
    
    # 创建Agent
    agent = WebExplorerAgent(config)
    
    try:
        # 初始化
        await agent.initialize()
        
        # 开始探索
        result = await agent.start_exploration()
        
        # 打印结果
        logger.info(f"探索完成:")
        logger.info(f"  总节点数: {result['total_nodes']}")
        logger.info(f"  总边数: {result['total_edges']}")
        logger.info(f"  最大深度: {result['max_depth_reached']}")
        logger.info(f"  Atlas路径: {result['atlas_path']}")
        
    finally:
        # 关闭Agent
        await agent.shutdown()


async def example_custom_config():
    """示例2: 自定义配置"""
    logger.info("=== 示例2: 自定义配置 ===")
    
    config = ExplorerConfig(
        agent_id="explorer_002",
        start_url="https://example.com",
        max_depth=5,
        max_nodes=50,
        max_iterations=500,
        headless=True,  # 无头模式
        atlas_root="custom_memory",
        model_provider="openai",
        model_name="gpt-4",
        debug=True
    )
    
    agent = WebExplorerAgent(config)
    
    try:
        await agent.initialize()
        result = await agent.start_exploration()
        logger.info(f"探索结果: {result}")
    finally:
        await agent.shutdown()


async def example_monitor_status():
    """示例3: 监控探索状态"""
    logger.info("=== 示例3: 监控探索状态 ===")
    
    config = ExplorerConfig(
        agent_id="explorer_003",
        start_url="http://127.0.0.1:8080",
        max_nodes=10
    )
    
    agent = WebExplorerAgent(config)
    
    try:
        await agent.initialize()
        
        # 启动探索(异步)
        exploration_task = asyncio.create_task(
            agent.start_exploration()
        )
        
        # 定期检查状态
        while not exploration_task.done():
            status = await agent.get_status()
            logger.info(f"当前状态: {status}")
            await asyncio.sleep(2)
        
        # 获取结果
        result = await exploration_task
        logger.info(f"最终结果: {result}")
        
    finally:
        await agent.shutdown()


async def example_analyze_atlas():
    """示例4: 分析Atlas结果"""
    logger.info("=== 示例4: 分析Atlas结果 ===")
    
    atlas_path = Path("project_memory")
    
    if not atlas_path.exists():
        logger.warning("Atlas目录不存在,请先运行探索")
        return
    
    # 读取索引文件
    import json
    index_file = atlas_path / "index.json"
    
    if index_file.exists():
        index = json.loads(index_file.read_text())
        
        logger.info("Atlas统计信息:")
        logger.info(f"  版本: {index.get('version')}")
        logger.info(f"  创建时间: {index.get('created_at')}")
        logger.info(f"  总节点数: {index['statistics']['total_nodes']}")
        logger.info(f"  总边数: {index['statistics']['total_edges']}")
        logger.info(f"  最大深度: {index['statistics']['max_depth']}")
        
        logger.info("\n节点列表:")
        for node_id, node_info in index['nodes'].items():
            logger.info(f"  {node_id}: {node_info['url']}")


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python example_usage.py basic      # 基础探索")
        print("  python example_usage.py custom     # 自定义配置")
        print("  python example_usage.py monitor    # 监控状态")
        print("  python example_usage.py analyze    # 分析结果")
        return
    
    example = sys.argv[1]
    
    if example == "basic":
        asyncio.run(example_basic_exploration())
    elif example == "custom":
        asyncio.run(example_custom_config())
    elif example == "monitor":
        asyncio.run(example_monitor_status())
    elif example == "analyze":
        asyncio.run(example_analyze_atlas())
    else:
        print(f"未知示例: {example}")


if __name__ == "__main__":
    main()
