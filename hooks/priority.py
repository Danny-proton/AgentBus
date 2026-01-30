"""
AgentBus Hook Priority Management

Provides sophisticated priority management for hook execution order.
"""

import heapq
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import IntEnum
import logging

logger = logging.getLogger(__name__)


class HookPriority(IntEnum):
    """Standard priority levels for hooks"""
    CRITICAL = 1000
    HIGH = 500
    NORMAL = 0
    LOW = -500
    BACKGROUND = -1000


@dataclass
class PriorityEntry:
    """Entry in priority queue"""
    priority: int
    event_key: str
    handler_id: str
    timestamp: float
    weight: float = 1.0
    
    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority > other.priority  # Higher priority first
        return self.timestamp < other.timestamp  # Earlier registration first
    
    def __eq__(self, other):
        return (self.priority == other.priority and 
                self.event_key == other.event_key and 
                self.handler_id == other.handler_id)


class PriorityManager:
    """Manages hook execution priorities"""
    
    def __init__(self):
        self._queues: Dict[str, List[PriorityEntry]] = {}
        self._handler_registry: Dict[str, PriorityEntry] = {}
        self._execution_order_cache: Dict[str, List[PriorityEntry]] = {}
        self._statistics = {
            'total_registrations': 0,
            'priority_conflicts': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def register(
        self, 
        event_key: str, 
        priority: int, 
        handler_id: Optional[str] = None,
        weight: float = 1.0
    ) -> bool:
        """
        Register a handler with a priority level
        
        Args:
            event_key: Event key to register for
            priority: Priority level (higher = earlier execution)
            handler_id: Unique handler identifier
            weight: Execution weight (affects ordering within same priority)
            
        Returns:
            True if registration successful
        """
        try:
            if handler_id is None:
                handler_id = f"{event_key}:{id(handler_id)}"
            
            # Create priority entry
            entry = PriorityEntry(
                priority=priority,
                event_key=event_key,
                handler_id=handler_id,
                timestamp=time.time(),
                weight=weight
            )
            
            # Add to event queue
            if event_key not in self._queues:
                self._queues[event_key] = []
            
            # Check for priority conflicts
            existing_priorities = {e.priority for e in self._queues[event_key]}
            if priority in existing_priorities:
                self._statistics['priority_conflicts'] += 1
                logger.debug(f"Priority conflict detected for {event_key} at level {priority}")
            
            heapq.heappush(self._queues[event_key], entry)
            self._handler_registry[handler_id] = entry
            
            # Invalidate cache
            if event_key in self._execution_order_cache:
                del self._execution_order_cache[event_key]
            
            self._statistics['total_registrations'] += 1
            logger.debug(f"Registered handler '{handler_id}' for '{event_key}' with priority {priority}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register handler for '{event_key}': {e}")
            return False
    
    def unregister(self, event_key: str, handler_id: str) -> bool:
        """
        Unregister a handler from priority queue
        
        Args:
            event_key: Event key
            handler_id: Handler identifier
            
        Returns:
            True if unregistration successful
        """
        try:
            # Find and remove from registry
            if handler_id not in self._handler_registry:
                logger.warning(f"Handler '{handler_id}' not found in registry")
                return False
            
            entry = self._handler_registry[handler_id]
            del self._handler_registry[handler_id]
            
            # Remove from queue (mark as removed rather than actual removal)
            queue = self._queues.get(event_key, [])
            for i, queue_entry in enumerate(queue):
                if queue_entry.handler_id == handler_id:
                    # Mark as removed by setting priority to very low
                    queue[i] = PriorityEntry(
                        priority=-999999,
                        event_key=event_key,
                        handler_id=handler_id,
                        timestamp=queue_entry.timestamp,
                        weight=0.0
                    )
                    break
            
            # Invalidate cache
            if event_key in self._execution_order_cache:
                del self._execution_order_cache[event_key]
            
            logger.debug(f"Unregistered handler '{handler_id}' from '{event_key}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister handler '{handler_id}': {e}")
            return False
    
    def get_execution_order(self, event_key: str) -> List[PriorityEntry]:
        """
        Get sorted execution order for an event key
        
        Args:
            event_key: Event key to get order for
            
        Returns:
            List of priority entries in execution order
        """
        try:
            # Check cache first
            if event_key in self._execution_order_cache:
                self._statistics['cache_hits'] += 1
                return self._execution_order_cache[event_key]
            
            self._statistics['cache_misses'] += 1
            
            # Get queue and sort
            queue = self._queues.get(event_key, [])
            if not queue:
                return []
            
            # Create sorted copy and filter removed entries
            active_entries = [
                entry for entry in sorted(queue) 
                if entry.priority > -999999 and entry.weight > 0
            ]
            
            # Cache result
            self._execution_order_cache[event_key] = active_entries
            
            return active_entries
            
        except Exception as e:
            logger.error(f"Failed to get execution order for '{event_key}': {e}")
            return []
    
    def adjust_priority(
        self, 
        event_key: str, 
        handler_id: str, 
        new_priority: int,
        new_weight: Optional[float] = None
    ) -> bool:
        """
        Adjust priority and/or weight of a registered handler
        
        Args:
            event_key: Event key
            handler_id: Handler identifier
            new_priority: New priority level
            new_weight: New weight (optional)
            
        Returns:
            True if adjustment successful
        """
        try:
            if handler_id not in self._handler_registry:
                logger.warning(f"Handler '{handler_id}' not found for priority adjustment")
                return False
            
            entry = self._handler_registry[handler_id]
            
            # Update values
            old_priority = entry.priority
            entry.priority = new_priority
            
            if new_weight is not None:
                entry.weight = new_weight
            
            # Invalidate cache
            if event_key in self._execution_order_cache:
                del self._execution_order_cache[event_key]
            
            logger.debug(
                f"Adjusted priority for '{handler_id}': {old_priority} -> {new_priority}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to adjust priority for '{handler_id}': {e}")
            return False
    
    def get_priority_statistics(self, event_key: str) -> Dict[str, Any]:
        """
        Get priority statistics for an event key
        
        Args:
            event_key: Event key to get statistics for
            
        Returns:
            Dictionary with priority statistics
        """
        queue = self._queues.get(event_key, [])
        active_entries = [
            entry for entry in queue 
            if entry.priority > -999999 and entry.weight > 0
        ]
        
        if not active_entries:
            return {
                'total_handlers': 0,
                'priority_range': (0, 0),
                'average_priority': 0,
                'most_common_priority': None
            }
        
        priorities = [entry.priority for entry in active_entries]
        
        # Find most common priority
        priority_counts = {}
        for priority in priorities:
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        most_common = max(priority_counts.items(), key=lambda x: x[1])
        
        return {
            'total_handlers': len(active_entries),
            'priority_range': (min(priorities), max(priorities)),
            'average_priority': sum(priorities) / len(priorities),
            'most_common_priority': most_common[0],
            'priority_distribution': priority_counts,
            'total_registered': len(queue),
            'removed_entries': len(queue) - len(active_entries)
        }
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global priority management statistics"""
        return {
            **self._statistics,
            'total_event_keys': len(self._queues),
            'total_active_handlers': len(self._handler_registry),
            'cached_event_keys': len(self._execution_order_cache)
        }
    
    def clear(self, event_key: Optional[str] = None) -> None:
        """
        Clear priority queues
        
        Args:
            event_key: Specific event key to clear, or None for all
        """
        if event_key:
            if event_key in self._queues:
                del self._queues[event_key]
            if event_key in self._execution_order_cache:
                del self._execution_order_cache[event_key]
            
            # Remove handlers for this event
            handlers_to_remove = [
                handler_id for handler_id, entry in self._handler_registry.items()
                if entry.event_key == event_key
            ]
            for handler_id in handlers_to_remove:
                del self._handler_registry[handler_id]
            
            logger.debug(f"Cleared priority queue for '{event_key}'")
        else:
            self._queues.clear()
            self._execution_order_cache.clear()
            self._handler_registry.clear()
            logger.info("Cleared all priority queues")


# Utility functions for priority management
def normalize_priority(priority: int, min_val: int = -1000, max_val: int = 1000) -> int:
    """
    Normalize priority to valid range
    
    Args:
        priority: Raw priority value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Normalized priority
    """
    return max(min_val, min(max_val, priority))


def compare_priorities(priority1: int, priority2: int) -> int:
    """
    Compare two priorities
    
    Args:
        priority1: First priority
        priority2: Second priority
        
    Returns:
        -1 if priority1 < priority2, 0 if equal, 1 if priority1 > priority2
    """
    if priority1 < priority2:
        return -1
    elif priority1 > priority2:
        return 1
    else:
        return 0


def priority_to_level(priority: int) -> str:
    """
    Convert numeric priority to descriptive level
    
    Args:
        priority: Numeric priority
        
    Returns:
        Descriptive priority level
    """
    if priority >= HookPriority.CRITICAL:
        return "CRITICAL"
    elif priority >= HookPriority.HIGH:
        return "HIGH"
    elif priority >= HookPriority.NORMAL:
        return "NORMAL"
    elif priority >= HookPriority.LOW:
        return "LOW"
    else:
        return "BACKGROUND"