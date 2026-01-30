"""
Command Logger Hook Example

Demonstrates how to create hooks for logging and analytics.
"""

import json
from typing import Any, Dict, List
from datetime import datetime
from collections import defaultdict, Counter

from ..types import HookEvent, HookResult


class CommandLoggerHook:
    """Advanced command logging hook with analytics"""
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.command_history = []
        self.user_stats = defaultdict(lambda: {
            'commands_count': 0,
            'first_seen': None,
            'last_seen': None,
            'favorite_commands': Counter(),
            'total_sessions': 0
        })
        self.command_stats = Counter()
        self.hourly_activity = defaultdict(int)
        self.session_data = {}
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Log commands and update analytics"""
        try:
            if event.type.value == "command":
                return await self._log_command(event)
            elif event.type.value == "session":
                return await self._log_session_event(event)
            elif event.type.value == "message":
                return await self._log_message(event)
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )
    
    async def _log_command(self, event: HookEvent) -> HookResult:
        """Log command execution"""
        command = event.data.get('command', '')
        args = event.data.get('args', [])
        user_id = event.context.user_id
        session_key = event.session_key
        timestamp = event.timestamp
        
        # Create command record
        command_record = {
            'timestamp': timestamp.isoformat(),
            'command': command,
            'args': args,
            'user_id': user_id,
            'session_key': session_key,
            'channel_id': event.context.channel_id,
            'success': event.data.get('success', True),
            'duration': event.data.get('duration', 0),
            'error': event.data.get('error')
        }
        
        # Add to history
        self.command_history.append(command_record)
        
        # Trim history if needed
        if len(self.command_history) > self.max_history:
            self.command_history = self.command_history[-self.max_history:]
        
        # Update statistics
        if user_id:
            self._update_user_stats(user_id, command, timestamp)
        
        self.command_stats[command] += 1
        self.hourly_activity[timestamp.hour] += 1
        
        return HookResult(
            success=True,
            data={
                'command_logged': True,
                'total_commands': len(self.command_history)
            }
        )
    
    async def _log_session_event(self, event: HookEvent) -> HookResult:
        """Log session events"""
        user_id = event.context.user_id
        session_key = event.session_key
        timestamp = event.timestamp
        
        if event.action == "start":
            # Initialize session data
            if user_id:
                self.user_stats[user_id]['total_sessions'] += 1
                if not self.user_stats[user_id]['first_seen']:
                    self.user_stats[user_id]['first_seen'] = timestamp.isoformat()
                self.user_stats[user_id]['last_seen'] = timestamp.isoformat()
            
            self.session_data[session_key] = {
                'start_time': timestamp.isoformat(),
                'user_id': user_id,
                'commands_count': 0,
                'messages_count': 0
            }
            
        elif event.action == "end":
            # Finalize session data
            if session_key in self.session_data:
                session = self.session_data[session_key]
                session['end_time'] = timestamp.isoformat()
                
                # Calculate session duration
                start_time = datetime.fromisoformat(session['start_time'])
                duration = (timestamp - start_time).total_seconds()
                session['duration'] = duration
        
        return HookResult(success=True)
    
    async def _log_message(self, event: HookEvent) -> HookResult:
        """Log messages for context"""
        user_id = event.context.user_id
        session_key = event.session_key
        
        # Update session message count
        if session_key in self.session_data:
            self.session_data[session_key]['messages_count'] += 1
        
        # Update user message count
        if user_id:
            # This would require storing message counts in user stats
            pass
        
        return HookResult(success=True)
    
    def _update_user_stats(self, user_id: str, command: str, timestamp: datetime) -> None:
        """Update user statistics"""
        stats = self.user_stats[user_id]
        
        stats['commands_count'] += 1
        stats['favorite_commands'][command] += 1
        
        if not stats['first_seen']:
            stats['first_seen'] = timestamp.isoformat()
        stats['last_seen'] = timestamp.isoformat()
    
    def get_command_analytics(self) -> Dict[str, Any]:
        """Get comprehensive command analytics"""
        if not self.command_history:
            return {
                'total_commands': 0,
                'unique_users': 0,
                'unique_commands': 0,
                'message': 'No commands logged yet'
            }
        
        # Calculate overall statistics
        total_commands = len(self.command_history)
        unique_users = len(set(cmd['user_id'] for cmd in self.command_history if cmd['user_id']))
        unique_commands = len(self.command_stats)
        
        # Calculate success rate
        successful_commands = sum(1 for cmd in self.command_history if cmd.get('success', True))
        success_rate = successful_commands / total_commands if total_commands > 0 else 0
        
        # Get top commands
        top_commands = self.command_stats.most_common(10)
        
        # Calculate hourly distribution
        hourly_distribution = dict(self.hourly_activity)
        
        # Get most active users
        user_activity = [
            (user_id, stats['commands_count']) 
            for user_id, stats in self.user_stats.items()
        ]
        most_active_users = sorted(user_activity, key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_commands': total_commands,
            'unique_users': unique_users,
            'unique_commands': unique_commands,
            'success_rate': round(success_rate, 3),
            'top_commands': top_commands,
            'most_active_users': most_active_users,
            'hourly_distribution': hourly_distribution,
            'average_commands_per_user': round(total_commands / unique_users, 2) if unique_users > 0 else 0,
            'peak_hour': max(self.hourly_activity.items(), key=lambda x: x[1])[0] if self.hourly_activity else None
        }
    
    def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics for specific user"""
        if user_id not in self.user_stats:
            return {'error': 'User not found'}
        
        stats = self.user_stats[user_id]
        user_commands = [cmd for cmd in self.command_history if cmd['user_id'] == user_id]
        
        # Calculate user-specific metrics
        successful_commands = sum(1 for cmd in user_commands if cmd.get('success', True))
        success_rate = successful_commands / len(user_commands) if user_commands else 0
        
        # Get user sessions
        user_sessions = [
            session for session in self.session_data.values() 
            if session['user_id'] == user_id
        ]
        
        total_session_time = sum(session.get('duration', 0) for session in user_sessions)
        average_session_time = total_session_time / len(user_sessions) if user_sessions else 0
        
        return {
            'user_id': user_id,
            'total_commands': stats['commands_count'],
            'success_rate': round(success_rate, 3),
            'favorite_commands': stats['favorite_commands'].most_common(5),
            'total_sessions': stats['total_sessions'],
            'first_seen': stats['first_seen'],
            'last_seen': stats['last_seen'],
            'total_session_time': round(total_session_time, 2),
            'average_session_time': round(average_session_time, 2),
            'commands_per_session': round(stats['commands_count'] / stats['total_sessions'], 2) if stats['total_sessions'] > 0 else 0
        }
    
    def export_analytics(self, format: str = 'json') -> str:
        """Export analytics data"""
        data = {
            'generated_at': datetime.now().isoformat(),
            'command_analytics': self.get_command_analytics(),
            'user_analytics': {
                user_id: self.get_user_analytics(user_id)
                for user_id in self.user_stats.keys()
            },
            'raw_data': {
                'command_history': self.command_history[-1000:],  # Last 1000 commands
                'session_data': list(self.session_data.values())
            }
        }
        
        if format.lower() == 'json':
            return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def clear_analytics(self) -> None:
        """Clear all analytics data"""
        self.command_history.clear()
        self.user_stats.clear()
        self.command_stats.clear()
        self.hourly_activity.clear()
        self.session_data.clear()


class ErrorTrackerHook:
    """Hook for tracking and analyzing errors"""
    
    def __init__(self):
        self.error_log = []
        self.error_counts = Counter()
        self.error_by_user = defaultdict(Counter)
        self.error_by_hour = defaultdict(int)
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Track errors"""
        try:
            if event.type.value == "error" or event.data.get('error'):
                error_info = {
                    'timestamp': event.timestamp.isoformat(),
                    'error_type': event.data.get('error_type', 'unknown'),
                    'error_message': event.data.get('error_message', ''),
                    'user_id': event.context.user_id,
                    'session_key': event.session_key,
                    'context': event.data.get('context', {}),
                    'stack_trace': event.data.get('stack_trace', '')
                }
                
                self.error_log.append(error_info)
                self.error_counts[error_info['error_type']] += 1
                
                if error_info['user_id']:
                    self.error_by_user[error_info['user_id']][error_info['error_type']] += 1
                
                self.error_by_hour[event.timestamp.hour] += 1
                
                return HookResult(
                    success=True,
                    data={'error_tracked': True}
                )
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )
    
    def get_error_analytics(self) -> Dict[str, Any]:
        """Get error analytics"""
        if not self.error_log:
            return {'total_errors': 0}
        
        return {
            'total_errors': len(self.error_log),
            'error_types': dict(self.error_counts.most_common()),
            'most_problematic_users': [
                (user_id, sum(errors.values()))
                for user_id, errors in self.error_by_user.items()
            ][-10:],  # Bottom 10 (users with most errors)
            'peak_error_hour': max(self.error_by_hour.items(), key=lambda x: x[1])[0] if self.error_by_hour else None,
            'recent_errors': self.error_log[-10:]  # Last 10 errors
        }


# Example hook instances
command_logger = CommandLoggerHook()
error_tracker = ErrorTrackerHook()