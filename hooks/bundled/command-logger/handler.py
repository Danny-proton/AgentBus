"""
Command Logger Hook Handler

Logs all command events for debugging, analytics, and system monitoring.
"""

import json
import hashlib
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
import logging

from ...types import HookEvent, HookResult, HookExecutionContext


class CommandLoggerHook:
    """Hook for logging command events"""
    
    def __init__(
        self,
        log_level: str = "INFO",
        include_args: bool = True,
        include_context: bool = True,
        sanitize_sensitive: bool = True,
        max_log_size: int = 10000,
        log_directory: Optional[str] = None
    ):
        self.log_level = log_level.upper()
        self.include_args = include_args
        self.include_context = include_context
        self.sanitize_sensitive = sanitize_sensitive
        self.max_log_size = max_log_size
        self.log_directory = Path(log_directory) if log_directory else None
        
        # Initialize logger
        self.logger = logging.getLogger("agentbus.command_logger")
        
        # Log statistics
        self.stats = {
            'commands_logged': 0,
            'errors_logged': 0,
            'total_duration': 0.0,
            'last_log': None
        }
        
        # Sensitive data patterns for sanitization
        self.sensitive_patterns = [
            r'password["\s:]+([^"\s,]+)',
            r'token["\s:]+([^"\s,]+)',
            r'api_key["\s:]+([^"\s,]+)',
            r'secret["\s:]+([^"\s,]+)',
            r'key["\s:]+([^"\s,]+)',
        ]
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Handle command events and log them"""
        try:
            # Only process command events
            if event.type.value != "command":
                return HookResult(success=True, data={'no_action_needed': True})
            
            # Create log entry
            log_entry = await self._create_log_entry(event)
            
            # Sanitize if needed
            if self.sanitize_sensitive:
                log_entry = self._sanitize_sensitive_data(log_entry)
            
            # Write log entry
            await self._write_log_entry(log_entry)
            
            # Update statistics
            self._update_statistics(log_entry, success=True)
            
            return HookResult(
                success=True,
                data={
                    'command_logged': True,
                    'log_entry_id': log_entry.get('id'),
                    'stats': self.stats.copy()
                }
            )
            
        except Exception as e:
            # Log the error
            self.logger.error(f"Command logger hook failed: {e}")
            self.stats['errors_logged'] += 1
            
            return HookResult(
                success=False,
                error=str(e)
            )
    
    async def _create_log_entry(self, event: HookEvent) -> Dict[str, Any]:
        """Create a log entry from event data"""
        # Basic log entry structure
        log_entry = {
            'id': self._generate_log_id(),
            'timestamp': event.timestamp.isoformat(),
            'session_key': event.session_key,
            'command': event.data.get('command', 'unknown'),
            'action': event.action,
            'success': event.data.get('success', True),
            'duration_ms': event.data.get('duration', 0) * 1000 if isinstance(event.data.get('duration'), (int, float)) else 0,
            'source': event.source
        }
        
        # Add user and channel info
        if event.context.user_id:
            log_entry['user_id'] = event.context.user_id
        if event.context.channel_id:
            log_entry['channel_id'] = event.context.channel_id
        if event.context.agent_id:
            log_entry['agent_id'] = event.context.agent_id
        
        # Add command arguments if configured
        if self.include_args:
            args = event.data.get('args', [])
            if isinstance(args, list):
                log_entry['args'] = args
            elif isinstance(args, str):
                log_entry['args'] = args.split()
        
        # Add context data if configured
        if self.include_context and event.context.metadata:
            log_entry['context'] = self._extract_relevant_context(event.context.metadata)
        
        # Add error information if command failed
        if not event.data.get('success', True):
            log_entry['error'] = {
                'type': event.data.get('error_type', 'unknown'),
                'message': event.data.get('error_message', 'No error message'),
                'stack_trace': event.data.get('stack_trace')
            }
        
        # Add performance metrics if available
        if 'performance' in event.data:
            log_entry['performance'] = event.data['performance']
        
        return log_entry
    
    def _sanitize_sensitive_data(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or mask sensitive data from log entry"""
        sensitive_fields = ['password', 'token', 'api_key', 'secret', 'key']
        
        def sanitize_string(text: str) -> str:
            if not isinstance(text, str):
                return text
            
            sanitized = text
            for pattern in self.sensitive_patterns:
                sanitized = re.sub(pattern, r'\1: [REDACTED]', sanitized, flags=re.IGNORECASE)
            
            return sanitized
        
        def sanitize_dict(obj: Dict[str, Any]) -> Dict[str, Any]:
            if not isinstance(obj, dict):
                return obj
            
            result = {}
            for key, value in obj.items():
                if key.lower() in sensitive_fields:
                    result[key] = '[REDACTED]'
                elif isinstance(value, str):
                    result[key] = sanitize_string(value)
                elif isinstance(value, dict):
                    result[key] = sanitize_dict(value)
                elif isinstance(value, list):
                    result[key] = [sanitize_string(item) if isinstance(item, str) else item for item in value]
                else:
                    result[key] = value
            
            return result
        
        # Sanitize entire log entry
        return sanitize_dict(log_entry)
    
    def _extract_relevant_context(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant context information"""
        relevant_keys = [
            'workspace_dir', 'user_preferences', 'session_settings',
            'environment', 'configuration', 'features_enabled'
        ]
        
        relevant_context = {}
        for key in relevant_keys:
            if key in metadata:
                relevant_context[key] = metadata[key]
        
        return relevant_context
    
    def _generate_log_id(self) -> str:
        """Generate unique log entry ID"""
        timestamp = datetime.now().isoformat()
        random_part = hashlib.md5(f"{timestamp}:{id(self)}".encode()).hexdigest()[:8]
        return f"cmd_{timestamp.replace(':', '').replace('-', '').replace('.', '')}_{random_part}"
    
    async def _write_log_entry(self, log_entry: Dict[str, Any]) -> None:
        """Write log entry to appropriate destination"""
        # Console logging
        if self.logger.isEnabledFor(getattr(logging, self.log_level)):
            message = self._format_log_message(log_entry)
            self.logger.log(getattr(logging, self.log_level), message)
        
        # File logging
        if self.log_directory:
            await self._write_to_file(log_entry)
    
    def _format_log_message(self, log_entry: Dict[str, Any]) -> str:
        """Format log entry as human-readable message"""
        command = log_entry['command']
        success = "✅" if log_entry['success'] else "❌"
        duration = f"{log_entry['duration_ms']:.0f}ms"
        user = log_entry.get('user_id', 'unknown')
        
        base_msg = f"{success} {command} ({duration}) by {user}"
        
        if not log_entry['success']:
            error_msg = log_entry.get('error', {}).get('message', 'Unknown error')
            base_msg += f" - Error: {error_msg}"
        
        return base_msg
    
    async def _write_to_file(self, log_entry: Dict[str, Any]) -> None:
        """Write log entry to file"""
        try:
            # Ensure log directory exists
            self.log_directory.mkdir(parents=True, exist_ok=True)
            
            # Create daily log file
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = self.log_directory / f"commands_{date_str}.log"
            
            # Check file size and rotate if needed
            if log_file.exists() and log_file.stat().st_size > self.max_log_size * 1024:
                await self._rotate_log_file(log_file)
            
            # Write entry
            log_line = json.dumps(log_entry, ensure_ascii=False) + "\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
                
        except Exception as e:
            self.logger.error(f"Failed to write to log file: {e}")
    
    async def _rotate_log_file(self, log_file: Path) -> None:
        """Rotate log file when size limit is reached"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_file = log_file.with_suffix(f".{timestamp}.log")
            
            log_file.rename(rotated_file)
            
            # Compress old file
            import gzip
            with open(rotated_file, 'rb') as f_in:
                with gzip.open(f"{rotated_file}.gz", 'wb') as f_out:
                    f_out.writelines(f_in)
            
            rotated_file.unlink()
            
        except Exception as e:
            self.logger.error(f"Failed to rotate log file: {e}")
    
    def _update_statistics(self, log_entry: Dict[str, Any], success: bool) -> None:
        """Update logging statistics"""
        self.stats['commands_logged'] += 1
        self.stats['last_log'] = datetime.now().isoformat()
        
        duration = log_entry.get('duration_ms', 0)
        self.stats['total_duration'] += duration
        
        if not success:
            self.stats['errors_logged'] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get logging statistics"""
        stats = self.stats.copy()
        
        # Calculate derived statistics
        if stats['commands_logged'] > 0:
            stats['average_duration_ms'] = stats['total_duration'] / stats['commands_logged']
            stats['success_rate'] = (stats['commands_logged'] - stats['errors_logged']) / stats['commands_logged']
        else:
            stats['average_duration_ms'] = 0
            stats['success_rate'] = 0
        
        return stats
    
    async def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent log entries from file"""
        if not self.log_directory:
            return []
        
        try:
            # Get latest log file
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = self.log_directory / f"commands_{date_str}.log"
            
            if not log_file.exists():
                return []
            
            # Read recent entries
            logs = []
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
            
            return logs[-limit:]  # Return last 'limit' entries
            
        except Exception as e:
            self.logger.error(f"Failed to read recent logs: {e}")
            return []
    
    async def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """Cleanup old log files"""
        if not self.log_directory:
            return 0
        
        try:
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_to_keep)
            
            removed_count = 0
            
            for log_file in self.log_directory.glob("commands_*.log*"):
                try:
                    if log_file.stat().st_mtime < cutoff_date.timestamp():
                        log_file.unlink()
                        removed_count += 1
                except Exception:
                    continue
            
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")
            return 0


# Default hook instance
default_command_logger = CommandLoggerHook()


async def handler(event: HookEvent) -> HookResult:
    """Handler function for the command-logger hook"""
    return await default_command_logger(event)


# Export for compatibility
__all__ = ['CommandLoggerHook', 'handler']