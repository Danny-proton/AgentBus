"""
WebExplorer Agent - 网页探索Agent

实现自主网页遍历和测试功能
"""

import asyncio
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from agents.core.base import BaseAgent
from agents.core.types import AgentConfig, AgentMetadata, AgentType

from .types import ExplorerState, ExplorerConfig, NodeInfo, ExplorationResult
from .fsm import ExplorerFSM
from plugins.web_explorer.atlas_manager import AtlasManagerPlugin
from plugins.web_explorer.browser_manager import BrowserManagerPlugin
from skills.web_explorer.page_analysis import PageAnalysisSkill
from skills.web_explorer.trajectory_labeling import TrajectoryLabelingSkill


logger = logging.getLogger(__name__)


class WebExplorerAgent(BaseAgent):
    """网页探索Agent"""
    
    def __init__(self, config: ExplorerConfig):
        # 创建Agent元数据
        metadata = AgentMetadata(
            agent_id=config.agent_id,
            name="WebExplorer Agent",
            agent_type=AgentType.AUTOMATION,
            description="自主网页遍历和测试Agent",
            version="1.0.0"
        )
        
        # 创建基础Agent配置
        agent_config = AgentConfig(
            agent_id=config.agent_id,
            model_provider=config.model_provider,
            model_name=config.model_name,
            temperature=config.temperature
        )
        
        super().__init__(agent_config, metadata)
        
        # Explorer配置
        self.explorer_config = config
        
        # 状态机
        self.fsm = ExplorerFSM()
        
        # 组件
        self.atlas_manager: Optional[AtlasManagerPlugin] = None
        self.browser_manager: Optional[BrowserManagerPlugin] = None
        self.page_analysis: Optional[PageAnalysisSkill] = None
        self.trajectory_labeling: Optional[TrajectoryLabelingSkill] = None
        
        # 运行时状态
        self.current_node: Optional[NodeInfo] = None
        self.visited_nodes: set = set()
        self.iteration_count = 0
        self.exploration_result = ExplorationResult()
    
    async def initialize(self) -> bool:
        """初始化Agent"""
        try:
            self.logger.info("初始化 WebExplorer Agent")
            
            # 初始化组件
            from plugins.core import PluginContext
            
            # 创建插件上下文
            context = PluginContext()
            
            # 初始化AtlasManager
            self.atlas_manager = AtlasManagerPlugin("atlas_manager", context)
            await self.atlas_manager.activate()
            
            # 初始化BrowserManager
            self.browser_manager = BrowserManagerPlugin("browser_manager", context)
            await self.browser_manager.activate()
            
            # 初始化Skills
            self.page_analysis = PageAnalysisSkill()
            self.trajectory_labeling = TrajectoryLabelingSkill()
            
            self.logger.info("所有组件初始化完成")
            
            return await super().initialize()
            
        except Exception as e:
            self.logger.error(f"初始化失败: {e}", exc_info=True)
            return False
    
    async def shutdown(self):
        """关闭Agent"""
        self.logger.info("关闭 WebExplorer Agent")
        
        # 停用组件
        if self.atlas_manager:
            await self.atlas_manager.deactivate()
        
        if self.browser_manager:
            await self.browser_manager.deactivate()
        
        await super().shutdown()
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[Dict]] = None
    ) -> str:
        """生成文本(使用LLM)"""
        # TODO: 实际调用LLM服务
        # 这里返回模拟响应
        return f"AI响应: {prompt}"
    
    # ========== 主要功能 ==========
    
    async def start_exploration(
        self,
        start_url: Optional[str] = None,
        max_depth: Optional[int] = None,
        max_nodes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        启动拓荒循环
        
        Args:
            start_url: 起始URL
            max_depth: 最大深度
            max_nodes: 最大节点数
        
        Returns:
            探索结果
        """
        try:
            # 更新配置
            if start_url:
                self.explorer_config.start_url = start_url
            if max_depth:
                self.explorer_config.max_depth = max_depth
            if max_nodes:
                self.explorer_config.max_nodes = max_nodes
            
            self.logger.info(f"开始探索: {self.explorer_config.start_url}")
            
            # 导航到起始URL
            await self.browser_manager.navigate_to(self.explorer_config.start_url)
            
            # 重置状态
            self.visited_nodes.clear()
            self.iteration_count = 0
            self.fsm.reset()
            
            # 执行拓荒循环
            await self._exploration_loop()
            
            # 返回结果
            return {
                "total_nodes": self.exploration_result.total_nodes,
                "total_edges": self.exploration_result.total_edges,
                "max_depth_reached": self.exploration_result.max_depth_reached,
                "atlas_path": str(Path(self.explorer_config.atlas_root).absolute())
            }
            
        except Exception as e:
            self.logger.error(f"探索失败: {e}", exc_info=True)
            return {
                "total_nodes": 0,
                "total_edges": 0,
                "error": str(e)
            }
    
    async def start_testing(
        self,
        atlas_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        启动深测循环
        
        Args:
            atlas_path: Atlas目录路径
        
        Returns:
            测试结果
        """
        try:
            self.logger.info("开始深度测试")
            
            # TODO: 实现深测循环
            # 这里先返回占位结果
            
            return {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "report_path": ""
            }
            
        except Exception as e:
            self.logger.error(f"测试失败: {e}", exc_info=True)
            return {
                "total_tests": 0,
                "error": str(e)
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            "state": self.fsm.current_state.value,
            "current_node": self.current_node.node_id if self.current_node else None,
            "nodes_explored": len(self.visited_nodes),
            "iteration_count": self.iteration_count,
            "max_iterations": self.explorer_config.max_iterations
        }
    
    # ========== 拓荒循环 ==========
    
    async def _exploration_loop(self):
        """
        拓荒循环主逻辑
        
        状态流转:
        IDLE -> LOCATING -> ANALYZING -> DECIDING -> ACTING -> REFLECTING -> LOCATING
                                             ↓
                                       BACKTRACKING (无任务时)
        """
        self.fsm.transition(ExplorerState.LOCATING)
        
        while (self.fsm.current_state != ExplorerState.COMPLETED and
               self.iteration_count < self.explorer_config.max_iterations):
            
            self.iteration_count += 1
            self.logger.info(f"迭代 {self.iteration_count}, 状态: {self.fsm.current_state.value}")
            
            try:
                if self.fsm.current_state == ExplorerState.LOCATING:
                    await self._locate_current_state()
                
                elif self.fsm.current_state == ExplorerState.ANALYZING:
                    await self._analyze_page()
                
                elif self.fsm.current_state == ExplorerState.DECIDING:
                    await self._decide_next_action()
                
                elif self.fsm.current_state == ExplorerState.ACTING:
                    await self._execute_action()
                
                elif self.fsm.current_state == ExplorerState.REFLECTING:
                    await self._reflect_on_action()
                
                elif self.fsm.current_state == ExplorerState.BACKTRACKING:
                    await self._backtrack()
                
                # 检查完成条件
                if len(self.visited_nodes) >= self.explorer_config.max_nodes:
                    self.logger.info("达到最大节点数,完成探索")
                    self.fsm.transition(ExplorerState.COMPLETED)
                
            except Exception as e:
                self.logger.error(f"循环错误: {e}", exc_info=True)
                self.fsm.transition(ExplorerState.ERROR)
                break
        
        self.logger.info(f"探索完成,共访问 {len(self.visited_nodes)} 个节点")
    
    async def _locate_current_state(self):
        """定位当前状态"""
        try:
            # 获取当前页面信息
            page_info = await self.browser_manager.get_page_info()
            url = page_info.get("url", "")
            
            # 截图
            screenshot_path = await self.browser_manager.take_screenshot()
            
            # 计算DOM指纹
            dom_fingerprint = self._calculate_dom_fingerprint(page_info)
            
            # 确保状态节点存在
            result = await self.atlas_manager.ensure_state(
                url=url,
                dom_fingerprint=dom_fingerprint,
                screenshot_path=screenshot_path,
                metadata={"title": page_info.get("title", "")}
            )
            
            node_id = result["node_id"]
            is_new = result["is_new"]
            
            # 更新当前节点
            self.current_node = NodeInfo(
                node_id=node_id,
                url=url,
                depth=0  # TODO: 计算实际深度
            )
            
            # 记录访问
            self.visited_nodes.add(node_id)
            
            # 检查是否有待创建的链接
            if hasattr(self, '_pending_link') and self._pending_link:
                source_node_id = self._pending_link.get("source_node_id")
                action_name = self._pending_link.get("action_name")
                
                if source_node_id and action_name:
                    # 创建从源节点到当前节点的链接
                    success = await self.atlas_manager.link_state(
                        source_node_id=source_node_id,
                        action_name=action_name,
                        target_node_id=node_id
                    )
                    
                    if success:
                        self.logger.info(f"创建链接: {source_node_id} --[{action_name}]--> {node_id}")
                        self.exploration_result.total_edges += 1
                
                # 清除待创建的链接
                self._pending_link = None
            
            if is_new:
                self.exploration_result.total_nodes += 1
                self.logger.info(f"发现新节点: {node_id}")
                # 新节点需要分析
                self.fsm.transition(ExplorerState.ANALYZING)
            else:
                self.logger.info(f"已访问节点: {node_id}")
                # 已访问节点,直接决策
                self.fsm.transition(ExplorerState.DECIDING)
            
        except Exception as e:
            self.logger.error(f"定位状态失败: {e}", exc_info=True)
            self.fsm.transition(ExplorerState.ERROR)
    
    async def _analyze_page(self):
        """分析页面"""
        try:
            # 获取页面信息
            page_info = await self.browser_manager.get_page_info()
            screenshot_path = await self.browser_manager.take_screenshot()
            
            # 调用PageAnalysis技能
            analysis_result = await self.page_analysis.execute(
                action="analyze",
                parameters={
                    "screenshot_path": screenshot_path,
                    "dom_tree": page_info,
                    "url": page_info.get("url", "")
                }
            )
            
            # 将frontier_tasks推送到待办队列
            frontier_tasks = analysis_result.get("frontier_tasks", [])
            if frontier_tasks:
                await self.atlas_manager.manage_todos(
                    node_id=self.current_node.node_id,
                    mode="push",
                    tasks=frontier_tasks
                )
                self.logger.info(f"推送 {len(frontier_tasks)} 个导航任务到队列")
            
            # 将test_ideas也推送到待办队列(会被保存为.idea文件)
            test_ideas = analysis_result.get("test_ideas", [])
            if test_ideas:
                await self.atlas_manager.manage_todos(
                    node_id=self.current_node.node_id,
                    mode="push",
                    tasks=test_ideas
                )
                self.logger.info(f"推送 {len(test_ideas)} 个测试想法到队列")
            
            # 转到决策状态
            self.fsm.transition(ExplorerState.DECIDING)
            
        except Exception as e:
            self.logger.error(f"页面分析失败: {e}", exc_info=True)
            self.fsm.transition(ExplorerState.ERROR)
    
    async def _decide_next_action(self):
        """决策下一步动作"""
        try:
            # 从待办队列获取任务
            tasks = await self.atlas_manager.manage_todos(
                node_id=self.current_node.node_id,
                mode="pop"
            )
            
            if tasks:
                # 有任务,执行第一个
                self.current_task = tasks[0]
                self.logger.info(f"选择任务: {self.current_task.get('selector')}")
                self.fsm.transition(ExplorerState.ACTING)
            else:
                # 无任务,回溯
                self.logger.info("无待办任务,准备回溯")
                self.fsm.transition(ExplorerState.BACKTRACKING)
            
        except Exception as e:
            self.logger.error(f"决策失败: {e}", exc_info=True)
            self.fsm.transition(ExplorerState.ERROR)
    
    async def _execute_action(self):
        """执行动作"""
        try:
            if not hasattr(self, 'current_task'):
                self.fsm.transition(ExplorerState.DECIDING)
                return
            
            task = self.current_task
            action_type = task.get("action", "click")
            selector = task.get("selector", "")
            
            # 构建意图描述
            intent = f"{action_type} {selector}"
            
            # 执行意图
            result = await self.browser_manager.execute_intent(
                intent=intent,
                context={"task": task}
            )
            
            # 保存执行结果供反思使用
            self.last_action_result = result
            
            if result["success"]:
                self.logger.info(f"动作执行成功: {intent}")
                self.fsm.transition(ExplorerState.REFLECTING)
            else:
                self.logger.warning(f"动作执行失败: {result.get('error')}")
                # 失败也要反思
                self.fsm.transition(ExplorerState.REFLECTING)
            
        except Exception as e:
            self.logger.error(f"执行动作失败: {e}", exc_info=True)
            self.fsm.transition(ExplorerState.ERROR)
    
    async def _reflect_on_action(self):
        """反思动作结果"""
        try:
            if not hasattr(self, 'last_action_result'):
                self.fsm.transition(ExplorerState.LOCATING)
                return
            
            result = self.last_action_result
            current_task = getattr(self, 'current_task', {})
            
            # 调用TrajectoryLabeling技能
            labeling_result = await self.trajectory_labeling.execute(
                action="label",
                parameters={
                    "screenshot_before": result.get("screenshot_before", ""),
                    "action_description": current_task.get("reason", ""),
                    "screenshot_after": result.get("screenshot_after", ""),
                    "dom_before": result.get("dom_before", {}),
                    "dom_after": result.get("dom_after", {})
                }
            )
            
            is_meaningful = labeling_result.get("is_meaningful", False)
            
            if is_meaningful:
                self.logger.info(f"动作有意义: {labeling_result.get('semantic_label')}")
                
                # 保存当前节点ID(作为源节点)
                source_node_id = self.current_node.node_id if self.current_node else None
                
                # 等待页面稳定
                await asyncio.sleep(1)
                
                # 保存脚本到当前节点
                if source_node_id:
                    script_name = labeling_result.get("script_name", "action.py")
                    script_path = f"project_memory/{source_node_id}/scripts/{script_name}"
                    
                    # 保存脚本
                    await self.browser_manager.save_script(
                        script_path=script_path,
                        metadata={
                            "name": script_name,
                            "description": labeling_result.get("semantic_label", ""),
                            "created_at": datetime.now().isoformat()
                        }
                    )
                    self.logger.info(f"脚本已保存: {script_path}")
                
                # 定位新状态
                self.fsm.transition(ExplorerState.LOCATING)
                
                # 等待定位完成后创建链接
                # 注意:这里需要在下一次循环中,当新节点创建后再创建链接
                # 我们保存源节点信息供后续使用
                self._pending_link = {
                    "source_node_id": source_node_id,
                    "action_name": labeling_result.get("script_name", "action").replace(".py", ""),
                    "semantic_label": labeling_result.get("semantic_label", "")
                }
                
            else:
                self.logger.info("动作无意义,继续决策")
                # 无意义,继续当前节点的其他任务
                self.fsm.transition(ExplorerState.DECIDING)
            
        except Exception as e:
            self.logger.error(f"反思失败: {e}", exc_info=True)
            self.fsm.transition(ExplorerState.ERROR)
    
    async def _backtrack(self):
        """回溯到父节点"""
        try:
            self.logger.info("执行回溯")
            
            # TODO: 实现实际的回溯逻辑
            # 1. 浏览器后退
            # 2. 切换到父节点
            # 3. 继续决策
            
            # 暂时标记为完成
            self.fsm.transition(ExplorerState.COMPLETED)
            
        except Exception as e:
            self.logger.error(f"回溯失败: {e}", exc_info=True)
            self.fsm.transition(ExplorerState.ERROR)
    
    # ========== 辅助方法 ==========
    
    def _calculate_dom_fingerprint(self, page_info: Dict[str, Any]) -> str:
        """计算DOM指纹"""
        # 简化实现:使用URL和title的组合
        url = page_info.get("url", "")
        title = page_info.get("title", "")
        
        combined = f"{url}::{title}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    async def _handle_custom_task(
        self,
        task_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理自定义任务"""
        if task_type == "explore":
            return await self.start_exploration(
                start_url=parameters.get("start_url"),
                max_depth=parameters.get("max_depth"),
                max_nodes=parameters.get("max_nodes")
            )
        elif task_type == "test":
            return await self.start_testing(
                atlas_path=parameters.get("atlas_path")
            )
        else:
            raise ValueError(f"未知任务类型: {task_type}")
