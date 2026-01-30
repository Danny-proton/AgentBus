"""
Example Hooks for AgentBus

Demonstrates how to create custom hooks for various use cases.
"""

import json
import time
from typing import Any, Dict, List
from datetime import datetime

from ..types import HookEvent, HookResult, HookExecutionContext


class WelcomeHook:
    """Hook that sends welcome messages for new users"""
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Handle welcome events"""
        try:
            if event.type.value == "session" and event.action == "start":
                user_id = event.context.user_id
                
                welcome_message = (
                    f"👋 Welcome to AgentBus! I'm here to help you with various tasks.\n\n"
                    f"Available features:\n"
                    f"• 🧠 AI-powered conversations\n"
                    f"• 🔧 Custom automation\n"
                    f"• 📊 Data analysis\n"
                    f"• 🌐 Web interactions\n\n"
                    f"Type 'help' to see available commands!"
                )
                
                return HookResult(
                    success=True,
                    messages=[welcome_message],
                    data={'user_id': user_id}
                )
            
            return HookResult(success=True, data={'no_welcome_needed': True})
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )


class CommandLoggerHook:
    """Hook that logs all commands for analysis"""
    
    def __init__(self):
        self.command_history = []
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Log commands for analysis"""
        try:
            if event.type.value == "command":
                command_data = {
                    'timestamp': datetime.now().isoformat(),
                    'command': event.data.get('command', ''),
                    'args': event.data.get('args', []),
                    'user_id': event.context.user_id,
                    'session_key': event.session_key,
                    'channel_id': event.context.channel_id
                }
                
                self.command_history.append(command_data)
                
                # Keep only last 1000 commands in memory
                if len(self.command_history) > 1000:
                    self.command_history = self.command_history[-1000:]
                
                return HookResult(
                    success=True,
                    data={
                        'command_logged': True,
                        'total_commands': len(self.command_history)
                    }
                )
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )
    
    def get_command_stats(self) -> Dict[str, Any]:
        """Get command usage statistics"""
        if not self.command_history:
            return {'total_commands': 0}
        
        # Count commands by type
        command_counts = {}
        user_counts = {}
        
        for cmd in self.command_history:
            command = cmd.get('command', 'unknown')
            user_id = cmd.get('user_id', 'unknown')
            
            command_counts[command] = command_counts.get(command, 0) + 1
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        
        return {
            'total_commands': len(self.command_history),
            'unique_commands': len(command_counts),
            'unique_users': len(user_counts),
            'most_used_commands': sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'most_active_users': sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }


class SessionMemoryHook:
    """Hook that saves session context to memory files"""
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Save session to memory on session end"""
        try:
            if event.type.value == "session" and event.action == "end":
                context = event.context
                
                if not context.workspace_dir:
                    return HookResult(
                        success=False,
                        error="No workspace directory provided"
                    )
                
                # Create memory directory if it doesn't exist
                from pathlib import Path
                memory_dir = Path(context.workspace_dir) / "memory"
                memory_dir.mkdir(exist_ok=True)
                
                # Create memory file with session summary
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                memory_file = memory_dir / f"session_{event.session_key}_{timestamp}.md"
                
                memory_content = self._create_memory_content(event)
                
                with open(memory_file, 'w', encoding='utf-8') as f:
                    f.write(memory_content)
                
                return HookResult(
                    success=True,
                    data={
                        'memory_saved': True,
                        'memory_file': str(memory_file)
                    }
                )
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )
    
    def _create_memory_content(self, event: HookEvent) -> str:
        """Create memory file content"""
        content = [
            f"# Session Memory: {event.session_key}",
            "",
            f"**Timestamp:** {event.timestamp.isoformat()}",
            f"**Agent ID:** {event.context.agent_id or 'Unknown'}",
            f"**Channel ID:** {event.context.channel_id or 'Unknown'}",
            f"**User ID:** {event.context.user_id or 'Unknown'}",
            "",
            "## Session Summary",
            ""
        ]
        
        # Add event data if available
        if event.data:
            content.append("### Event Data")
            content.append("```json")
            content.append(json.dumps(event.data, indent=2, default=str))
            content.append("```")
            content.append("")
        
        # Add messages if available
        if event.messages:
            content.append("### Messages")
            for message in event.messages:
                content.append(f"- {message}")
            content.append("")
        
        content.append("---")
        content.append(f"*Generated by AgentBus Hook System on {datetime.now().isoformat()}*")
        
        return "\n".join(content)


class RateLimitHook:
    """Hook that implements rate limiting for users"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.user_requests = {}  # user_id -> [timestamps]
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Check and enforce rate limits"""
        try:
            if event.type.value == "command":
                user_id = event.context.user_id
                
                if not user_id:
                    return HookResult(success=True)  # Allow requests without user ID
                
                current_time = time.time()
                
                # Clean up old requests for this user
                if user_id in self.user_requests:
                    self.user_requests[user_id] = [
                        ts for ts in self.user_requests[user_id]
                        if current_time - ts < self.time_window
                    ]
                else:
                    self.user_requests[user_id] = []
                
                # Check if user has exceeded rate limit
                if len(self.user_requests[user_id]) >= self.max_requests:
                    return HookResult(
                        success=False,
                        error=f"Rate limit exceeded. You can make {self.max_requests} requests per {self.time_window} seconds.",
                        data={'rate_limited': True}
                    )
                
                # Add current request
                self.user_requests[user_id].append(current_time)
                
                return HookResult(
                    success=True,
                    data={'rate_limit_checked': True}
                )
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )


class HealthCheckHook:
    """Hook that performs periodic health checks"""
    
    def __init__(self):
        self.health_status = {
            'status': 'healthy',
            'last_check': None,
            'checks_performed': 0,
            'issues': []
        }
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Perform health check"""
        try:
            if event.type.value == "health" and event.action == "check":
                self.health_status['last_check'] = datetime.now().isoformat()
                self.health_status['checks_performed'] += 1
                
                # Perform basic health checks
                issues = []
                
                # Check memory usage
                try:
                    import psutil
                    memory_percent = psutil.virtual_memory().percent
                    if memory_percent > 85:
                        issues.append(f"High memory usage: {memory_percent}%")
                except ImportError:
                    pass
                
                # Check disk usage
                try:
                    import psutil
                    disk_percent = psutil.disk_usage('/').percent
                    if disk_percent > 90:
                        issues.append(f"High disk usage: {disk_percent}%")
                except ImportError:
                    pass
                
                self.health_status['issues'] = issues
                self.health_status['status'] = 'degraded' if issues else 'healthy'
                
                return HookResult(
                    success=True,
                    data=self.health_status
                )
            
            return HookResult(success=True)
            
        except Exception as e:
            self.health_status['status'] = 'unhealthy'
            return HookResult(
                success=False,
                error=str(e)
            )


# Example hook creators
def create_welcome_hook() -> WelcomeHook:
    """Create a welcome hook instance"""
    return WelcomeHook()


def create_command_logger_hook() -> CommandLoggerHook:
    """Create a command logger hook instance"""
    return CommandLoggerHook()


def create_session_memory_hook() -> SessionMemoryHook:
    """Create a session memory hook instance"""
    return SessionMemoryHook()


def create_rate_limit_hook(max_requests: int = 10, time_window: int = 60) -> RateLimitHook:
    """Create a rate limit hook instance"""
    return RateLimitHook(max_requests, time_window)


def create_health_check_hook() -> HealthCheckHook:
    """Create a health check hook instance"""
    return HealthCheckHook()


# Example hook metadata for configuration files
WELCOME_HOOK_METADATA = {
    "name": "welcome",
    "description": "Sends welcome messages to new users",
    "events": ["session:start"],
    "priority": 100,
    "tags": ["greeting", "user-experience"]
}

COMMAND_LOGGER_HOOK_METADATA = {
    "name": "command-logger",
    "description": "Logs all commands for analysis",
    "events": ["command"],
    "priority": -500,
    "tags": ["logging", "analytics"]
}

SESSION_MEMORY_HOOK_METADATA = {
    "name": "session-memory",
    "description": "Saves session context to memory files",
    "events": ["session:end"],
    "priority": 200,
    "tags": ["memory", "persistence"]
}

RATE_LIMIT_HOOK_METADATA = {
    "name": "rate-limit",
    "description": "Implements rate limiting for users",
    "events": ["command"],
    "priority": 300,
    "tags": ["security", "rate-limiting"]
}

HEALTH_CHECK_HOOK_METADATA = {
    "name": "health-check",
    "description": "Performs system health checks",
    "events": ["health:check"],
    "priority": -1000,
    "tags": ["monitoring", "health"]
}