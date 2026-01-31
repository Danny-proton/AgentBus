"""
WebExplorer Plugin Package
"""

from .atlas_manager import AtlasManagerPlugin
from .browser_manager import BrowserManagerPlugin

__all__ = [
    "AtlasManagerPlugin",
    "BrowserManagerPlugin",
]
