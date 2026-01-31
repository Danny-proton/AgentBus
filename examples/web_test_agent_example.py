"""
AgentBus 网页测试Agent示例

演示如何使用浏览器自动化系统创建网页测试Agent
"""

from agents.core.base import BaseAgent
from agents.core.types import AgentConfig, AgentMetadata, AgentType
from automation.browser import BrowserAutomation, BrowserConfig
from typing import Dict, Any, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class WebTestAgent(BaseAgent):
    """网页测试Agent"""
    
    def __init__(self, config: AgentConfig):
        metadata = AgentMetadata(
            agent_id="web_test_agent",
            name="Web Test Agent",
            agent_type=AgentType.AUTOMATION,
            description="网页自动化测试Agent",
            version="1.0.0"
        )
        
        super().__init__(config, metadata)
        
        self.browser = None
        self.test_results = []
    
    async def initialize(self) -> bool:
        """初始化Agent"""
        try:
            # 初始化浏览器
            browser_config = BrowserConfig(
                headless=False,  # 显示浏览器窗口便于调试
                viewport_width=1920,
                viewport_height=1080
            )
            
            self.browser = BrowserAutomation(browser_config)
            await self.browser.start()
            
            self.logger.info("WebTestAgent 初始化成功")
            return await super().initialize()
            
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            return False
    
    async def shutdown(self):
        """关闭Agent"""
        if self.browser:
            await self.browser.stop()
        
        self.logger.info(f"WebTestAgent 已关闭,共执行 {len(self.test_results)} 个测试")
        await super().shutdown()
    
    async def generate_text(self, prompt: str,
                           system_prompt: Optional[str] = None,
                           context: Optional[List[Dict]] = None) -> str:
        """生成文本"""
        return f"AI分析: {prompt}"
    
    async def _handle_custom_task(self, task_type: str,
                                  parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理自定义任务"""
        
        if task_type == "navigate":
            return await self._task_navigate(parameters)
        
        elif task_type == "test_form":
            return await self._task_test_form(parameters)
        
        elif task_type == "test_links":
            return await self._task_test_links(parameters)
        
        elif task_type == "take_screenshot":
            return await self._task_screenshot(parameters)
        
        else:
            raise ValueError(f"未知任务类型: {task_type}")
    
    # ========== 任务处理函数 ==========
    
    async def _task_navigate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """导航任务"""
        url = params.get("url")
        
        self.logger.info(f"导航到: {url}")
        await self.browser.navigate_to(url)
        
        # 等待页面加载
        await asyncio.sleep(2)
        
        # 获取页面信息
        page_info = await self.browser.get_page_info()
        
        return {
            "success": True,
            "url": url,
            "title": page_info.get("title", ""),
            "loaded": True
        }
    
    async def _task_test_form(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """表单测试任务"""
        form_data = params.get("form_data", {})
        submit_selector = params.get("submit_selector", "button[type='submit']")
        
        results = []
        
        # 填写表单字段
        for field_selector, value in form_data.items():
            try:
                await self.browser.type_text(
                    selector=field_selector,
                    value=value
                )
                results.append({
                    "field": field_selector,
                    "success": True
                })
                self.logger.info(f"填写字段 {field_selector}: {value}")
                
            except Exception as e:
                results.append({
                    "field": field_selector,
                    "success": False,
                    "error": str(e)
                })
                self.logger.error(f"填写字段失败 {field_selector}: {e}")
        
        # 提交表单
        try:
            await self.browser.click_element(selector=submit_selector)
            await asyncio.sleep(2)
            
            submit_success = True
            self.logger.info("表单提交成功")
            
        except Exception as e:
            submit_success = False
            self.logger.error(f"表单提交失败: {e}")
        
        test_result = {
            "success": submit_success,
            "fields_filled": len([r for r in results if r["success"]]),
            "fields_failed": len([r for r in results if not r["success"]]),
            "details": results
        }
        
        self.test_results.append(test_result)
        return test_result
    
    async def _task_test_links(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """链接测试任务"""
        max_links = params.get("max_links", 10)
        
        # 查找所有链接
        links = await self.browser.find_elements(selector="a")
        
        results = []
        tested_count = 0
        
        for link in links[:max_links]:
            try:
                href = await link.get_attribute("href")
                text = await link.text_content()
                
                if href and href.startswith("http"):
                    results.append({
                        "url": href,
                        "text": text,
                        "valid": True
                    })
                    tested_count += 1
                    
            except Exception as e:
                self.logger.error(f"测试链接失败: {e}")
        
        return {
            "success": True,
            "total_links": len(links),
            "tested_links": tested_count,
            "valid_links": len(results),
            "links": results
        }
    
    async def _task_screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """截图任务"""
        full_page = params.get("full_page", False)
        
        filepath = await self.browser.take_screenshot(
            full_page=full_page
        )
        
        return {
            "success": True,
            "filepath": filepath,
            "full_page": full_page
        }


# ========== 使用示例 ==========

async def example_basic_navigation():
    """示例1: 基本导航"""
    print("\n=== 示例1: 基本导航 ===")
    
    config = AgentConfig(agent_id="web_test_001")
    agent = WebTestAgent(config)
    
    await agent.initialize()
    await agent.start()
    
    # 导航到网页
    result = await agent.execute_task(
        task_type="navigate",
        parameters={"url": "https://example.com"}
    )
    print(f"导航结果: {result}")
    
    # 截图
    screenshot = await agent.execute_task(
        task_type="take_screenshot",
        parameters={"full_page": True}
    )
    print(f"截图保存: {screenshot['filepath']}")
    
    await agent.stop()
    await agent.shutdown()


async def example_form_testing():
    """示例2: 表单测试"""
    print("\n=== 示例2: 表单测试 ===")
    
    config = AgentConfig(agent_id="web_test_002")
    agent = WebTestAgent(config)
    
    await agent.initialize()
    await agent.start()
    
    # 导航到表单页面
    await agent.execute_task(
        task_type="navigate",
        parameters={"url": "https://example.com/form"}
    )
    
    # 测试表单
    result = await agent.execute_task(
        task_type="test_form",
        parameters={
            "form_data": {
                "#username": "testuser",
                "#email": "test@example.com",
                "#message": "这是测试消息"
            },
            "submit_selector": "#submit-btn"
        }
    )
    print(f"表单测试结果: {result}")
    
    await agent.stop()
    await agent.shutdown()


async def example_link_validation():
    """示例3: 链接验证"""
    print("\n=== 示例3: 链接验证 ===")
    
    config = AgentConfig(agent_id="web_test_003")
    agent = WebTestAgent(config)
    
    await agent.initialize()
    await agent.start()
    
    # 导航到页面
    await agent.execute_task(
        task_type="navigate",
        parameters={"url": "https://example.com"}
    )
    
    # 测试链接
    result = await agent.execute_task(
        task_type="test_links",
        parameters={"max_links": 5}
    )
    print(f"链接测试结果:")
    print(f"  总链接数: {result['total_links']}")
    print(f"  有效链接数: {result['valid_links']}")
    for link in result['links']:
        print(f"  - {link['text']}: {link['url']}")
    
    await agent.stop()
    await agent.shutdown()


async def main():
    """运行所有示例"""
    # 选择要运行的示例
    await example_basic_navigation()
    # await example_form_testing()
    # await example_link_validation()


if __name__ == "__main__":
    asyncio.run(main())
