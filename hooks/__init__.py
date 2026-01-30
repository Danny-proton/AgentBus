"""
AgentBus Hook System

A comprehensive hook system for AgentBus that provides extensible event-driven
functionality for agent events, command processing, session lifecycle, and more.

Features:
- Event-driven hook architecture
- Priority-based execution ordering
- Built-in hooks for common functionality
- Third-party hook support
- Configuration management
- Health monitoring and statistics
- Security and performance hooks
"""

import logging
from typing import Any, Dict, List, Optional, Type, Union

from .types import (
    Hook, HookEntry, HookEvent, HookResult, HookHandler,
    HookEventType, HookExecutionContext, HookSource,
    HookMetadata, HookInvocationPolicy
)

from .core import (
    HookRegistry, HookEngine, hook_engine,
    trigger_hook, register_hook, get_hook_engine
)

from .manager import (
    HookManager, get_hook_manager, initialize_hook_manager
)

from .loader import HookLoader

from .config import (
    HookConfig, HookConfigManager, HookExecutionConfig, HookEntryConfig,
    get_config_manager, load_hook_config, save_hook_config
)

from .priority import (
    PriorityManager, HookPriority, priority_to_level,
    normalize_priority, compare_priorities
)

from .internal_hooks import (
    register_internal_hooks, get_metrics, cleanup_internal_hooks,
    logging_hook, metrics_hook, session_management, error_handler,
    security_monitor, health_monitor, performance_optimizer
)

# Import example hooks
from .examples.welcome_hook import (
    WelcomeHook, create_welcome_hook
)

from .examples.analytics_hooks import (
    CommandLoggerHook, ErrorTrackerHook, 
    command_logger, error_tracker
)

from .examples.utility_hooks import (
    EchoHook, TimeHook, HealthHook, CalculatorHook,
    HashHook, JSONProcessorHook, TextStatsHook,
    create_utility_hooks
)

# Configure logging
logger = logging.getLogger(__name__)

# Version
__version__ = "1.0.0"

# Public API exports
__all__ = [
    # Core types
    "Hook", "HookEntry", "HookEvent", "HookResult", "HookHandler",
    "HookEventType", "HookExecutionContext", "HookSource",
    "HookMetadata", "HookInvocationPolicy",
    
    # Core system
    "HookRegistry", "HookEngine", "hook_engine",
    "trigger_hook", "register_hook", "get_hook_engine",
    
    # Manager
    "HookManager", "get_hook_manager", "initialize_hook_manager",
    
    # Loader
    "HookLoader",
    
    # Configuration
    "HookConfig", "HookConfigManager", "HookExecutionConfig", "HookEntryConfig",
    "get_config_manager", "load_hook_config", "save_hook_config",
    
    # Priority management
    "PriorityManager", "HookPriority", "priority_to_level",
    "normalize_priority", "compare_priorities",
    
    # Internal hooks
    "register_internal_hooks", "get_metrics", "cleanup_internal_hooks",
    "logging_hook", "metrics_hook", "session_management", 
    "error_handler", "security_monitor", "health_monitor", 
    "performance_optimizer",
    
    # Example hooks
    "WelcomeHook", "create_welcome_hook",
    "CommandLoggerHook", "ErrorTrackerHook",
    "command_logger", "error_tracker",
    "EchoHook", "TimeHook", "HealthHook", "CalculatorHook",
    "HashHook", "JSONProcessorHook", "TextStatsHook",
    "create_utility_hooks",
    
    # System functions
    "initialize_system", "shutdown_system", "get_system_info",
]


class AgentBusHookSystem:
    """Main hook system interface"""
    
    def __init__(self, config: Optional[HookConfig] = None, workspace_dir: Optional[str] = None):
        self.config = config or HookConfig()
        self.workspace_dir = workspace_dir
        self._initialized = False
        self._hook_manager: Optional[HookManager] = None
    
    async def initialize(self) -> bool:
        """Initialize the hook system"""
        try:
            if self._initialized:
                logger.warning("Hook system already initialized")
                return True
            
            logger.info("Initializing AgentBus Hook System...")
            
            # Initialize configuration
            config_manager = get_config_manager()
            if self.workspace_dir:
                config_manager.config_dir = self.workspace_dir
            
            # Load configuration
            config = load_hook_config()
            
            # Initialize hook manager
            self._hook_manager = await initialize_hook_manager(config, self.workspace_dir)
            
            # Register internal hooks
            register_internal_hooks()
            
            self._initialized = True
            logger.info("AgentBus Hook System initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize hook system: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the hook system"""
        try:
            if not self._initialized:
                return
            
            logger.info("Shutting down AgentBus Hook System...")
            
            # Shutdown hook engine
            await hook_engine.shutdown()
            
            # Cleanup internal hooks
            await cleanup_internal_hooks()
            
            # Clear hook manager
            if self._hook_manager:
                await self._hook_manager.cleanup_expired_history()
            
            self._initialized = False
            logger.info("AgentBus Hook System shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during hook system shutdown: {e}")
    
    async def trigger_event(
        self,
        event_type: HookEventType,
        action: str,
        session_key: str,
        context: Optional[HookExecutionContext] = None,
        **kwargs
    ) -> List[HookResult]:
        """Trigger an event and execute hooks"""
        if not self._initialized:
            logger.warning("Hook system not initialized, skipping event trigger")
            return []
        
        if not self._hook_manager:
            logger.error("Hook manager not available")
            return []
        
        return await self._hook_manager.trigger_event(
            event_type=event_type,
            action=action,
            session_key=session_key,
            context=context,
            **kwargs
        )
    
    def register_hook(
        self,
        event_key: str,
        handler: HookHandler,
        priority: int = 0,
        hook_entry: Optional[HookEntry] = None
    ) -> bool:
        """Register a hook handler"""
        if not self._initialized:
            logger.warning("Hook system not initialized, cannot register hook")
            return False
        
        return register_hook(event_key, handler, priority, hook_entry)
    
    def get_status(self) -> Dict[str, Any]:
        """Get hook system status"""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        return {
            "status": "initialized",
            "version": __version__,
            "hook_manager": self._hook_manager.get_status() if self._hook_manager else None,
            "engine": hook_engine.get_statistics(),
            "config": get_config_manager().get_config_summary()
        }
    
    def enable(self) -> None:
        """Enable the hook system"""
        hook_engine.enable()
        logger.info("Hook system enabled")
    
    def disable(self) -> None:
        """Disable the hook system"""
        hook_engine.disable()
        logger.info("Hook system disabled")


# Global system instance
_global_system: Optional[AgentBusHookSystem] = None


def initialize_system(
    config: Optional[HookConfig] = None,
    workspace_dir: Optional[str] = None
) -> AgentBusHookSystem:
    """Initialize the global hook system"""
    global _global_system
    _global_system = AgentBusHookSystem(config, workspace_dir)
    return _global_system


async def shutdown_system() -> None:
    """Shutdown the global hook system"""
    global _global_system
    if _global_system:
        await _global_system.shutdown()
        _global_system = None


def get_system() -> Optional[AgentBusHookSystem]:
    """Get the global hook system instance"""
    return _global_system


def get_system_info() -> Dict[str, Any]:
    """Get comprehensive system information"""
    if not _global_system:
        return {"status": "not_initialized"}
    
    return {
        "system": _global_system.get_status(),
        "metrics": get_metrics(),
        "statistics": hook_engine.get_statistics()
    }


# Convenience functions for common operations
async def trigger_command(
    command: str,
    session_key: str,
    context: Optional[HookExecutionContext] = None,
    **kwargs
) -> List[HookResult]:
    """Trigger a command event"""
    return await trigger_hook(
        event_type=HookEventType.COMMAND,
        action=command,
        session_key=session_key,
        context=context,
        **kwargs
    )


async def trigger_session_event(
    action: str,
    session_key: str,
    context: Optional[HookExecutionContext] = None,
    **kwargs
) -> List[HookResult]:
    """Trigger a session event"""
    return await trigger_hook(
        event_type=HookEventType.SESSION,
        action=action,
        session_key=session_key,
        context=context,
        **kwargs
    )


async def trigger_message_event(
    action: str,
    session_key: str,
    context: Optional[HookExecutionContext] = None,
    **kwargs
) -> List[HookResult]:
    """Trigger a message event"""
    return await trigger_hook(
        event_type=HookEventType.MESSAGE,
        action=action,
        session_key=session_key,
        context=context,
        **kwargs
    )


async def trigger_error_event(
    error_type: str,
    error_message: str,
    session_key: str,
    context: Optional[HookExecutionContext] = None,
    **kwargs
) -> List[HookResult]:
    """Trigger an error event"""
    return await trigger_hook(
        event_type=HookEventType.ERROR,
        action=error_type,
        session_key=session_key,
        context=context,
        error_message=error_message,
        **kwargs
    )


# Initialize the system with basic logging
def setup_logging():
    """Setup logging for the hook system"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


# Auto-setup logging when module is imported
setup_logging()