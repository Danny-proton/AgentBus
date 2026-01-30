"""
AgentBus Hook Configuration

Manages configuration for the hook system including loading, validation,
and persistence of hook settings.
"""

import os
import json
import yaml
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class HookExecutionConfig:
    """Configuration for hook execution"""
    timeout: Optional[int] = 30  # seconds
    retry_count: int = 0
    max_concurrent: int = 10
    fail_silent: bool = False
    continue_on_error: bool = True


@dataclass
class HookEntryConfig:
    """Configuration for individual hook entries"""
    enabled: bool = True
    priority: int = 0
    timeout: Optional[int] = None
    retry_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HookConfig:
    """Main configuration class for the hook system"""
    
    # Global settings
    enabled: bool = True
    debug: bool = False
    
    # Loading settings
    load_bundled_hooks: bool = True
    load_workspace_hooks: bool = True
    load_managed_hooks: bool = True
    load_third_party_hooks: bool = True
    load_plugin_hooks: bool = True
    
    # Discovery settings
    auto_discover: bool = True
    workspace_hooks_dir: str = "hooks"
    managed_hooks_dir: Optional[str] = None
    third_party_hooks_dir: Optional[str] = None
    
    # Filtering settings
    included_hooks: List[str] = field(default_factory=list)
    excluded_hooks: List[str] = field(default_factory=list)
    hook_tags: List[str] = field(default_factory=list)
    
    # Execution settings
    execution: HookExecutionConfig = field(default_factory=HookExecutionConfig)
    
    # Individual hook configurations
    hooks: Dict[str, HookEntryConfig] = field(default_factory=dict)
    
    # Priority overrides
    priority_overrides: Dict[str, int] = field(default_factory=dict)
    
    # Health monitoring
    health_check_interval: int = 300  # seconds
    max_execution_history: int = 1000
    enable_metrics: bool = True
    
    # Security settings
    allowed_sources: List[str] = field(default_factory=lambda: [
        "agentbus-bundled",
        "agentbus-workspace", 
        "agentbus-managed"
    ])
    require_signature: bool = False
    allowed_apis: List[str] = field(default_factory=list)


class HookConfigManager:
    """Manages hook configuration loading, validation, and persistence"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or self._get_default_config_dir())
        self.config_file = self.config_dir / "hooks.yaml"
        self.user_config_file = self.config_dir / "hooks.user.yaml"
        
        self._config: Optional[HookConfig] = None
        self._config_watchers: List[callable] = []
        
    def _get_default_config_dir(self) -> str:
        """Get default configuration directory"""
        home_dir = Path.home()
        return str(home_dir / ".agentbus" / "config")
    
    def load_config(self, force_reload: bool = False) -> HookConfig:
        """
        Load hook configuration
        
        Args:
            force_reload: Force reload even if config is cached
            
        Returns:
            Loaded configuration
        """
        if self._config is not None and not force_reload:
            return self._config
        
        try:
            # Load configuration from file
            self._config = self._load_config_from_file()
            
            # Apply environment variables
            self._apply_environment_overrides()
            
            # Validate configuration
            self._validate_config()
            
            logger.info(f"Loaded hook configuration from {self.config_file}")
            return self._config
            
        except Exception as e:
            logger.error(f"Failed to load hook configuration: {e}")
            # Return default configuration
            self._config = HookConfig()
            return self._config
    
    def _load_config_from_file(self) -> HookConfig:
        """Load configuration from YAML file"""
        if not self.config_file.exists():
            logger.info(f"Hook config file not found, using defaults: {self.config_file}")
            return HookConfig()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return HookConfig()
            
            # Convert to HookConfig
            config = self._dict_to_hook_config(data)
            return config
            
        except Exception as e:
            logger.error(f"Failed to parse hook configuration file: {e}")
            return HookConfig()
    
    def _dict_to_hook_config(self, data: Dict[str, Any]) -> HookConfig:
        """Convert dictionary to HookConfig"""
        try:
            # Handle execution config
            execution_data = data.get('execution', {})
            execution = HookExecutionConfig(**execution_data)
            
            # Handle hook entries
            hooks_data = data.get('hooks', {})
            hooks = {}
            for hook_name, hook_data in hooks_data.items():
                hooks[hook_name] = HookEntryConfig(**hook_data)
            
            # Create main config
            config = HookConfig(
                enabled=data.get('enabled', True),
                debug=data.get('debug', False),
                load_bundled_hooks=data.get('load_bundled_hooks', True),
                load_workspace_hooks=data.get('load_workspace_hooks', True),
                load_managed_hooks=data.get('load_managed_hooks', True),
                load_third_party_hooks=data.get('load_third_party_hooks', True),
                load_plugin_hooks=data.get('load_plugin_hooks', True),
                auto_discover=data.get('auto_discover', True),
                workspace_hooks_dir=data.get('workspace_hooks_dir', 'hooks'),
                managed_hooks_dir=data.get('managed_hooks_dir'),
                third_party_hooks_dir=data.get('third_party_hooks_dir'),
                included_hooks=data.get('included_hooks', []),
                excluded_hooks=data.get('excluded_hooks', []),
                hook_tags=data.get('hook_tags', []),
                execution=execution,
                hooks=hooks,
                priority_overrides=data.get('priority_overrides', {}),
                health_check_interval=data.get('health_check_interval', 300),
                max_execution_history=data.get('max_execution_history', 1000),
                enable_metrics=data.get('enable_metrics', True),
                allowed_sources=data.get('allowed_sources', [
                    "agentbus-bundled", "agentbus-workspace", "agentbus-managed"
                ]),
                require_signature=data.get('require_signature', False),
                allowed_apis=data.get('allowed_apis', [])
            )
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to convert dictionary to HookConfig: {e}")
            return HookConfig()
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides"""
        if not self._config:
            return
        
        # Environment variable mappings
        env_mappings = {
            'AGENTBUS_HOOKS_ENABLED': lambda x: self._config.__setattr__('enabled', x.lower() == 'true'),
            'AGENTBUS_HOOKS_DEBUG': lambda x: self._config.__setattr__('debug', x.lower() == 'true'),
            'AGENTBUS_HOOKS_TIMEOUT': lambda x: self._config.execution.__setattr__('timeout', int(x)),
            'AGENTBUS_HOOKS_MAX_CONCURRENT': lambda x: self._config.execution.__setattr__('max_concurrent', int(x)),
        }
        
        for env_var, setter in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    setter(value)
                    logger.debug(f"Applied environment override: {env_var}={value}")
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Failed to apply environment override {env_var}: {e}")
    
    def _validate_config(self) -> None:
        """Validate loaded configuration"""
        if not self._config:
            return
        
        try:
            # Validate numeric ranges
            if self._config.execution.timeout is not None and self._config.execution.timeout <= 0:
                logger.warning("Invalid timeout value, using default")
                self._config.execution.timeout = 30
            
            if self._config.execution.max_concurrent <= 0:
                logger.warning("Invalid max_concurrent value, using default")
                self._config.execution.max_concurrent = 10
            
            if self._config.health_check_interval <= 0:
                logger.warning("Invalid health_check_interval, using default")
                self._config.health_check_interval = 300
            
            # Validate paths
            if self._config.workspace_hooks_dir:
                # Convert to absolute path if relative
                if not os.path.isabs(self._config.workspace_hooks_dir):
                    self._config.workspace_hooks_dir = os.path.join(os.getcwd(), self._config.workspace_hooks_dir)
            
            # Validate hook configurations
            for hook_name, hook_config in self._config.hooks.items():
                if hook_config.timeout is not None and hook_config.timeout <= 0:
                    logger.warning(f"Invalid timeout for hook '{hook_name}', using None")
                    hook_config.timeout = None
                
                if hook_config.retry_count < 0:
                    logger.warning(f"Invalid retry_count for hook '{hook_name}', using 0")
                    hook_config.retry_count = 0
            
            logger.debug("Hook configuration validation completed")
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
    
    def save_config(self, config: Optional[HookConfig] = None) -> bool:
        """
        Save configuration to file
        
        Args:
            config: Configuration to save, or current config if None
            
        Returns:
            True if save successful
        """
        try:
            config_to_save = config or self._config
            if not config_to_save:
                logger.error("No configuration to save")
                return False
            
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert to dictionary
            config_dict = self._hook_config_to_dict(config_to_save)
            
            # Save to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2, allow_unicode=True)
            
            logger.info(f"Saved hook configuration to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save hook configuration: {e}")
            return False
    
    def _hook_config_to_dict(self, config: HookConfig) -> Dict[str, Any]:
        """Convert HookConfig to dictionary"""
        return {
            'enabled': config.enabled,
            'debug': config.debug,
            'load_bundled_hooks': config.load_bundled_hooks,
            'load_workspace_hooks': config.load_workspace_hooks,
            'load_managed_hooks': config.load_managed_hooks,
            'load_third_party_hooks': config.load_third_party_hooks,
            'load_plugin_hooks': config.load_plugin_hooks,
            'auto_discover': config.auto_discover,
            'workspace_hooks_dir': config.workspace_hooks_dir,
            'managed_hooks_dir': config.managed_hooks_dir,
            'third_party_hooks_dir': config.third_party_hooks_dir,
            'included_hooks': config.included_hooks,
            'excluded_hooks': config.excluded_hooks,
            'hook_tags': config.hook_tags,
            'execution': asdict(config.execution),
            'hooks': {k: asdict(v) for k, v in config.hooks.items()},
            'priority_overrides': config.priority_overrides,
            'health_check_interval': config.health_check_interval,
            'max_execution_history': config.max_execution_history,
            'enable_metrics': config.enable_metrics,
            'allowed_sources': config.allowed_sources,
            'require_signature': config.require_signature,
            'allowed_apis': config.allowed_apis
        }
    
    def update_hook_config(self, hook_name: str, updates: Dict[str, Any]) -> bool:
        """
        Update configuration for a specific hook
        
        Args:
            hook_name: Name of the hook
            updates: Dictionary of updates to apply
            
        Returns:
            True if update successful
        """
        try:
            config = self.load_config()
            
            # Get or create hook config
            if hook_name not in config.hooks:
                config.hooks[hook_name] = HookEntryConfig()
            
            hook_config = config.hooks[hook_name]
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(hook_config, key):
                    setattr(hook_config, key, value)
                else:
                    logger.warning(f"Unknown hook config attribute '{key}' for hook '{hook_name}'")
            
            # Save configuration
            return self.save_config(config)
            
        except Exception as e:
            logger.error(f"Failed to update hook config for '{hook_name}': {e}")
            return False
    
    def get_hook_config(self, hook_name: str) -> Optional[HookEntryConfig]:
        """
        Get configuration for a specific hook
        
        Args:
            hook_name: Name of the hook
            
        Returns:
            Hook configuration or None
        """
        config = self.load_config()
        return config.hooks.get(hook_name)
    
    def list_hooks(self) -> List[str]:
        """List all configured hooks"""
        config = self.load_config()
        return list(config.hooks.keys())
    
    def add_watcher(self, callback: callable) -> None:
        """
        Add a configuration change watcher
        
        Args:
            callback: Function to call when configuration changes
        """
        self._config_watchers.append(callback)
    
    def remove_watcher(self, callback: callable) -> None:
        """Remove a configuration change watcher"""
        if callback in self._config_watchers:
            self._config_watchers.remove(callback)
    
    def _notify_watchers(self) -> None:
        """Notify all watchers of configuration changes"""
        for callback in self._config_watchers:
            try:
                callback(self._config)
            except Exception as e:
                logger.error(f"Configuration watcher failed: {e}")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration"""
        config = self.load_config()
        
        return {
            'enabled': config.enabled,
            'debug': config.debug,
            'load_sources': {
                'bundled': config.load_bundled_hooks,
                'workspace': config.load_workspace_hooks,
                'managed': config.load_managed_hooks,
                'third_party': config.load_third_party_hooks,
                'plugins': config.load_plugin_hooks
            },
            'total_hooks': len(config.hooks),
            'enabled_hooks': sum(1 for h in config.hooks.values() if h.enabled),
            'execution_settings': {
                'timeout': config.execution.timeout,
                'max_concurrent': config.execution.max_concurrent,
                'retry_count': config.execution.retry_count
            },
            'config_file': str(self.config_file)
        }
    
    def create_default_config(self) -> bool:
        """Create default configuration file"""
        try:
            config = HookConfig()
            return self.save_config(config)
        except Exception as e:
            logger.error(f"Failed to create default configuration: {e}")
            return False


# Global configuration manager instance
_config_manager: Optional[HookConfigManager] = None


def get_config_manager() -> HookConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = HookConfigManager()
    return _config_manager


def load_hook_config() -> HookConfig:
    """Load hook configuration using the global manager"""
    return get_config_manager().load_config()


def save_hook_config(config: HookConfig) -> bool:
    """Save hook configuration using the global manager"""
    return get_config_manager().save_config(config)