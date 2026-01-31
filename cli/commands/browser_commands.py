"""
浏览器管理CLI命令
Browser Management CLI Commands

基于Moltbot的浏览器CLI系统，提供完整的浏览器自动化管理功能。
"""

import asyncio
import json
import click
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
from loguru import logger

from automation.browser import BrowserAutomation, BrowserConfig, BrowserStatus, TabInfo
from automation.playwright_manager import PlaywrightManager
from automation.screenshot import ScreenshotManager
from automation.page_navigator import PageNavigator
from automation.element_finder import ElementFinder
from automation.form_handler import FormHandler


class BrowserCommands:
    """浏览器管理命令类"""
    
    def __init__(self, browser_automation: Optional[BrowserAutomation] = None):
        self.browser_automation = browser_automation or BrowserAutomation()
    
    async def start_browser(self, headless: bool = False, profile: Optional[str] = None,
                          proxy: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """启动浏览器"""
        try:
            # 创建浏览器配置
            config = BrowserConfig(
                headless=headless,
                proxy=proxy,
                **{k: v for k, v in kwargs.items() if hasattr(BrowserConfig, k)}
            )
            
            # 重新配置浏览器自动化
            if self.browser_automation:
                self.browser_automation.config = config
            else:
                self.browser_automation = BrowserAutomation(config)
            
            # 启动浏览器
            await self.browser_automation.start()
            
            # 获取状态信息
            status = await self.get_browser_status()
            
            return {
                "success": True,
                "message": "浏览器启动成功",
                "status": status,
                "config": {
                    "headless": headless,
                    "profile": profile,
                    "proxy": proxy,
                    **kwargs
                }
            }
            
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def stop_browser(self) -> Dict[str, Any]:
        """停止浏览器"""
        try:
            if not self.browser_automation:
                return {
                    "success": False,
                    "error": "浏览器未启动"
                }
            
            await self.browser_automation.stop()
            
            return {
                "success": True,
                "message": "浏览器已停止"
            }
            
        except Exception as e:
            logger.error(f"停止浏览器失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def restart_browser(self, headless: Optional[bool] = None,
                           **kwargs) -> Dict[str, Any]:
        """重启浏览器"""
        try:
            # 保存当前配置
            current_config = self.browser_automation.config if self.browser_automation else None
            
            # 停止浏览器
            await self.stop_browser()
            
            # 启动浏览器（使用新配置或当前配置）
            config_updates = {}
            if headless is not None:
                config_updates['headless'] = headless
            config_updates.update(kwargs)
            
            return await self.start_browser(**config_updates)
            
        except Exception as e:
            logger.error(f"重启浏览器失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_browser_status(self) -> Dict[str, Any]:
        """获取浏览器状态"""
        try:
            if not self.browser_automation:
                return {
                    "running": False,
                    "message": "浏览器未初始化"
                }
            
            status = await self.browser_automation.get_status()
            
            return {
                "running": status.running,
                "browser": {
                    "type": type(status.browser).__name__ if status.browser else None,
                    "version": status.version,
                    "executable_path": status.executable_path
                } if status.browser else None,
                "context": {
                    "active": status.context is not None
                } if status.context else None,
                "tabs": [
                    {
                        "target_id": tab.target_id,
                        "title": tab.title,
                        "url": tab.url,
                        "type": tab.type
                    } for tab in status.pages
                ] if status.pages else [],
                "pid": status.pid
            }
            
        except Exception as e:
            logger.error(f"获取浏览器状态失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def navigate_to(self, url: str, wait_until: str = "load") -> Dict[str, Any]:
        """导航到URL"""
        try:
            if not self.browser_automation or not self.browser_automation._browser:
                return {
                    "success": False,
                    "error": "浏览器未启动"
                }
            
            page = await self.browser_automation.create_page()
            await page.goto(url, wait_until=wait_until)
            
            return {
                "success": True,
                "message": f"已导航到 {url}",
                "url": url,
                "title": await page.title()
            }
            
        except Exception as e:
            logger.error(f"导航到 {url} 失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def take_screenshot(self, path: Optional[Path] = None, 
                            full_page: bool = False) -> Dict[str, Any]:
        """截取屏幕截图"""
        try:
            if not self.browser_automation or not self.browser_automation._browser:
                return {
                    "success": False,
                    "error": "浏览器未启动"
                }
            
            # 获取当前页面
            pages = self.browser_automation._browser.contexts[0].pages if self.browser_automation._browser.contexts else []
            if not pages:
                return {
                    "success": False,
                    "error": "没有可用的页面"
                }
            
            page = pages[-1]  # 使用最后一个页面
            
            # 设置截图路径
            if not path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = Path(f"screenshot_{timestamp}.png")
            
            # 截取截图
            await page.screenshot(path=path, full_page=full_page)
            
            return {
                "success": True,
                "message": "截图已保存",
                "path": str(path),
                "full_page": full_page,
                "title": await page.title(),
                "url": page.url
            }
            
        except Exception as e:
            logger.error(f"截取截图失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_script(self, script: str) -> Dict[str, Any]:
        """执行JavaScript脚本"""
        try:
            if not self.browser_automation or not self.browser_automation._browser:
                return {
                    "success": False,
                    "error": "浏览器未启动"
                }
            
            pages = self.browser_automation._browser.contexts[0].pages if self.browser_automation._browser.contexts else []
            if not pages:
                return {
                    "success": False,
                    "error": "没有可用的页面"
                }
            
            page = pages[-1]
            result = await page.evaluate(script)
            
            return {
                "success": True,
                "result": result,
                "script": script
            }
            
        except Exception as e:
            logger.error(f"执行脚本失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def find_element(self, selector: str, by: str = "css") -> Dict[str, Any]:
        """查找页面元素"""
        try:
            if not self.browser_automation or not self.browser_automation._browser:
                return {
                    "success": False,
                    "error": "浏览器未启动"
                }
            
            pages = self.browser_automation._browser.contexts[0].pages if self.browser_automation._browser.contexts else []
            if not pages:
                return {
                    "success": False,
                    "error": "没有可用的页面"
                }
            
            page = pages[-1]
            
            # 根据查找方式选择方法
            if by == "css":
                element = await page.query_selector(selector)
            elif by == "xpath":
                element = await page.query_selector(f"xpath={selector}")
            else:
                return {
                    "success": False,
                    "error": f"不支持的查找方式: {by}"
                }
            
            if element:
                # 获取元素信息
                bounding_box = await element.bounding_box()
                text_content = await element.text_content()
                tag_name = await element.evaluate("el => el.tagName")
                
                return {
                    "success": True,
                    "found": True,
                    "element": {
                        "tag": tag_name,
                        "text": text_content,
                        "selector": selector,
                        "bounding_box": bounding_box
                    }
                }
            else:
                return {
                    "success": True,
                    "found": False,
                    "selector": selector,
                    "message": "未找到指定元素"
                }
            
        except Exception as e:
            logger.error(f"查找元素失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def fill_form(self, form_data: Dict[str, str]) -> Dict[str, Any]:
        """填写表单"""
        try:
            if not self.browser_automation or not self.browser_automation._browser:
                return {
                    "success": False,
                    "error": "浏览器未启动"
                }
            
            pages = self.browser_automation._browser.contexts[0].pages if self.browser_automation._browser.contexts else []
            if not pages:
                return {
                    "success": False,
                    "error": "没有可用的页面"
                }
            
            page = pages[-1]
            filled_count = 0
            errors = []
            
            for field_name, value in form_data.items():
                try:
                    # 尝试通过名称或ID查找输入框
                    input_element = await page.query_selector(f'input[name="{field_name}"], input[id="{field_name}"], textarea[name="{field_name}"], textarea[id="{field_name}"]')
                    
                    if input_element:
                        await input_element.fill(value)
                        filled_count += 1
                    else:
                        errors.append(f"字段 '{field_name}' 未找到")
                        
                except Exception as e:
                    errors.append(f"字段 '{field_name}' 填写失败: {e}")
            
            return {
                "success": True,
                "filled_count": filled_count,
                "total_fields": len(form_data),
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"填写表单失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def click_element(self, selector: str, by: str = "css") -> Dict[str, Any]:
        """点击元素"""
        try:
            if not self.browser_automation or not self.browser_automation._browser:
                return {
                    "success": False,
                    "error": "浏览器未启动"
                }
            
            pages = self.browser_automation._browser.contexts[0].pages if self.browser_automation._browser.contexts else []
            if not pages:
                return {
                    "success": False,
                    "error": "没有可用的页面"
                }
            
            page = pages[-1]
            
            # 根据查找方式选择方法
            if by == "css":
                element = await page.query_selector(selector)
            elif by == "xpath":
                element = await page.query_selector(f"xpath={selector}")
            else:
                return {
                    "success": False,
                    "error": f"不支持的查找方式: {by}"
                }
            
            if element:
                await element.click()
                return {
                    "success": True,
                    "message": f"已点击元素: {selector}",
                    "selector": selector
                }
            else:
                return {
                    "success": False,
                    "error": f"元素未找到: {selector}"
                }
            
        except Exception as e:
            logger.error(f"点击元素失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_page_info(self) -> Dict[str, Any]:
        """获取页面信息"""
        try:
            if not self.browser_automation or not self.browser_automation._browser:
                return {
                    "success": False,
                    "error": "浏览器未启动"
                }
            
            pages = self.browser_automation._browser.contexts[0].pages if self.browser_automation._browser.contexts else []
            if not pages:
                return {
                    "success": False,
                    "error": "没有可用的页面"
                }
            
            page = pages[-1]
            
            # 获取页面信息
            title = await page.title()
            url = page.url
            content = await page.content()
            
            # 统计元素数量
            elements_count = await page.evaluate("""
                () => {
                    return {
                        links: document.querySelectorAll('a').length,
                        images: document.querySelectorAll('img').length,
                        forms: document.querySelectorAll('form').length,
                        inputs: document.querySelectorAll('input').length,
                        buttons: document.querySelectorAll('button').length
                    }
                }
            """)
            
            return {
                "success": True,
                "page": {
                    "title": title,
                    "url": url,
                    "content_length": len(content),
                    "elements": elements_count
                }
            }
            
        except Exception as e:
            logger.error(f"获取页面信息失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_tabs(self) -> Dict[str, Any]:
        """列出所有标签页"""
        try:
            if not self.browser_automation or not self.browser_automation._browser:
                return {
                    "success": False,
                    "error": "浏览器未启动"
                }
            
            pages = self.browser_automation._browser.contexts[0].pages if self.browser_automation._browser.contexts else []
            
            tabs = []
            for i, page in enumerate(pages):
                tabs.append({
                    "index": i,
                    "title": await page.title(),
                    "url": page.url,
                    "target_id": page.target._target_id
                })
            
            return {
                "success": True,
                "tabs": tabs,
                "total": len(tabs),
                "active_tab": len(pages) - 1  # 最后一个标签是活动的
            }
            
        except Exception as e:
            logger.error(f"列出标签页失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def new_tab(self, url: Optional[str] = None) -> Dict[str, Any]:
        """新建标签页"""
        try:
            if not self.browser_automation or not self.browser_automation._browser:
                return {
                    "success": False,
                    "error": "浏览器未启动"
                }
            
            context = self.browser_automation._browser.contexts[0]
            page = await context.new_page()
            
            if url:
                await page.goto(url)
            
            return {
                "success": True,
                "message": "新标签页已创建",
                "tab_index": len(context.pages) - 1,
                "url": url
            }
            
        except Exception as e:
            logger.error(f"新建标签页失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def close_tab(self, tab_index: Optional[int] = None) -> Dict[str, Any]:
        """关闭标签页"""
        try:
            if not self.browser_automation or not self.browser_automation._browser:
                return {
                    "success": False,
                    "error": "浏览器未启动"
                }
            
            context = self.browser_automation._browser.contexts[0]
            pages = context.pages
            
            if not pages:
                return {
                    "success": False,
                    "error": "没有可用的标签页"
                }
            
            # 确定要关闭的标签页
            if tab_index is None:
                target_page = pages[-1]  # 关闭最后一个标签页
            elif 0 <= tab_index < len(pages):
                target_page = pages[tab_index]
            else:
                return {
                    "success": False,
                    "error": f"标签页索引无效: {tab_index}"
                }
            
            await target_page.close()
            
            return {
                "success": True,
                "message": f"标签页已关闭",
                "closed_tab_index": tab_index or len(pages) - 1
            }
            
        except Exception as e:
            logger.error(f"关闭标签页失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def set_proxy(self, proxy: str) -> Dict[str, Any]:
        """设置代理"""
        try:
            if not self.browser_automation:
                return {
                    "success": False,
                    "error": "浏览器未初始化"
                }
            
            # 更新代理设置
            self.browser_automation.config.proxy = proxy
            
            # 如果浏览器正在运行，需要重启才能应用新设置
            if self.browser_automation._browser:
                await self.restart_browser(proxy=proxy)
                return {
                    "success": True,
                    "message": "代理设置已更新，浏览器已重启",
                    "proxy": proxy
                }
            else:
                return {
                    "success": True,
                    "message": "代理设置已更新，将在下次启动时应用",
                    "proxy": proxy
                }
            
        except Exception as e:
            logger.error(f"设置代理失败: {e}")
            return {"success": False, "error": str(e)}


def create_browser_commands(browser_automation: Optional[BrowserAutomation] = None) -> BrowserCommands:
    """创建浏览器命令实例"""
    return BrowserCommands(browser_automation)


# CLI命令组
@click.group()
def browser():
    """浏览器管理命令"""
    pass


@browser.command()
@click.option('--headless', '-h', is_flag=True, help='无头模式')
@click.option('--profile', '-p', help='浏览器档案名')
@click.option('--proxy', help='代理设置 (格式: host:port)')
@click.option('--width', default=1920, help='窗口宽度')
@click.option('--height', default=1080, help='窗口高度')
@click.option('--timeout', default=30000, help='超时时间(ms)')
@click.pass_context
def start(ctx, headless, profile, proxy, width, height, timeout):
    """启动浏览器"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _start():
        commands = create_browser_commands(browser_automation)
        result = await commands.start_browser(
            headless=headless,
            profile=profile,
            proxy=proxy,
            viewport_width=width,
            viewport_height=height,
            timeout=timeout
        )
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            status = result['status']
            click.echo(f"   运行状态: {'运行中' if status['running'] else '未运行'}")
            if status.get('browser'):
                click.echo(f"   浏览器: {status['browser'].get('version', 'unknown')}")
            click.echo(f"   无头模式: {headless}")
            if proxy:
                click.echo(f"   代理: {proxy}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_start())
    except Exception as e:
        click.echo(f"❌ 启动浏览器失败: {e}", err=True)


@browser.command()
@click.pass_context
def stop(ctx):
    """停止浏览器"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _stop():
        commands = create_browser_commands(browser_automation)
        result = await commands.stop_browser()
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_stop())
    except Exception as e:
        click.echo(f"❌ 停止浏览器失败: {e}", err=True)


@browser.command()
@click.option('--headless', '-h', is_flag=True, help='无头模式')
@click.option('--proxy', help='代理设置')
@click.pass_context
def restart(ctx, headless, proxy):
    """重启浏览器"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _restart():
        commands = create_browser_commands(browser_automation)
        kwargs = {}
        if headless:
            kwargs['headless'] = headless
        if proxy:
            kwargs['proxy'] = proxy
        
        result = await commands.restart_browser(**kwargs)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_restart())
    except Exception as e:
        click.echo(f"❌ 重启浏览器失败: {e}", err=True)


@browser.command()
@click.pass_context
def status(ctx):
    """查看浏览器状态"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _status():
        commands = create_browser_commands(browser_automation)
        result = await commands.get_browser_status()
        
        if result.get('running'):
            click.echo("🟢 浏览器状态: 运行中")
            if result.get('browser'):
                browser_info = result['browser']
                click.echo(f"   浏览器: {browser_info.get('version', 'unknown')}")
                if browser_info.get('executable_path'):
                    click.echo(f"   路径: {browser_info['executable_path']}")
            
            if result.get('pid'):
                click.echo(f"   进程ID: {result['pid']}")
            
            if result.get('tabs'):
                click.echo(f"   标签页: {len(result['tabs'])} 个")
                for i, tab in enumerate(result['tabs']):
                    status = "📄" if i == result.get('active_tab', -1) else "📑"
                    click.echo(f"     {status} [{i}] {tab['title']} - {tab['url']}")
        else:
            click.echo("🔴 浏览器状态: 未运行")
            if result.get('message'):
                click.echo(f"   信息: {result['message']}")
    
    try:
        asyncio.run(_status())
    except Exception as e:
        click.echo(f"❌ 获取浏览器状态失败: {e}", err=True)


@browser.command()
@click.argument('url')
@click.option('--wait', 'wait_until', default='load', type=click.Choice(['load', 'domcontentloaded', 'networkidle']), help='等待条件')
@click.pass_context
def navigate(ctx, url, wait_until):
    """导航到URL"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _navigate():
        commands = create_browser_commands(browser_automation)
        result = await commands.navigate_to(url, wait_until)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            click.echo(f"   标题: {result['title']}")
            click.echo(f"   URL: {result['url']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_navigate())
    except Exception as e:
        click.echo(f"❌ 导航失败: {e}", err=True)


@browser.command()
@click.option('--output', '-o', help='截图保存路径')
@click.option('--full-page', '-f', is_flag=True, help='完整页面截图')
@click.pass_context
def screenshot(ctx, output, full_page):
    """截取屏幕截图"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _screenshot():
        commands = create_browser_commands(browser_automation)
        path = Path(output) if output else None
        result = await commands.take_screenshot(path, full_page)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            click.echo(f"   文件: {result['path']}")
            click.echo(f"   标题: {result['title']}")
            click.echo(f"   URL: {result['url']}")
            if full_page:
                click.echo("   类型: 完整页面截图")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_screenshot())
    except Exception as e:
        click.echo(f"❌ 截图失败: {e}", err=True)


@browser.command()
@click.argument('script')
@click.pass_context
def eval(ctx, script):
    """执行JavaScript脚本"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _eval():
        commands = create_browser_commands(browser_automation)
        result = await commands.execute_script(script)
        
        if result['success']:
            click.echo(f"✅ 脚本执行成功")
            click.echo(f"   结果: {json.dumps(result['result'], indent=2, ensure_ascii=False)}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_eval())
    except Exception as e:
        click.echo(f"❌ 执行脚本失败: {e}", err=True)


@browser.command()
@click.argument('selector')
@click.option('--by', 'by_method', default='css', type=click.Choice(['css', 'xpath']), help='查找方式')
@click.pass_context
def find(ctx, selector, by_method):
    """查找页面元素"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _find():
        commands = create_browser_commands(browser_automation)
        result = await commands.find_element(selector, by_method)
        
        if result['success']:
            if result['found']:
                click.echo(f"✅ 找到元素: {selector}")
                element = result['element']
                click.echo(f"   标签: {element['tag']}")
                if element['text']:
                    click.echo(f"   文本: {element['text'][:100]}{'...' if len(element['text']) > 100 else ''}")
                if element['bounding_box']:
                    bbox = element['bounding_box']
                    click.echo(f"   位置: x={bbox['x']:.0f}, y={bbox['y']:.0f}, width={bbox['width']:.0f}, height={bbox['height']:.0f}")
            else:
                click.echo(f"❌ 未找到元素: {selector}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_find())
    except Exception as e:
        click.echo(f"❌ 查找元素失败: {e}", err=True)


@browser.command(name='click')
@click.argument('selector')
@click.option('--by', 'by_method', default='css', type=click.Choice(['css', 'xpath']), help='查找方式')
@click.pass_context
def click_element_cmd(ctx, selector, by_method):
    """点击元素"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _click():
        commands = create_browser_commands(browser_automation)
        result = await commands.click_element(selector, by_method)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_click())
    except Exception as e:
        click.echo(f"❌ 点击元素失败: {e}", err=True)


@browser.command()
@click.option('--json-format', 'json_output', is_flag=True, help='JSON格式输出')
@click.pass_context
def info(ctx, json_output):
    """获取页面信息"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _info():
        commands = create_browser_commands(browser_automation)
        result = await commands.get_page_info()
        
        if result['success']:
            if json_output:
                click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                page_info = result['page']
                click.echo(f"📄 页面信息")
                click.echo(f"   标题: {page_info['title']}")
                click.echo(f"   URL: {page_info['url']}")
                click.echo(f"   内容长度: {page_info['content_length']} 字符")
                click.echo(f"   元素统计:")
                for element_type, count in page_info['elements'].items():
                    click.echo(f"     {element_type}: {count}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_info())
    except Exception as e:
        click.echo(f"❌ 获取页面信息失败: {e}", err=True)


@browser.command()
@click.option('--json-format', 'json_output', is_flag=True, help='JSON格式输出')
@click.pass_context
def tabs(ctx, json_output):
    """列出所有标签页"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _tabs():
        commands = create_browser_commands(browser_automation)
        result = await commands.list_tabs()
        
        if result['success']:
            if json_output:
                click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                click.echo(f"🏷️ 标签页列表 (总计: {result['total']})")
                for tab in result['tabs']:
                    status = "📄 活动" if tab['index'] == result['active_tab'] else "📑"
                    click.echo(f"   {status} [{tab['index']}] {tab['title']}")
                    click.echo(f"      {tab['url']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_tabs())
    except Exception as e:
        click.echo(f"❌ 列出标签页失败: {e}", err=True)


@browser.command()
@click.argument('url', required=False)
@click.pass_context
def tab_new(ctx, url):
    """新建标签页"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _tab_new():
        commands = create_browser_commands(browser_automation)
        result = await commands.new_tab(url)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            click.echo(f"   标签页索引: {result['tab_index']}")
            if result.get('url'):
                click.echo(f"   URL: {result['url']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_tab_new())
    except Exception as e:
        click.echo(f"❌ 新建标签页失败: {e}", err=True)


@browser.command()
@click.argument('index', type=int, required=False)
@click.pass_context
def tab_close(ctx, index):
    """关闭标签页"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _tab_close():
        commands = create_browser_commands(browser_automation)
        result = await commands.close_tab(index)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            click.echo(f"   关闭的标签页: {result['closed_tab_index']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_tab_close())
    except Exception as e:
        click.echo(f"❌ 关闭标签页失败: {e}", err=True)


@browser.command()
@click.argument('proxy')
@click.pass_context
def proxy_set(ctx, proxy):
    """设置代理"""
    browser_automation = ctx.obj.get('browser_automation')
    
    async def _proxy_set():
        commands = create_browser_commands(browser_automation)
        result = await commands.set_proxy(proxy)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            click.echo(f"   代理: {result['proxy']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_proxy_set())
    except Exception as e:
        click.echo(f"❌ 设置代理失败: {e}", err=True)