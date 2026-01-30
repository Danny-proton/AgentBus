"""
AgentBus Hook Loader

Loads hooks from various sources including bundled hooks, workspace hooks,
third-party hooks, and plugins.
"""

import os
import importlib.util
import sys
import inspect
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
from dataclasses import asdict
from datetime import datetime

from .types import (
    Hook, HookEntry, HookMetadata, HookSource, HookInstallSpec,
    HookRequirements, HookInvocationPolicy, HookHandler
)
from .config import HookConfig

logger = logging.getLogger(__name__)


class HookLoader:
    """Loader for hooks from various sources"""
    
    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir or os.getcwd()
        self._loaded_modules: Dict[str, Any] = {}
        self._load_statistics = {
            'total_attempts': 0,
            'successful_loads': 0,
            'failed_loads': 0,
            'load_time': 0.0,
            'sources': {
                HookSource.BUNDLED: {'attempts': 0, 'success': 0, 'failed': 0},
                HookSource.MANAGED: {'attempts': 0, 'success': 0, 'failed': 0},
                HookSource.WORKSPACE: {'attempts': 0, 'success': 0, 'failed': 0},
                HookSource.PLUGIN: {'attempts': 0, 'success': 0, 'failed': 0},
                HookSource.THIRD_PARTY: {'attempts': 0, 'success': 0, 'failed': 0}
            }
        }
    
    async def load_all_hooks(self, config: HookConfig) -> List[HookEntry]:
        """
        Load hooks from all available sources
        
        Args:
            config: Hook configuration
            
        Returns:
            List of loaded hook entries
        """
        start_time = datetime.now()
        all_entries: List[HookEntry] = []
        
        try:
            logger.info("Loading hooks from all sources...")
            
            # Load bundled hooks
            if config.load_bundled_hooks:
                bundled_entries = await self._load_bundled_hooks()
                all_entries.extend(bundled_entries)
                logger.info(f"Loaded {len(bundled_entries)} bundled hooks")
            
            # Load workspace hooks
            if config.load_workspace_hooks:
                workspace_entries = await self._load_workspace_hooks()
                all_entries.extend(workspace_entries)
                logger.info(f"Loaded {len(workspace_entries)} workspace hooks")
            
            # Load managed hooks
            if config.load_managed_hooks:
                managed_entries = await self._load_managed_hooks()
                all_entries.extend(managed_entries)
                logger.info(f"Loaded {len(managed_entries)} managed hooks")
            
            # Load third-party hooks
            if config.load_third_party_hooks:
                third_party_entries = await self._load_third_party_hooks()
                all_entries.extend(third_party_entries)
                logger.info(f"Loaded {len(third_party_entries)} third-party hooks")
            
            # Load plugin hooks
            if config.load_plugin_hooks:
                plugin_entries = await self._load_plugin_hooks()
                all_entries.extend(plugin_entries)
                logger.info(f"Loaded {len(plugin_entries)} plugin hooks")
            
            # Remove duplicates and apply filters
            filtered_entries = self._filter_and_deduplicate_hooks(all_entries, config)
            
            load_time = (datetime.now() - start_time).total_seconds()
            self._load_statistics['load_time'] += load_time
            
            logger.info(f"Total hook loading completed in {load_time:.3f}s: {len(filtered_entries)} hooks loaded")
            return filtered_entries
            
        except Exception as e:
            logger.error(f"Failed to load hooks from all sources: {e}")
            return []
    
    async def _load_bundled_hooks(self) -> List[HookEntry]:
        """Load built-in bundled hooks"""
        try:
            bundled_dir = Path(__file__).parent / "bundled"
            if not bundled_dir.exists():
                logger.warning(f"Bundled hooks directory not found: {bundled_dir}")
                return []
            
            return await self._load_hooks_from_directory(
                directory=bundled_dir,
                source=HookSource.BUNDLED
            )
        except Exception as e:
            logger.error(f"Failed to load bundled hooks: {e}")
            return []
    
    async def _load_workspace_hooks(self) -> List[HookEntry]:
        """Load hooks from workspace directory"""
        try:
            workspace_hooks_dir = Path(self.workspace_dir) / "hooks"
            if not workspace_hooks_dir.exists():
                logger.info(f"Workspace hooks directory not found: {workspace_hooks_dir}")
                return []
            
            return await self._load_hooks_from_directory(
                directory=workspace_hooks_dir,
                source=HookSource.WORKSPACE
            )
        except Exception as e:
            logger.error(f"Failed to load workspace hooks: {e}")
            return []
    
    async def _load_managed_hooks(self) -> List[HookEntry]:
        """Load user-managed hooks"""
        try:
            # Look for managed hooks in config directory or standard locations
            managed_dirs = [
                Path.home() / ".agentbus" / "hooks",
                Path("/etc/agentbus/hooks"),
                Path(self.workspace_dir) / ".agentbus" / "hooks"
            ]
            
            all_entries = []
            for managed_dir in managed_dirs:
                if managed_dir.exists():
                    entries = await self._load_hooks_from_directory(
                        directory=managed_dir,
                        source=HookSource.MANAGED
                    )
                    all_entries.extend(entries)
            
            return all_entries
        except Exception as e:
            logger.error(f"Failed to load managed hooks: {e}")
            return []
    
    async def _load_third_party_hooks(self) -> List[HookEntry]:
        """Load third-party hooks from pip packages"""
        try:
            # This would require integration with Python package management
            # For now, return empty list
            logger.info("Third-party hook loading not yet implemented")
            return []
        except Exception as e:
            logger.error(f"Failed to load third-party hooks: {e}")
            return []
    
    async def _load_plugin_hooks(self) -> List[HookEntry]:
        """Load hooks from plugins"""
        try:
            # This would require integration with the plugin system
            # For now, return empty list
            logger.info("Plugin hook loading not yet implemented")
            return []
        except Exception as e:
            logger.error(f"Failed to load plugin hooks: {e}")
            return []
    
    async def _load_hooks_from_directory(
        self, 
        directory: Path, 
        source: HookSource
    ) -> List[HookEntry]:
        """
        Load hooks from a specific directory
        
        Args:
            directory: Directory to scan for hooks
            source: Source type for the hooks
            
        Returns:
            List of hook entries found
        """
        entries = []
        
        try:
            if not directory.exists():
                return entries
            
            # Scan subdirectories for hooks
            for item in directory.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    hook_entry = await self._load_hook_from_directory(item, source)
                    if hook_entry:
                        entries.append(hook_entry)
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to load hooks from directory {directory}: {e}")
            return entries
    
    async def _load_hook_from_directory(
        self, 
        hook_dir: Path, 
        source: HookSource
    ) -> Optional[HookEntry]:
        """
        Load a single hook from a directory
        
        Args:
            hook_dir: Directory containing the hook
            source: Source type
            
        Returns:
            Hook entry or None if loading failed
        """
        try:
            self._load_statistics['total_attempts'] += 1
            self._load_statistics['sources'][source]['attempts'] += 1
            
            # Check for required files
            hook_md_file = hook_dir / "HOOK.md"
            handler_file = await self._find_handler_file(hook_dir)
            
            if not hook_md_file.exists():
                logger.debug(f"No HOOK.md found in {hook_dir}")
                return None
            
            if not handler_file:
                logger.warning(f"No handler file found in {hook_dir}")
                return None
            
            # Parse hook metadata
            frontmatter = await self._parse_frontmatter(hook_md_file)
            metadata = self._parse_hook_metadata(frontmatter)
            invocation = self._parse_invocation_policy(frontmatter)
            
            # Create hook entry
            hook = Hook(
                name=frontmatter.get('name', hook_dir.name),
                description=frontmatter.get('description', ''),
                source=source,
                file_path=str(hook_md_file),
                base_dir=str(hook_dir),
                handler_path=str(handler_file)
            )
            
            entry = HookEntry(
                hook=hook,
                frontmatter=frontmatter,
                metadata=metadata,
                invocation=invocation
            )
            
            self._load_statistics['successful_loads'] += 1
            self._load_statistics['sources'][source]['success'] += 1
            
            logger.debug(f"Successfully loaded hook: {hook.name}")
            return entry
            
        except Exception as e:
            self._load_statistics['failed_loads'] += 1
            self._load_statistics['sources'][source]['failed'] += 1
            logger.error(f"Failed to load hook from {hook_dir}: {e}")
            return None
    
    async def _find_handler_file(self, hook_dir: Path) -> Optional[Path]:
        """
        Find the handler file for a hook
        
        Args:
            hook_dir: Hook directory
            
        Returns:
            Path to handler file or None
        """
        handler_candidates = [
            "handler.py",
            "handler.js", 
            "index.py",
            "index.js",
            "main.py",
            "main.js"
        ]
        
        for candidate in handler_candidates:
            handler_path = hook_dir / candidate
            if handler_path.exists():
                return handler_path
        
        return None
    
    async def _parse_frontmatter(self, hook_md_file: Path) -> Dict[str, str]:
        """
        Parse frontmatter from HOOK.md file
        
        Args:
            hook_md_file: Path to HOOK.md file
            
        Returns:
            Parsed frontmatter dictionary
        """
        try:
            content = hook_md_file.read_text(encoding='utf-8')
            
            # Simple YAML frontmatter parser
            lines = content.split('\n')
            frontmatter = {}
            in_frontmatter = False
            
            for line in lines:
                if line.strip() == '---':
                    if not in_frontmatter:
                        in_frontmatter = True
                        continue
                    else:
                        break
                
                if in_frontmatter and ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()
            
            return frontmatter
            
        except Exception as e:
            logger.error(f"Failed to parse frontmatter from {hook_md_file}: {e}")
            return {}
    
    def _parse_hook_metadata(self, frontmatter: Dict[str, str]) -> Optional[HookMetadata]:
        """
        Parse hook metadata from frontmatter
        
        Args:
            frontmatter: Parsed frontmatter
            
        Returns:
            HookMetadata object or None
        """
        try:
            # Look for metadata section
            metadata_raw = frontmatter.get('metadata', '')
            if not metadata_raw:
                return None
            
            # Parse JSON metadata
            import json
            try:
                metadata_dict = json.loads(metadata_raw)
                moltbot_metadata = metadata_dict.get('moltbot', {})
                
                # Parse requirements
                requires_raw = moltbot_metadata.get('requires', {})
                requires = HookRequirements(
                    bins=requires_raw.get('bins', []),
                    any_bins=requires_raw.get('anyBins', []),
                    env=requires_raw.get('env', []),
                    config=requires_raw.get('config', [])
                )
                
                # Parse install specs
                install_raw = moltbot_metadata.get('install', [])
                install_specs = []
                for spec_dict in install_raw:
                    spec = HookInstallSpec(
                        id=spec_dict.get('id'),
                        kind=spec_dict.get('kind', 'bundled'),
                        label=spec_dict.get('label'),
                        package=spec_dict.get('package'),
                        repository=spec_dict.get('repository'),
                        bins=spec_dict.get('bins', [])
                    )
                    install_specs.append(spec)
                
                # Create metadata
                metadata = HookMetadata(
                    always=moltbot_metadata.get('always', False),
                    hook_key=moltbot_metadata.get('hookKey'),
                    emoji=moltbot_metadata.get('emoji'),
                    homepage=moltbot_metadata.get('homepage'),
                    events=moltbot_metadata.get('events', []),
                    export=moltbot_metadata.get('export', 'default'),
                    os=moltbot_metadata.get('os', []),
                    priority=moltbot_metadata.get('priority', 0),
                    timeout=moltbot_metadata.get('timeout'),
                    retry_count=moltbot_metadata.get('retryCount', 0),
                    requires=requires if any([
                        requires.bins, requires.any_bins, requires.env, requires.config
                    ]) else None,
                    install=install_specs if install_specs else None,
                    tags=moltbot_metadata.get('tags', []),
                    version=moltbot_metadata.get('version', '1.0.0')
                )
                
                return metadata
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid metadata JSON in hook frontmatter")
                return None
                
        except Exception as e:
            logger.error(f"Failed to parse hook metadata: {e}")
            return None
    
    def _parse_invocation_policy(self, frontmatter: Dict[str, str]) -> HookInvocationPolicy:
        """
        Parse invocation policy from frontmatter
        
        Args:
            frontmatter: Parsed frontmatter
            
        Returns:
            HookInvocationPolicy object
        """
        enabled_str = frontmatter.get('enabled', 'true')
        enabled = enabled_str.lower() in ('true', '1', 'yes', 'on')
        
        return HookInvocationPolicy(
            enabled=enabled,
            priority=0,  # Would be parsed from metadata if available
            timeout=None,  # Would be parsed from metadata if available
            retry_count=0,  # Would be parsed from metadata if available
            fail_silent=False
        )
    
    def _filter_and_deduplicate_hooks(
        self, 
        entries: List[HookEntry], 
        config: HookConfig
    ) -> List[HookEntry]:
        """
        Filter and deduplicate hook entries
        
        Args:
            entries: Raw hook entries
            config: Hook configuration
            
        Returns:
            Filtered and deduplicated entries
        """
        # Remove duplicates by name (last one wins)
        unique_hooks: Dict[str, HookEntry] = {}
        for entry in entries:
            unique_hooks[entry.hook.name] = entry
        
        # Apply filters
        filtered_entries = []
        for entry in unique_hooks.values():
            # Skip disabled hooks
            if entry.invocation and not entry.invocation.enabled:
                continue
            
            # Apply hook-specific filters
            if self._should_include_hook(entry, config):
                filtered_entries.append(entry)
        
        return filtered_entries
    
    def _should_include_hook(self, entry: HookEntry, config: HookConfig) -> bool:
        """
        Determine if a hook should be included based on configuration
        
        Args:
            entry: Hook entry to evaluate
            config: Hook configuration
            
        Returns:
            True if hook should be included
        """
        # Check explicit inclusion/exclusion lists
        if config.included_hooks and entry.hook.name not in config.included_hooks:
            return False
        
        if config.excluded_hooks and entry.hook.name in config.excluded_hooks:
            return False
        
        # Check metadata requirements
        if entry.metadata and entry.metadata.os:
            current_os = sys.platform
            if current_os not in entry.metadata.os:
                logger.debug(f"Hook '{entry.hook.name}' excluded: OS requirement not met")
                return False
        
        # Check environment requirements
        if entry.metadata and entry.metadata.requires:
            requirements = entry.metadata.requires
            
            # Check required binaries
            for bin_name in requirements.bins:
                if not self._check_binary_exists(bin_name):
                    logger.debug(f"Hook '{entry.hook.name}' excluded: required binary '{bin_name}' not found")
                    return False
            
            # Check required environment variables
            for env_var in requirements.env:
                if not os.environ.get(env_var):
                    logger.debug(f"Hook '{entry.hook.name}' excluded: required environment variable '{env_var}' not set")
                    return False
        
        return True
    
    def _check_binary_exists(self, binary_name: str) -> bool:
        """
        Check if a binary exists in PATH
        
        Args:
            binary_name: Name of the binary
            
        Returns:
            True if binary exists
        """
        import shutil
        return shutil.which(binary_name) is not None
    
    async def load_hook_handler(self, entry: HookEntry) -> Optional[HookHandler]:
        """
        Load the handler function from a hook entry
        
        Args:
            entry: Hook entry
            
        Returns:
            Handler function or None if loading failed
        """
        try:
            handler_path = Path(entry.hook.handler_path)
            
            if not handler_path.exists():
                logger.error(f"Handler file not found: {handler_path}")
                return None
            
            # Load module
            module_name = f"agentbus_hook_{entry.hook.name}_{hash(str(handler_path))}"
            
            spec = importlib.util.spec_from_file_location(module_name, handler_path)
            if not spec or not spec.loader:
                logger.error(f"Failed to create module spec for {handler_path}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Get handler function
            export_name = entry.metadata.export if entry.metadata else 'default'
            
            if hasattr(module, export_name):
                handler = getattr(module, export_name)
                if callable(handler):
                    self._loaded_modules[entry.hook.name] = module
                    return handler
                else:
                    logger.error(f"Handler '{export_name}' is not callable")
            else:
                logger.error(f"Handler '{export_name}' not found in module")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load hook handler for '{entry.hook.name}': {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get loader statistics"""
        return {
            **self._load_statistics,
            'loaded_modules': len(self._loaded_modules)
        }
    
    def cleanup_loaded_modules(self) -> None:
        """Clean up loaded modules"""
        for module_name in list(self._loaded_modules.keys()):
            if module_name in sys.modules:
                del sys.modules[module_name]
        
        self._loaded_modules.clear()
        logger.debug("Cleaned up loaded hook modules")