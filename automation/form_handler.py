"""
AgentBus Form Handler

基于Moltbot实现的表单处理器，提供表单填写、提交等功能。
"""

import logging
from typing import Dict, List, Optional, Union, Any
from playwright.async_api import Page, ElementHandle, Locator

logger = logging.getLogger(__name__)


class FormHandler:
    """表单处理器"""
    
    def __init__(self, page: Page):
        """
        初始化表单处理器
        
        Args:
            page: Playwright页面实例
        """
        self.page = page
        
    async def fill_form(self, form_data: Dict[str, Any]) -> bool:
        """
        批量填写表单
        
        Args:
            form_data: 表单数据，键为选择器，值为要填入的值
            
        Returns:
            bool: 是否成功填写
        """
        try:
            logger.info(f"开始填写表单，共{len(form_data)}个字段")
            
            for selector, value in form_data.items():
                try:
                    # 等待元素出现
                    element = await self.page.wait_for_selector(selector, timeout=5000)
                    if not element:
                        logger.warning(f"未找到元素: {selector}")
                        continue
                        
                    # 获取元素类型
                    tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                    input_type = await element.get_attribute("type")
                    
                    # 根据元素类型填写
                    if tag_name in ["input", "textarea"]:
                        if input_type == "checkbox":
                            await self._handle_checkbox(element, value)
                        elif input_type == "radio":
                            await self._handle_radio(element, value)
                        elif input_type == "file":
                            await self._handle_file_upload(element, value)
                        else:
                            await self._handle_text_input(element, value)
                    elif tag_name == "select":
                        await self._handle_select(element, value)
                    else:
                        logger.warning(f"不支持的元素类型: {tag_name}")
                        
                except Exception as e:
                    logger.error(f"填写字段失败 {selector}: {e}")
                    continue
                    
            logger.info("表单填写完成")
            return True
            
        except Exception as e:
            logger.error(f"表单填写失败: {e}")
            return False
            
    async def _handle_text_input(self, element: ElementHandle, value: Any):
        """处理文本输入"""
        if value is None:
            return
            
        str_value = str(value)
        
        # 清除现有内容
        await element.click()
        await element.fill("")
        
        # 输入新内容
        await element.fill(str_value)
        
    async def _handle_checkbox(self, element: ElementHandle, value: Any):
        """处理复选框"""
        is_checked = await element.is_checked()
        
        if isinstance(value, bool):
            target_state = value
        else:
            target_state = str(value).lower() in ["true", "1", "yes", "on"]
            
        if is_checked != target_state:
            await element.click()
            
    async def _handle_radio(self, element: ElementHandle, value: Any):
        """处理单选按钮"""
        if isinstance(value, str):
            # 如果是字符串，比较value属性
            element_value = await element.get_attribute("value")
            if element_value == value:
                await element.click()
        else:
            # 如果是布尔值，选中第一个
            await element.click()
            
    async def _handle_file_upload(self, element: ElementHandle, value: Union[str, List[str]]):
        """处理文件上传"""
        if isinstance(value, str):
            file_paths = [value]
        elif isinstance(value, list):
            file_paths = value
        else:
            raise ValueError("文件上传需要字符串或字符串列表")
            
        await element.set_input_files(file_paths)
        
    async def _handle_select(self, element: ElementHandle, value: Any):
        """处理下拉选择"""
        if isinstance(value, str):
            await element.select_option(value)
        elif isinstance(value, list):
            await element.select_option(value)
        else:
            raise ValueError("下拉选择需要字符串或字符串列表")
            
    async def submit_form(self, submit_selector: Optional[str] = None) -> bool:
        """
        提交表单
        
        Args:
            submit_selector: 提交按钮选择器，如果为None则自动查找
            
        Returns:
            bool: 是否成功提交
        """
        try:
            if submit_selector:
                # 使用指定的提交按钮
                submit_button = await self.page.wait_for_selector(submit_selector)
                if not submit_button:
                    raise Exception(f"未找到提交按钮: {submit_selector}")
                await submit_button.click()
            else:
                # 自动查找提交按钮
                submit_selectors = [
                    "input[type=submit]",
                    "button[type=submit]",
                    "button:has-text('submit')",
                    "button:has-text('Submit')",
                    "button:has-text('提交')",
                    "button:has-text('登录')",
                    "button:has-text('登录')",
                    "button:has-text('确认')",
                    "button:has-text('确定')",
                    "button:has-text('提交')",
                    "[type=submit]"
                ]
                
                submitted = False
                for selector in submit_selectors:
                    try:
                        submit_button = await self.page.wait_for_selector(selector, timeout=1000)
                        if submit_button:
                            await submit_button.click()
                            submitted = True
                            break
                    except:
                        continue
                        
                if not submitted:
                    raise Exception("未找到提交按钮")
                    
            logger.info("表单提交成功")
            return True
            
        except Exception as e:
            logger.error(f"表单提交失败: {e}")
            return False
            
    async def fill_input(
        self,
        selector: str,
        value: Any,
        clear_first: bool = True
    ) -> bool:
        """
        填写单个输入框
        
        Args:
            selector: 选择器
            value: 值
            clear_first: 是否先清除
            
        Returns:
            bool: 是否成功
        """
        try:
            element = await self.page.wait_for_selector(selector)
            if not element:
                return False
                
            if clear_first:
                await element.fill("")
                
            await element.fill(str(value))
            return True
            
        except Exception as e:
            logger.error(f"填写输入框失败 {selector}: {e}")
            return False
            
    async def select_option(
        self,
        selector: str,
        value: Union[str, List[str]]
    ) -> bool:
        """
        选择下拉选项
        
        Args:
            selector: 选择器
            value: 选项值
            
        Returns:
            bool: 是否成功
        """
        try:
            element = await self.page.wait_for_selector(selector)
            if not element:
                return False
                
            await element.select_option(value)
            return True
            
        except Exception as e:
            logger.error(f"选择选项失败 {selector}: {e}")
            return False
            
    async def click_checkbox(
        self,
        selector: str,
        checked: Optional[bool] = None
    ) -> bool:
        """
        点击复选框
        
        Args:
            selector: 选择器
            checked: 是否选中状态，None表示切换状态
            
        Returns:
            bool: 是否成功
        """
        try:
            element = await self.page.wait_for_selector(selector)
            if not element:
                return False
                
            if checked is not None:
                current_state = await element.is_checked()
                if current_state != checked:
                    await element.click()
            else:
                await element.click()
                
            return True
            
        except Exception as e:
            logger.error(f"点击复选框失败 {selector}: {e}")
            return False
            
    async def upload_file(
        self,
        selector: str,
        file_paths: Union[str, List[str]]
    ) -> bool:
        """
        上传文件
        
        Args:
            selector: 文件输入框选择器
            file_paths: 文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            element = await self.page.wait_for_selector(selector)
            if not element:
                return False
                
            await element.set_input_files(file_paths)
            return True
            
        except Exception as e:
            logger.error(f"文件上传失败 {selector}: {e}")
            return False
            
    async def get_form_data(self, form_selector: Optional[str] = None) -> Dict[str, Any]:
        """
        获取表单数据
        
        Args:
            form_selector: 表单选择器，如果为None则获取页面所有表单
            
        Returns:
            Dict: 表单数据
        """
        try:
            if form_selector:
                forms = [await self.page.wait_for_selector(form_selector)]
            else:
                forms = await self.page.query_selector_all("form")
                
            form_data = {}
            
            for form in forms:
                if not form:
                    continue
                    
                # 获取所有输入元素
                inputs = await form.query_selector_all("input, textarea, select")
                
                for input_element in inputs:
                    if not input_element:
                        continue
                        
                    tag_name = await input_element.evaluate("el => el.tagName.toLowerCase()")
                    input_type = await input_element.get_attribute("type")
                    name = await input_element.get_attribute("name")
                    
                    if not name:
                        continue
                        
                    try:
                        if tag_name in ["input", "textarea"]:
                            if input_type == "checkbox" or input_type == "radio":
                                if await input_element.is_checked():
                                    form_data[name] = await input_element.get_attribute("value")
                            else:
                                form_data[name] = await input_element.input_value()
                        elif tag_name == "select":
                            form_data[name] = await input_element.evaluate("el => el.value")
                    except:
                        continue
                        
            return form_data
            
        except Exception as e:
            logger.error(f"获取表单数据失败: {e}")
            return {}
            
    async def validate_form(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证表单数据
        
        Args:
            form_data: 表单数据
            
        Returns:
            Dict: 验证结果
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            for selector, value in form_data.items():
                try:
                    element = await self.page.query_selector(selector)
                    if not element:
                        validation_result["warnings"].append(f"元素未找到: {selector}")
                        continue
                        
                    # 检查必填字段
                    required = await element.get_attribute("required")
                    if required and (not value or str(value).strip() == ""):
                        validation_result["valid"] = False
                        validation_result["errors"].append(f"必填字段不能为空: {selector}")
                        
                    # 检查字段类型
                    input_type = await element.get_attribute("type")
                    if input_type == "email" and value:
                        import re
                        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                        if not re.match(email_pattern, str(value)):
                            validation_result["valid"] = False
                            validation_result["errors"].append(f"邮箱格式不正确: {selector}")
                            
                except Exception as e:
                    validation_result["warnings"].append(f"验证字段失败 {selector}: {e}")
                    
        except Exception as e:
            logger.error(f"表单验证失败: {e}")
            validation_result["valid"] = False
            validation_result["errors"].append(f"验证过程出错: {e}")
            
        return validation_result
        
    async def wait_for_form_submit(self, timeout: int = 10000) -> bool:
        """
        等待表单提交完成
        
        Args:
            timeout: 超时时间
            
        Returns:
            bool: 是否成功提交
        """
        try:
            # 等待页面加载完成或URL变化
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
            return True
            
        except Exception as e:
            logger.error(f"等待表单提交失败: {e}")
            return False