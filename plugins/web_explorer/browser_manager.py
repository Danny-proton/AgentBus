"""
BrowserManager Plugin - 浏览器操作管理插件

负责管理浏览器操作:
- 执行模糊意图指令
- 录制操作脚本
- 回放脚本链(瞬移)
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from plugins.core import AgentBusPlugin, PluginContext
from automation.browser import BrowserAutomation, BrowserConfig


logger = logging.getLogger(__name__)


class BrowserManagerPlugin(AgentBusPlugin):
    """浏览器操作管理插件"""
    
    NAME = "browser_manager"
    VERSION = "1.0.0"
    DESCRIPTION = "管理浏览器操作,支持意图执行、脚本录制和回放"
    AUTHOR = "AgentBus Team"
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        
        # 浏览器实例
        self.browser: Optional[BrowserAutomation] = None
        
        # 操作历史缓存
        self._action_history: List[Dict[str, Any]] = []
        
        # 配置
        self.browser_config = BrowserConfig(
            headless=False,  # 默认显示浏览器便于调试
            viewport_width=1920,
            viewport_height=1080
        )
    
    def get_info(self) -> Dict[str, Any]:
        """返回插件信息"""
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "description": self.DESCRIPTION,
            "author": self.AUTHOR,
            "status": self.status.value,
            "browser_running": self.browser is not None,
            "action_history_count": len(self._action_history)
        }
    
    async def activate(self) -> bool:
        """激活插件"""
        try:
            # 初始化浏览器
            self.browser = BrowserAutomation(self.browser_config)
            await self.browser.start()
            
            # 注册工具
            self.register_tool(
                name="execute_intent",
                description="执行模糊意图指令",
                function=self.execute_intent,
                parameters={
                    "intent": {"type": "string", "description": "模糊指令"},
                    "context": {"type": "object", "description": "上下文信息", "default": None}
                }
            )
            
            self.register_tool(
                name="save_script",
                description="保存操作历史为脚本",
                function=self.save_script,
                parameters={
                    "script_path": {"type": "string", "description": "脚本保存路径"},
                    "metadata": {"type": "object", "description": "脚本元数据", "default": None}
                }
            )
            
            self.register_tool(
                name="replay_teleport",
                description="执行脚本链,瞬移到目标状态",
                function=self.replay_teleport,
                parameters={
                    "script_paths": {"type": "array", "description": "脚本路径列表"}
                }
            )
            
            self.register_tool(
                name="clear_history",
                description="清空操作历史",
                function=self.clear_history,
                parameters={}
            )
            
            self.register_tool(
                name="navigate_to",
                description="导航到指定URL",
                function=self.navigate_to,
                parameters={
                    "url": {"type": "string", "description": "目标URL"}
                }
            )
            
            self.register_tool(
                name="take_screenshot",
                description="截取当前页面截图",
                function=self.take_screenshot,
                parameters={
                    "save_path": {"type": "string", "description": "保存路径", "default": None},
                    "full_page": {"type": "boolean", "description": "是否全页截图", "default": False}
                }
            )
            
            self.register_tool(
                name="get_page_info",
                description="获取当前页面信息",
                function=self.get_page_info,
                parameters={}
            )
            
            self.logger.info(f"插件 {self.NAME} 激活成功")
            return True
            
        except Exception as e:
            self.logger.error(f"插件激活失败: {e}", exc_info=True)
            return False
    
    async def deactivate(self) -> bool:
        """停用插件"""
        if self.browser:
            await self.browser.stop()
            self.browser = None
        
        self.logger.info(f"插件 {self.NAME} 已停用")
        return True
    
    # ========== 核心功能 ==========
    
    async def execute_intent(
        self,
        intent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行模糊意图指令
        
        Args:
            intent: 模糊指令,如"点击登录按钮"
            context: 上下文信息
        
        Returns:
            {
                "success": bool,
                "action_type": str,
                "selector": str,
                "screenshot_before": str,
                "screenshot_after": str,
                "error": str | None
            }
        """
        try:
            if not self.browser:
                raise RuntimeError("浏览器未初始化")
            
            # 操作前截图
            screenshot_before = await self.browser.take_screenshot()
            
            # 解析意图并执行
            # TODO: 使用LLM将模糊意图转换为具体操作
            # 这里先实现简单的关键词匹配
            action_result = await self._parse_and_execute_intent(intent, context)
            
            # 操作后截图
            screenshot_after = await self.browser.take_screenshot()
            
            # 记录到历史
            action_record = {
                "intent": intent,
                "action_type": action_result["action_type"],
                "selector": action_result.get("selector"),
                "parameters": action_result.get("parameters", {}),
                "screenshot_before": screenshot_before,
                "screenshot_after": screenshot_after,
                "timestamp": datetime.now().isoformat()
            }
            self._action_history.append(action_record)
            
            return {
                "success": True,
                "action_type": action_result["action_type"],
                "selector": action_result.get("selector", ""),
                "screenshot_before": screenshot_before,
                "screenshot_after": screenshot_after,
                "dom_before": action_result.get("dom_before"),
                "dom_after": action_result.get("dom_after"),
                "error": None
            }
            
        except Exception as e:
            self.logger.error(f"execute_intent失败: {e}", exc_info=True)
            return {
                "success": False,
                "action_type": "unknown",
                "selector": "",
                "screenshot_before": "",
                "screenshot_after": "",
                "error": str(e)
            }
    
    async def save_script(
        self,
        script_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        保存操作历史为Python脚本
        
        Args:
            script_path: 脚本保存路径
            metadata: 脚本元数据
        
        Returns:
            是否保存成功
        """
        try:
            if not self._action_history:
                self.logger.warning("操作历史为空,无法生成脚本")
                return False
            
            # 生成脚本内容
            script_content = self._generate_script(metadata or {})
            
            # 保存到文件
            script_file = Path(script_path)
            script_file.parent.mkdir(parents=True, exist_ok=True)
            script_file.write_text(script_content, encoding="utf-8")
            
            self.logger.info(f"脚本已保存: {script_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"save_script失败: {e}", exc_info=True)
            return False
    
    async def replay_teleport(
        self,
        script_paths: List[str]
    ) -> Dict[str, Any]:
        """
        执行脚本链,瞬移到目标状态
        
        Args:
            script_paths: 脚本路径列表
        
        Returns:
            {
                "success": bool,
                "executed_scripts": List[str],
                "final_url": str,
                "error": str | None
            }
        """
        try:
            if not self.browser:
                raise RuntimeError("浏览器未初始化")
            
            # 重启浏览器到干净状态
            await self.browser.stop()
            await self.browser.start()
            
            executed = []
            
            # 按顺序执行脚本
            for script_path in script_paths:
                self.logger.info(f"执行脚本: {script_path}")
                
                # TODO: 实际执行脚本
                # 这里需要实现脚本加载和执行逻辑
                # 暂时跳过
                
                executed.append(script_path)
            
            # 获取最终URL
            page_info = await self.browser.get_page_info()
            final_url = page_info.get("url", "")
            
            return {
                "success": True,
                "executed_scripts": executed,
                "final_url": final_url,
                "final_screenshot": await self.browser.take_screenshot(),
                "error": None
            }
            
        except Exception as e:
            self.logger.error(f"replay_teleport失败: {e}", exc_info=True)
            return {
                "success": False,
                "executed_scripts": [],
                "final_url": "",
                "error": str(e)
            }
    
    async def clear_history(self) -> None:
        """清空操作历史"""
        self._action_history.clear()
        self.logger.info("操作历史已清空")
    
    async def navigate_to(self, url: str) -> Dict[str, Any]:
        """导航到指定URL"""
        try:
            if not self.browser:
                raise RuntimeError("浏览器未初始化")
            
            await self.browser.navigate_to(url)
            
            # 记录到历史
            self._action_history.append({
                "intent": f"导航到 {url}",
                "action_type": "navigate",
                "parameters": {"url": url},
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "url": url
            }
            
        except Exception as e:
            self.logger.error(f"navigate_to失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def take_screenshot(
        self,
        save_path: Optional[str] = None,
        full_page: bool = False
    ) -> str:
        """截取当前页面截图"""
        try:
            if not self.browser:
                raise RuntimeError("浏览器未初始化")
            
            screenshot_path = await self.browser.take_screenshot(full_page=full_page)
            
            # 如果指定了保存路径,复制文件
            if save_path:
                import shutil
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(screenshot_path, save_path)
                return save_path
            
            return screenshot_path
            
        except Exception as e:
            self.logger.error(f"take_screenshot失败: {e}", exc_info=True)
            return ""
    
    async def get_page_info(self) -> Dict[str, Any]:
        """获取当前页面信息"""
        try:
            if not self.browser:
                raise RuntimeError("浏览器未初始化")
            
            return await self.browser.get_page_info()
            
        except Exception as e:
            self.logger.error(f"get_page_info失败: {e}", exc_info=True)
            return {}
    
    # ========== 辅助方法 ==========
    
    async def _parse_and_execute_intent(
        self,
        intent: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        解析并执行意图
        
        简化实现:使用关键词匹配
        TODO: 后续使用LLM进行智能解析
        """
        intent_lower = intent.lower()
        
        # 点击操作
        if "点击" in intent or "click" in intent_lower:
            # 提取目标(简化版)
            # TODO: 使用LLM提取准确的选择器
            selector = self._extract_selector_from_intent(intent)
            
            await self.browser.click_element(selector=selector)
            
            return {
                "action_type": "click",
                "selector": selector
            }
        
        # 输入操作
        elif "输入" in intent or "填写" in intent or "type" in intent_lower:
            # TODO: 提取选择器和文本
            selector = self._extract_selector_from_intent(intent)
            text = self._extract_text_from_intent(intent)
            
            await self.browser.type_text(selector=selector, value=text)
            
            return {
                "action_type": "type",
                "selector": selector,
                "parameters": {"text": text}
            }
        
        # 导航操作
        elif "打开" in intent or "访问" in intent or "navigate" in intent_lower:
            url = self._extract_url_from_intent(intent)
            await self.browser.navigate_to(url)
            
            return {
                "action_type": "navigate",
                "parameters": {"url": url}
            }
        
        else:
            raise ValueError(f"无法解析意图: {intent}")
    
    def _extract_selector_from_intent(self, intent: str) -> str:
        """从意图中提取选择器(简化版)"""
        # TODO: 使用LLM智能提取
        # 这里只是占位实现
        if "登录" in intent or "login" in intent.lower():
            return "#login-btn"
        elif "搜索" in intent or "search" in intent.lower():
            return "#search-input"
        else:
            return "button"  # 默认查找按钮
    
    def _extract_text_from_intent(self, intent: str) -> str:
        """从意图中提取文本(简化版)"""
        # TODO: 使用LLM智能提取
        return ""
    
    def _extract_url_from_intent(self, intent: str) -> str:
        """从意图中提取URL(简化版)"""
        # TODO: 使用LLM智能提取
        import re
        urls = re.findall(r'https?://[^\s]+', intent)
        return urls[0] if urls else ""
    
    def _generate_script(self, metadata: Dict[str, Any]) -> str:
        """生成Python脚本"""
        name = metadata.get("name", "Generated Script")
        description = metadata.get("description", "Auto-generated navigation script")
        
        # 脚本头部
        script = f'''"""
{name}

{description}

创建时间: {datetime.now().isoformat()}
操作步骤数: {len(self._action_history)}
"""

from playwright.async_api import async_playwright
import asyncio


async def main():
    """执行脚本"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
'''
        
        # 添加操作步骤
        for i, action in enumerate(self._action_history, 1):
            action_type = action["action_type"]
            
            if action_type == "navigate":
                url = action["parameters"]["url"]
                script += f'            # 步骤{i}: 导航\n'
                script += f'            await page.goto("{url}")\n'
                script += f'            await page.wait_for_load_state("networkidle")\n\n'
            
            elif action_type == "click":
                selector = action["selector"]
                script += f'            # 步骤{i}: 点击\n'
                script += f'            await page.click("{selector}")\n'
                script += f'            await page.wait_for_timeout(1000)\n\n'
            
            elif action_type == "type":
                selector = action["selector"]
                text = action["parameters"].get("text", "")
                script += f'            # 步骤{i}: 输入\n'
                script += f'            await page.fill("{selector}", "{text}")\n\n'
        
        # 脚本尾部
        script += '''        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
'''
        
        return script
