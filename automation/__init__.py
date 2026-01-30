"""
AgentBus Browser Automation System

基于Moltbot的浏览器自动化功能，提供完整的浏览器自动化解决方案。
"""

from .browser import BrowserAutomation
from .playwright_manager import PlaywrightManager
from .screenshot import ScreenshotManager
from .form_handler import FormHandler
from .page_navigator import PageNavigator
from .element_finder import ElementFinder

__all__ = [
    "BrowserAutomation",
    "PlaywrightManager", 
    "ScreenshotManager",
    "FormHandler",
    "PageNavigator",
    "ElementFinder"
]

__version__ = "1.0.0"