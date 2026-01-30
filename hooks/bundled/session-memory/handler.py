"""
Session Memory Hook Handler

Saves session context to memory files when sessions end.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from ...types import HookEvent, HookResult, HookExecutionContext


class SessionMemoryHook:
    """Hook for saving session context to memory files"""
    
    def __init__(self, max_memory_files: int = 100, include_messages: bool = True):
        self.max_memory_files = max_memory_files
        self.include_messages = include_messages
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Handle session end events and save to memory"""
        try:
            # Only process session end events
            if event.type.value != "session" or event.action != "end":
                return HookResult(success=True, data={'no_action_needed': True})
            
            context = event.context
            
            # Validate workspace directory
            if not context.workspace_dir:
                return HookResult(
                    success=False,
                    error="No workspace directory provided"
                )
            
            # Create memory directory
            memory_dir = Path(context.workspace_dir) / "memory"
            memory_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = event.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"session_{event.session_key}_{timestamp}.md"
            memory_file = memory_dir / filename
            
            # Create memory content
            memory_content = await self._create_memory_content(event)
            
            # Write to file
            with open(memory_file, 'w', encoding='utf-8') as f:
                f.write(memory_content)
            
            # Cleanup old files if needed
            await self._cleanup_old_files(memory_dir)
            
            # Get relative path for display
            relative_path = str(memory_file.relative_to(Path.cwd()))
            
            return HookResult(
                success=True,
                data={
                    'memory_saved': True,
                    'memory_file': str(memory_file),
                    'relative_path': relative_path,
                    'file_size': len(memory_content)
                }
            )
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )
    
    async def _create_memory_content(self, event: HookEvent) -> str:
        """Create memory file content"""
        content = [
            f"# Session Memory: {event.session_key}",
            "",
            f"**Timestamp:** {event.timestamp.isoformat()}",
            f"**Agent ID:** {event.context.agent_id or 'Unknown'}",
            f"**Channel ID:** {event.context.channel_id or 'Unknown'}",
            f"**User ID:** {event.context.user_id or 'Unknown'}",
            ""
        ]
        
        # Add session metadata
        if hasattr(event, 'data') and event.data:
            content.append("## Session Metadata")
            content.append("")
            
            session_metadata = {
                'session_key': event.session_key,
                'start_time': event.data.get('start_time'),
                'end_time': event.timestamp.isoformat(),
                'total_events': len(event.data.get('events', [])),
                'duration': self._calculate_duration(event.data)
            }
            
            for key, value in session_metadata.items():
                if value is not None:
                    content.append(f"- **{key.replace('_', ' ').title()}:** {value}")
            content.append("")
        
        # Add event summary
        content.append("## Event Summary")
        content.append("")
        
        events = event.data.get('events', [])
        if events:
            # Group events by type
            events_by_type = {}
            for evt in events:
                evt_type = evt.get('type', 'unknown')
                if evt_type not in events_by_type:
                    events_by_type[evt_type] = []
                events_by_type[evt_type].append(evt)
            
            # Add summary for each type
            for evt_type, type_events in events_by_type.items():
                content.append(f"### {evt_type.title()} Events ({len(type_events)})")
                content.append("")
                
                for evt in type_events[-5:]:  # Last 5 events of each type
                    action = evt.get('action', 'unknown')
                    timestamp = evt.get('timestamp', 'unknown')
                    content.append(f"- **{action}** at {timestamp}")
                
                if len(type_events) > 5:
                    content.append(f"- ... and {len(type_events) - 5} more {evt_type} events")
                content.append("")
        else:
            content.append("No events recorded.")
            content.append("")
        
        # Add messages if configured and available
        if self.include_messages and event.messages:
            content.append("## Session Messages")
            content.append("")
            
            for message in event.messages[:10]:  # First 10 messages
                content.append(f"- {message}")
            
            if len(event.messages) > 10:
                content.append(f"- ... and {len(event.messages) - 10} more messages")
            content.append("")
        
        # Add context data
        if event.data:
            content.append("## Context Data")
            content.append("")
            content.append("```json")
            content.append(json.dumps(event.data, indent=2, default=str))
            content.append("```")
            content.append("")
        
        # Add footer
        content.extend([
            "---",
            f"*Generated by AgentBus Hook System on {datetime.now().isoformat()}*",
            f"*Hook: session-memory v1.0.0*"
        ])
        
        return "\n".join(content)
    
    def _calculate_duration(self, event_data: Dict[str, Any]) -> Optional[str]:
        """Calculate session duration"""
        try:
            start_time = event_data.get('start_time')
            if not start_time:
                return None
            
            start = datetime.fromisoformat(start_time)
            end = datetime.now()
            duration = end - start
            
            # Format duration
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
                
        except Exception:
            return None
    
    async def _cleanup_old_files(self, memory_dir: Path) -> None:
        """Cleanup old memory files if limit exceeded"""
        try:
            # Get all session memory files
            memory_files = list(memory_dir.glob("session_*.md"))
            
            if len(memory_files) <= self.max_memory_files:
                return
            
            # Sort by modification time (oldest first)
            memory_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Remove oldest files
            files_to_remove = memory_files[:len(memory_files) - self.max_memory_files]
            
            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                except Exception as e:
                    # Log but continue cleanup
                    pass  # Could add logging here
            
        except Exception:
            # If cleanup fails, don't fail the hook
            pass


# Default hook instance
default_session_memory_hook = SessionMemoryHook()


async def handler(event: HookEvent) -> HookResult:
    """Handler function for the session-memory hook"""
    return await default_session_memory_hook(event)


# Export for compatibility
__all__ = ['SessionMemoryHook', 'handler']