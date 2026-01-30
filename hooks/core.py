"""
AgentBus Hook System Core

Provides the core hook registry and event triggering system for AgentBus.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set, Callable, Any
from collections import defaultdict
from datetime import datetime

from .types import (
    Hook, HookEvent, HookResult, HookHandler, HookEventType,
    HookExecutionContext, HookPriority, HookEntry
)
from .priority import PriorityManager


logger = logging.getLogger(__name__)


class HookRegistry:
    """Registry for managing hook handlers"""
    
    def __init__(self):
        self._handlers: Dict[str, List[tuple[int, HookHandler]]] = defaultdict(list)
        self._hook_entries: Dict[str, HookEntry] = {}
        self._priority_manager = PriorityManager()
        self._statistics = {
            'registered': 0,
            'executed': 0,
            'successful': 0,
            'failed': 0,
            'total_execution_time': 0.0
        }
    
    def register(
        self, 
        event_key: str, 
        handler: HookHandler, 
        priority: int = 0,
        hook_entry: Optional[HookEntry] = None
    ) -> bool:
        """
        Register a hook handler for a specific event
        
        Args:
            event_key: Event type or specific action (e.g., 'command' or 'command:new')
            handler: Function to call when event is triggered
            priority: Execution priority (higher numbers run first)
            hook_entry: Optional hook entry metadata
            
        Returns:
            True if registration successful
        """
        try:
            # Generate handler ID if not provided
            if hook_entry and hook_entry.hook.name:
                handler_id = f"{event_key}:{hook_entry.hook.name}"
            else:
                handler_id = f"{event_key}:{id(handler)}"
            
            # Add to priority manager
            self._priority_manager.register(event_key, priority, handler_id)
            
            # Add handler to registry
            self._handlers[event_key].append((priority, handler))
            
            # Sort handlers by priority (highest first)
            self._handlers[event_key].sort(key=lambda x: x[0], reverse=True)
            
            # Store hook entry if provided
            if hook_entry:
                self._hook_entries[event_key] = hook_entry
            
            logger.debug(f"Registered hook handler for '{event_key}' with priority {priority}")
            self._statistics['registered'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to register hook handler for '{event_key}': {e}")
            return False
    
    def unregister(self, event_key: str, handler: HookHandler) -> bool:
        """
        Unregister a specific hook handler
        
        Args:
            event_key: Event key the handler was registered for
            handler: Handler function to remove
            
        Returns:
            True if unregistration successful
        """
        try:
            handlers = self._handlers.get(event_key, [])
            
            # Find and remove handler
            for i, (priority, existing_handler) in enumerate(handlers):
                if existing_handler == handler:
                    handlers.pop(i)
                    # Use a unique handler ID for priority manager
                    handler_id = f"{event_key}:{id(handler)}"
                    self._priority_manager.unregister(event_key, handler_id)
                    logger.debug(f"Unregistered hook handler for '{event_key}'")
                    return True
            
            logger.warning(f"Handler not found for event key '{event_key}'")
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister hook handler for '{event_key}': {e}")
            return False
    
    def clear(self, event_key: Optional[str] = None) -> None:
        """
        Clear all registered hooks or hooks for specific event
        
        Args:
            event_key: Specific event key to clear, or None to clear all
        """
        if event_key:
            if event_key in self._handlers:
                del self._handlers[event_key]
            if event_key in self._hook_entries:
                del self._hook_entries[event_key]
            self._priority_manager.clear(event_key)
            logger.debug(f"Cleared hooks for event '{event_key}'")
        else:
            self._handlers.clear()
            self._hook_entries.clear()
            self._priority_manager.clear()
            logger.info("Cleared all hook registrations")
    
    def get_handlers(self, event_key: str) -> List[tuple[int, HookHandler]]:
        """
        Get all handlers for an event key
        
        Args:
            event_key: Event key to get handlers for
            
        Returns:
            List of (priority, handler) tuples
        """
        return self._handlers.get(event_key, [])
    
    def get_registered_event_keys(self) -> List[str]:
        """Get all registered event keys"""
        return list(self._handlers.keys())
    
    def get_hook_entry(self, event_key: str) -> Optional[HookEntry]:
        """Get hook entry for event key"""
        return self._hook_entries.get(event_key)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get hook registry statistics"""
        return {
            **self._statistics,
            'registered_events': len(self._handlers),
            'total_handlers': sum(len(handlers) for handlers in self._handlers.values())
        }


class HookEngine:
    """Core engine for triggering and executing hooks"""
    
    def __init__(self):
        self.registry = HookRegistry()
        self._execution_lock = asyncio.Lock()
        self._is_enabled = True
        self._max_concurrent_executions = 10
        self._active_executions: Set[asyncio.Task] = set()
    
    async def trigger(
        self, 
        event: HookEvent, 
        timeout: Optional[int] = None
    ) -> List[HookResult]:
        """
        Trigger hook execution for an event
        
        Args:
            event: Event to trigger hooks for
            timeout: Maximum execution time per handler
            
        Returns:
            List of execution results
        """
        if not self._is_enabled:
            logger.debug("Hook engine is disabled, skipping event triggering")
            return []
        
        async with self._execution_lock:
            logger.debug(f"Triggering hooks for event: {event.type.value}:{event.action}")
            
            # Get handlers for both the event type and specific action
            type_handlers = self.registry.get_handlers(event.type.value)
            specific_handlers = self.registry.get_handlers(f"{event.type.value}:{event.action}")
            
            # Combine and execute handlers
            all_handlers = type_handlers + specific_handlers
            
            if not all_handlers:
                logger.debug(f"No handlers found for event: {event.type.value}:{event.action}")
                return []
            
            logger.info(f"Executing {len(all_handlers)} hook handlers")
            
            # Execute handlers concurrently
            tasks = []
            for priority, handler in all_handlers:
                task = asyncio.create_task(
                    self._execute_handler(handler, event, timeout)
                )
                tasks.append(task)
                self._active_executions.add(task)
            
            try:
                # Wait for all handlers to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                processed_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        processed_results.append(HookResult(
                            success=False,
                            error=str(result),
                            execution_time=0.0
                        ))
                        logger.error(f"Handler execution failed: {result}")
                    else:
                        processed_results.append(result)
                
                return processed_results
                
            finally:
                # Clean up active executions
                self._active_executions.difference_update(tasks)
    
    async def _execute_handler(
        self, 
        handler: HookHandler, 
        event: HookEvent, 
        timeout: Optional[int] = None
    ) -> HookResult:
        """
        Execute a single hook handler with timeout and error handling
        
        Args:
            handler: Hook handler function
            event: Event to process
            timeout: Maximum execution time
            
        Returns:
            Execution result
        """
        start_time = time.time()
        
        try:
            # Execute handler with timeout
            if timeout:
                result = await asyncio.wait_for(handler(event), timeout=timeout)
            else:
                result = await handler(event)
            
            execution_time = time.time() - start_time
            
            # Update statistics
            self.registry._statistics['executed'] += 1
            self.registry._statistics['total_execution_time'] += execution_time
            
            if result.success:
                self.registry._statistics['successful'] += 1
            else:
                self.registry._statistics['failed'] += 1
            
            # Add execution time to result
            result.execution_time = execution_time
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.error(f"Handler execution timed out after {timeout}s")
            return HookResult(
                success=False,
                error=f"Execution timed out after {timeout}s",
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Handler execution failed: {e}")
            return HookResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def enable(self) -> None:
        """Enable the hook engine"""
        self._is_enabled = True
        logger.info("Hook engine enabled")
    
    def disable(self) -> None:
        """Disable the hook engine"""
        self._is_enabled = False
        logger.info("Hook engine disabled")
    
    async def shutdown(self) -> None:
        """Shutdown hook engine and wait for active executions"""
        logger.info("Shutting down hook engine...")
        
        # Disable new executions
        self.disable()
        
        # Cancel active executions
        for task in self._active_executions:
            if not task.done():
                task.cancel()
        
        # Wait for active executions to complete
        if self._active_executions:
            await asyncio.gather(*self._active_executions, return_exceptions=True)
        
        logger.info("Hook engine shutdown complete")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            'registry': self.registry.get_statistics(),
            'is_enabled': self._is_enabled,
            'active_executions': len(self._active_executions),
            'max_concurrent': self._max_concurrent_executions
        }


# Global hook engine instance
hook_engine = HookEngine()


# Convenience functions for working with hooks
async def trigger_hook(
    event_type: HookEventType,
    action: str,
    session_key: str,
    context: Optional[HookExecutionContext] = None,
    **kwargs
) -> List[HookResult]:
    """
    Convenience function to trigger hooks
    
    Args:
        event_type: Type of event
        action: Specific action
        session_key: Session identifier
        context: Execution context
        **kwargs: Additional event data
        
    Returns:
        List of hook execution results
    """
    event = HookEvent(
        type=event_type,
        action=action,
        session_key=session_key,
        context=context or HookExecutionContext(session_key=session_key),
        data=kwargs
    )
    
    return await hook_engine.trigger(event)


def register_hook(
    event_key: str,
    handler: HookHandler,
    priority: int = 0,
    hook_entry: Optional[HookEntry] = None
) -> bool:
    """
    Convenience function to register hooks
    
    Args:
        event_key: Event key to register for
        handler: Handler function
        priority: Execution priority
        hook_entry: Optional hook metadata
        
    Returns:
        True if registration successful
    """
    return hook_engine.registry.register(event_key, handler, priority, hook_entry)


def get_hook_engine() -> HookEngine:
    """Get the global hook engine instance"""
    return hook_engine