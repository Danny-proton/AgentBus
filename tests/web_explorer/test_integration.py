"""
WebExplorer Agent - 简单集成测试

验证核心流程是否可以正常运行
"""

import asyncio
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_basic_flow():
    """测试基本流程"""
    try:
        logger.info("=" * 60)
        logger.info("开始 WebExplorer Agent 基础流程测试")
        logger.info("=" * 60)
        
        # 导入组件
        from agents.web_explorer import WebExplorerAgent, ExplorerConfig
        
        # 创建配置
        config = ExplorerConfig(
            agent_id="test_explorer",
            start_url="http://example.com",  # 使用一个简单的测试网站
            max_depth=2,
            max_nodes=5,
            max_iterations=10,
            headless=False,  # 显示浏览器便于观察
            atlas_root="test_memory"
        )
        
        logger.info(f"配置: {config.start_url}, max_nodes={config.max_nodes}")
        
        # 创建Agent
        agent = WebExplorerAgent(config)
        
        # 初始化
        logger.info("初始化 Agent...")
        init_success = await agent.initialize()
        
        if not init_success:
            logger.error("Agent 初始化失败")
            return False
        
        logger.info("✅ Agent 初始化成功")
        
        # 开始探索
        logger.info("\n开始探索...")
        result = await agent.start_exploration()
        
        # 打印结果
        logger.info("\n" + "=" * 60)
        logger.info("探索完成!")
        logger.info("=" * 60)
        logger.info(f"总节点数: {result.get('total_nodes', 0)}")
        logger.info(f"总边数: {result.get('total_edges', 0)}")
        logger.info(f"最大深度: {result.get('max_depth_reached', 0)}")
        logger.info(f"Atlas路径: {result.get('atlas_path', 'N/A')}")
        
        # 检查Atlas结构
        atlas_path = Path(config.atlas_root)
        if atlas_path.exists():
            logger.info("\n检查 Atlas 结构:")
            
            # 检查index.json
            index_file = atlas_path / "index.json"
            if index_file.exists():
                import json
                index = json.loads(index_file.read_text())
                logger.info(f"  ✅ index.json 存在")
                logger.info(f"     节点数: {len(index.get('nodes', {}))}")
                logger.info(f"     统计: {index.get('statistics', {})}")
            
            # 检查节点目录
            node_dirs = [d for d in atlas_path.iterdir() if d.is_dir()]
            logger.info(f"  ✅ 节点目录数: {len(node_dirs)}")
            
            # 检查第一个节点的结构
            if node_dirs:
                first_node = node_dirs[0]
                logger.info(f"\n  检查节点: {first_node.name}")
                
                if (first_node / "meta.json").exists():
                    logger.info(f"    ✅ meta.json 存在")
                
                if (first_node / "links").exists():
                    logger.info(f"    ✅ links/ 目录存在")
                
                if (first_node / "scripts").exists():
                    logger.info(f"    ✅ scripts/ 目录存在")
                
                if (first_node / "todos").exists():
                    todos_dir = first_node / "todos"
                    task_files = list(todos_dir.glob("*.task"))
                    idea_files = list(todos_dir.glob("*.idea"))
                    logger.info(f"    ✅ todos/ 目录存在")
                    logger.info(f"       .task 文件: {len(task_files)}")
                    logger.info(f"       .idea 文件: {len(idea_files)}")
        
        # 关闭Agent
        logger.info("\n关闭 Agent...")
        await agent.shutdown()
        logger.info("✅ Agent 已关闭")
        
        logger.info("\n" + "=" * 60)
        logger.info("测试完成!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        return False


async def test_components():
    """测试各个组件是否可以正常创建"""
    try:
        logger.info("\n测试组件创建...")
        
        from plugins.core import PluginContext
        from plugins.web_explorer.atlas_manager import AtlasManagerPlugin
        from plugins.web_explorer.browser_manager import BrowserManagerPlugin
        from skills.web_explorer.page_analysis import PageAnalysisSkill
        from skills.web_explorer.trajectory_labeling import TrajectoryLabelingSkill
        
        # 测试 AtlasManager
        logger.info("  创建 AtlasManager...")
        context = PluginContext()
        atlas = AtlasManagerPlugin("test_atlas", context)
        await atlas.activate()
        logger.info("  ✅ AtlasManager 创建成功")
        await atlas.deactivate()
        
        # 测试 BrowserManager
        logger.info("  创建 BrowserManager...")
        browser = BrowserManagerPlugin("test_browser", context)
        await browser.activate()
        logger.info("  ✅ BrowserManager 创建成功")
        await browser.deactivate()
        
        # 测试 Skills
        logger.info("  创建 PageAnalysis Skill...")
        page_skill = PageAnalysisSkill()
        logger.info("  ✅ PageAnalysis Skill 创建成功")
        
        logger.info("  创建 TrajectoryLabeling Skill...")
        traj_skill = TrajectoryLabelingSkill()
        logger.info("  ✅ TrajectoryLabeling Skill 创建成功")
        
        logger.info("\n✅ 所有组件测试通过")
        return True
        
    except Exception as e:
        logger.error(f"组件测试失败: {e}", exc_info=True)
        return False


async def main():
    """主测试函数"""
    logger.info("WebExplorer Agent - 集成测试\n")
    
    # 测试1: 组件创建
    logger.info("【测试1】组件创建测试")
    logger.info("-" * 60)
    component_ok = await test_components()
    
    if not component_ok:
        logger.error("❌ 组件测试失败,终止测试")
        return
    
    # 测试2: 基本流程
    logger.info("\n【测试2】基本流程测试")
    logger.info("-" * 60)
    flow_ok = await test_basic_flow()
    
    if flow_ok:
        logger.info("\n🎉 所有测试通过!")
    else:
        logger.error("\n❌ 流程测试失败")


if __name__ == "__main__":
    asyncio.run(main())
