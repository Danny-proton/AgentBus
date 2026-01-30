"""
AgentBus Element Finder

基于Moltbot实现的元素查找器，提供页面元素查找、操作等功能。
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from playwright.async_api import Page, ElementHandle, Locator, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class ElementFinder:
    """元素查找器"""
    
    def __init__(self, page: Page):
        """
        初始化元素查找器
        
        Args:
            page: Playwright页面实例
        """
        self.page = page
        
    async def find_element(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        css: Optional[str] = None,
        timeout: int = 5000,
        visible_only: bool = True
    ) -> Optional[ElementHandle]:
        """
        查找单个元素
        
        Args:
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            css: CSS选择器
            timeout: 超时时间
            visible_only: 只查找可见元素
            
        Returns:
            Optional[ElementHandle]: 元素句柄
        """
        try:
            if text:
                # 根据文本查找
                if visible_only:
                    element = await self.page.wait_for_selector(f"text={text}", timeout=timeout)
                else:
                    elements = await self.page.query_selector_all(f"text={text}")
                    element = elements[0] if elements else None
                    
            elif xpath:
                # XPath查找
                if visible_only:
                    element = await self.page.wait_for_selector(f"xpath={xpath}", timeout=timeout)
                else:
                    elements = await self.page.query_selector_all(f"xpath={xpath}")
                    element = elements[0] if elements else None
                    
            elif css:
                # CSS选择器查找
                if visible_only:
                    element = await self.page.wait_for_selector(css, timeout=timeout)
                else:
                    elements = await self.page.query_selector_all(css)
                    element = elements[0] if elements else None
                    
            elif selector:
                # 默认选择器查找
                if visible_only:
                    element = await self.page.wait_for_selector(selector, timeout=timeout)
                else:
                    elements = await self.page.query_selector_all(selector)
                    element = elements[0] if elements else None
                    
            else:
                logger.error("必须提供选择器、文本或XPath")
                return None
                
            return element
            
        except PlaywrightTimeoutError:
            logger.debug(f"元素查找超时: {selector or text or xpath}")
            return None
        except Exception as e:
            logger.error(f"查找元素失败: {e}")
            return None
            
    async def find_elements(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        css: Optional[str] = None,
        timeout: int = 5000,
        visible_only: bool = True,
        limit: Optional[int] = None
    ) -> List[ElementHandle]:
        """
        查找多个元素
        
        Args:
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            css: CSS选择器
            timeout: 超时时间
            visible_only: 只查找可见元素
            limit: 限制返回数量
            
        Returns:
            List[ElementHandle]: 元素句柄列表
        """
        try:
            elements: List[ElementHandle] = []
            
            if text:
                # 根据文本查找
                all_elements = await self.page.query_selector_all(f"text={text}")
                if visible_only:
                    for element in all_elements:
                        if await element.is_visible():
                            elements.append(element)
                            if limit and len(elements) >= limit:
                                break
                else:
                    elements = all_elements[:limit] if limit else all_elements
                    
            elif xpath:
                # XPath查找
                all_elements = await self.page.query_selector_all(f"xpath={xpath}")
                if visible_only:
                    for element in all_elements:
                        if await element.is_visible():
                            elements.append(element)
                            if limit and len(elements) >= limit:
                                break
                else:
                    elements = all_elements[:limit] if limit else all_elements
                    
            elif css:
                # CSS选择器查找
                all_elements = await self.page.query_selector_all(css)
                if visible_only:
                    for element in all_elements:
                        if await element.is_visible():
                            elements.append(element)
                            if limit and len(elements) >= limit:
                                break
                else:
                    elements = all_elements[:limit] if limit else all_elements
                    
            elif selector:
                # 默认选择器查找
                all_elements = await self.page.query_selector_all(selector)
                if visible_only:
                    for element in all_elements:
                        if await element.is_visible():
                            elements.append(element)
                            if limit and len(elements) >= limit:
                                break
                else:
                    elements = all_elements[:limit] if limit else all_elements
                    
            else:
                logger.error("必须提供选择器、文本或XPath")
                return []
                
            return elements
            
        except Exception as e:
            logger.error(f"查找多个元素失败: {e}")
            return []
            
    async def click_element(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        element: Optional[ElementHandle] = None,
        force: bool = False,
        timeout: int = 5000
    ) -> bool:
        """
        点击元素
        
        Args:
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            element: 元素句柄
            force: 强制点击
            timeout: 超时时间
            
        Returns:
            bool: 是否成功
        """
        try:
            if element is None:
                element = await self.find_element(
                    selector=selector,
                    text=text,
                    xpath=xpath,
                    timeout=timeout
                )
                
            if not element:
                return False
                
            if force:
                await element.click(force=force)
            else:
                await element.click()
                
            logger.debug(f"元素点击成功")
            return True
            
        except Exception as e:
            logger.error(f"点击元素失败: {e}")
            return False
            
    async def type_text(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        element: Optional[ElementHandle] = None,
        value: str = "",
        clear_first: bool = True,
        timeout: int = 5000
    ) -> bool:
        """
        输入文本
        
        Args:
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            element: 元素句柄
            value: 要输入的值
            clear_first: 是否先清除
            timeout: 超时时间
            
        Returns:
            bool: 是否成功
        """
        try:
            if element is None:
                element = await self.find_element(
                    selector=selector,
                    text=text,
                    xpath=xpath,
                    timeout=timeout
                )
                
            if not element:
                return False
                
            if clear_first:
                await element.fill("")
                
            await element.fill(value)
            logger.debug(f"文本输入成功: {value}")
            return True
            
        except Exception as e:
            logger.error(f"输入文本失败: {e}")
            return False
            
    async def get_element_info(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        element: Optional[ElementHandle] = None
    ) -> Dict[str, Any]:
        """
        获取元素信息
        
        Args:
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            element: 元素句柄
            
        Returns:
            Dict: 元素信息
        """
        try:
            if element is None:
                element = await self.find_element(
                    selector=selector,
                    text=text,
                    xpath=xpath
                )
                
            if not element:
                return {}
                
            # 获取元素属性和状态
            info = await element.evaluate("""
                (el) => {
                    const rect = el.getBoundingClientRect();
                    const computedStyle = window.getComputedStyle(el);
                    return {
                        tag_name: el.tagName.toLowerCase(),
                        text: el.textContent,
                        inner_text: el.innerText,
                        value: el.value,
                        type: el.type,
                        name: el.name,
                        id: el.id,
                        class_name: el.className,
                        attributes: Object.fromEntries(
                            Array.from(el.attributes).map(attr => [attr.name, attr.value])
                        ),
                        visible: el.offsetWidth > 0 && el.offsetHeight > 0,
                        enabled: !el.disabled,
                        checked: el.checked,
                        selected: el.selected,
                        position: {
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        },
                        styles: {
                            display: computedStyle.display,
                            visibility: computedStyle.visibility,
                            opacity: computedStyle.opacity,
                            background_color: computedStyle.backgroundColor,
                            color: computedStyle.color,
                            font_size: computedStyle.fontSize
                        }
                    };
                }
            """)
            
            return info
            
        except Exception as e:
            logger.error(f"获取元素信息失败: {e}")
            return {}
            
    async def wait_for_element(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        timeout: int = 5000,
        state: str = "visible"
    ) -> bool:
        """
        等待元素出现
        
        Args:
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            timeout: 超时时间
            state: 等待状态 (visible, hidden, attached, detached)
            
        Returns:
            bool: 是否成功
        """
        try:
            wait_selector = selector
            
            if text:
                wait_selector = f"text={text}"
            elif xpath:
                wait_selector = f"xpath={xpath}"
                
            if not wait_selector:
                logger.error("必须提供选择器、文本或XPath")
                return False
                
            await self.page.wait_for_selector(wait_selector, timeout=timeout, state=state)
            return True
            
        except PlaywrightTimeoutError:
            logger.debug(f"等待元素超时: {wait_selector}")
            return False
        except Exception as e:
            logger.error(f"等待元素失败: {e}")
            return False
            
    async def wait_for_element_hidden(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        timeout: int = 5000
    ) -> bool:
        """
        等待元素隐藏
        
        Args:
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            timeout: 超时时间
            
        Returns:
            bool: 是否成功
        """
        return await self.wait_for_element(
            selector=selector,
            text=text,
            xpath=xpath,
            timeout=timeout,
            state="hidden"
        )
        
    async def is_element_visible(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        element: Optional[ElementHandle] = None
    ) -> bool:
        """
        检查元素是否可见
        
        Args:
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            element: 元素句柄
            
        Returns:
            bool: 是否可见
        """
        try:
            if element is None:
                element = await self.find_element(
                    selector=selector,
                    text=text,
                    xpath=xpath
                )
                
            if not element:
                return False
                
            return await element.is_visible()
            
        except Exception as e:
            logger.error(f"检查元素可见性失败: {e}")
            return False
            
    async def is_element_enabled(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        element: Optional[ElementHandle] = None
    ) -> bool:
        """
        检查元素是否可用
        
        Args:
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            element: 元素句柄
            
        Returns:
            bool: 是否可用
        """
        try:
            if element is None:
                element = await self.find_element(
                    selector=selector,
                    text=text,
                    xpath=xpath
                )
                
            if not element:
                return False
                
            return await element.is_enabled()
            
        except Exception as e:
            logger.error(f"检查元素可用性失败: {e}")
            return False
            
    async def get_element_text(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        element: Optional[ElementHandle] = None
    ) -> str:
        """
        获取元素文本
        
        Args:
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            element: 元素句柄
            
        Returns:
            str: 元素文本
        """
        try:
            if element is None:
                element = await self.find_element(
                    selector=selector,
                    text=text,
                    xpath=xpath
                )
                
            if not element:
                return ""
                
            return await element.text_content() or ""
            
        except Exception as e:
            logger.error(f"获取元素文本失败: {e}")
            return ""
            
    async def get_element_attribute(
        self,
        attribute: str,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        element: Optional[ElementHandle] = None
    ) -> Optional[str]:
        """
        获取元素属性
        
        Args:
            attribute: 属性名
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            element: 元素句柄
            
        Returns:
            Optional[str]: 属性值
        """
        try:
            if element is None:
                element = await self.find_element(
                    selector=selector,
                    text=text,
                    xpath=xpath
                )
                
            if not element:
                return None
                
            return await element.get_attribute(attribute)
            
        except Exception as e:
            logger.error(f"获取元素属性失败: {e}")
            return None
            
    async def hover_element(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        element: Optional[ElementHandle] = None,
        timeout: int = 5000
    ) -> bool:
        """
        悬停在元素上
        
        Args:
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            element: 元素句柄
            timeout: 超时时间
            
        Returns:
            bool: 是否成功
        """
        try:
            if element is None:
                element = await self.find_element(
                    selector=selector,
                    text=text,
                    xpath=xpath,
                    timeout=timeout
                )
                
            if not element:
                return False
                
            await element.hover()
            return True
            
        except Exception as e:
            logger.error(f"悬停元素失败: {e}")
            return False
            
    async def double_click_element(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        xpath: Optional[str] = None,
        element: Optional[ElementHandle] = None,
        timeout: int = 5000
    ) -> bool:
        """
        双击元素
        
        Args:
            selector: CSS选择器
            text: 文本内容
            xpath: XPath表达式
            element: 元素句柄
            timeout: 超时时间
            
        Returns:
            bool: 是否成功
        """
        try:
            if element is None:
                element = await self.find_element(
                    selector=selector,
                    text=text,
                    xpath=xpath,
                    timeout=timeout
                )
                
            if not element:
                return False
                
            await element.dblclick()
            return True
            
        except Exception as e:
            logger.error(f"双击元素失败: {e}")
            return False
            
    async def drag_and_drop(
        self,
        source_selector: str,
        target_selector: str,
        timeout: int = 5000
    ) -> bool:
        """
        拖拽元素
        
        Args:
            source_selector: 源元素选择器
            target_selector: 目标元素选择器
            timeout: 超时时间
            
        Returns:
            bool: 是否成功
        """
        try:
            source_element = await self.page.wait_for_selector(source_selector, timeout=timeout)
            target_element = await self.page.wait_for_selector(target_selector, timeout=timeout)
            
            if not source_element or not target_element:
                return False
                
            await source_element.drag_to(target_element)
            return True
            
        except Exception as e:
            logger.error(f"拖拽元素失败: {e}")
            return False
            
    async def find_by_placeholder(self, placeholder: str) -> Optional[ElementHandle]:
        """根据placeholder查找元素"""
        return await self.find_element(selector=f"[placeholder='{placeholder}']")
        
    async def find_by_text_content(self, text: str) -> Optional[ElementHandle]:
        """根据文本内容查找元素"""
        return await self.find_element(text=text)
        
    async def find_by_xpath(self, xpath: str) -> Optional[ElementHandle]:
        """根据XPath查找元素"""
        return await self.find_element(xpath=xpath)
        
    async def find_by_tag(self, tag: str) -> List[ElementHandle]:
        """根据标签名查找元素"""
        return await self.find_elements(selector=tag)
        
    async def find_by_class(self, class_name: str) -> List[ElementHandle]:
        """根据class名查找元素"""
        return await self.find_elements(selector=f".{class_name}")
        
    async def find_by_id(self, id_name: str) -> Optional[ElementHandle]:
        """根据ID查找元素"""
        return await self.find_element(selector=f"#{id_name}")
        
    async def find_links(self) -> List[ElementHandle]:
        """查找所有链接"""
        return await self.find_elements(selector="a[href]")
        
    async def find_images(self) -> List[ElementHandle]:
        """查找所有图片"""
        return await self.find_elements(selector="img")
        
    async def find_forms(self) -> List[ElementHandle]:
        """查找所有表单"""
        return await self.find_elements(selector="form")
        
    async def find_buttons(self) -> List[ElementHandle]:
        """查找所有按钮"""
        return await self.find_elements(selector="button, input[type=button], input[type=submit]")