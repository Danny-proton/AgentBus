"""
Simple Utility Hooks

Basic utility hooks for common functionality.
"""

import asyncio
import json
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime

from ..types import HookEvent, HookResult


class EchoHook:
    """Simple echo hook that returns the input"""
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Echo back the event data"""
        try:
            if event.type.value == "command" and event.action == "echo":
                message = event.data.get('message', '')
                
                return HookResult(
                    success=True,
                    messages=[f"Echo: {message}"],
                    data={'echoed': True}
                )
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )


class TimeHook:
    """Hook that provides current time information"""
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Provide time information"""
        try:
            if event.type.value == "command" and event.action == "time":
                now = datetime.now()
                
                time_info = {
                    'iso_format': now.isoformat(),
                    'timestamp': now.timestamp(),
                    'utc': now.utcnow().isoformat(),
                    'local_timezone': str(now.astimezone().tzinfo),
                    'weekday': now.strftime('%A'),
                    'formatted': now.strftime('%Y-%m-%d %H:%M:%S %Z')
                }
                
                return HookResult(
                    success=True,
                    messages=[f"Current time: {time_info['formatted']}"],
                    data={'time_info': time_info}
                )
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )


class HealthHook:
    """Basic health check hook"""
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Perform basic health check"""
        try:
            if event.type.value == "command" and event.action == "health":
                health_status = {
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'version': '1.0.0',
                    'checks': {
                        'database': 'ok',
                        'cache': 'ok',
                        'external_apis': 'ok'
                    }
                }
                
                return HookResult(
                    success=True,
                    messages=[f"System health: {health_status['status']}"],
                    data={'health': health_status}
                )
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )


class CalculatorHook:
    """Simple calculator hook for basic math operations"""
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Perform calculations"""
        try:
            if event.type.value == "command" and event.action == "calc":
                expression = event.data.get('expression', '')
                
                try:
                    # Simple safe evaluation (only numbers and basic operators)
                    if not all(c in '0123456789+-*/.() ' for c in expression):
                        raise ValueError("Invalid characters in expression")
                    
                    result = eval(expression)
                    
                    return HookResult(
                        success=True,
                        messages=[f"Result: {expression} = {result}"],
                        data={
                            'expression': expression,
                            'result': result
                        }
                    )
                    
                except Exception as calc_error:
                    return HookResult(
                        success=False,
                        error=f"Calculation error: {calc_error}"
                    )
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )


class HashHook:
    """Hook for generating hashes"""
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Generate hash of input"""
        try:
            if event.type.value == "command" and event.action == "hash":
                text = event.data.get('text', '')
                algorithm = event.data.get('algorithm', 'md5').lower()
                
                if not text:
                    return HookResult(
                        success=False,
                        error="No text provided for hashing"
                    )
                
                # Generate hash
                if algorithm == 'md5':
                    hash_obj = hashlib.md5(text.encode())
                elif algorithm == 'sha1':
                    hash_obj = hashlib.sha1(text.encode())
                elif algorithm == 'sha256':
                    hash_obj = hashlib.sha256(text.encode())
                else:
                    return HookResult(
                        success=False,
                        error=f"Unsupported algorithm: {algorithm}"
                    )
                
                hash_value = hash_obj.hexdigest()
                
                return HookResult(
                    success=True,
                    messages=[f"Hash ({algorithm}): {hash_value}"],
                    data={
                        'text': text,
                        'algorithm': algorithm,
                        'hash': hash_value
                    }
                )
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )


class JSONProcessorHook:
    """Hook for processing JSON data"""
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Process JSON data"""
        try:
            if event.type.value == "command" and event.action == "json":
                operation = event.data.get('operation', 'validate')
                json_text = event.data.get('json_text', '')
                
                if operation == 'validate':
                    try:
                        parsed = json.loads(json_text)
                        return HookResult(
                            success=True,
                            messages=[f"Valid JSON with {len(parsed)} keys"],
                            data={'parsed': parsed}
                        )
                    except json.JSONDecodeError as e:
                        return HookResult(
                            success=False,
                            error=f"Invalid JSON: {e}"
                        )
                
                elif operation == 'format':
                    try:
                        parsed = json.loads(json_text)
                        formatted = json.dumps(parsed, indent=2)
                        return HookResult(
                            success=True,
                            messages=["Formatted JSON:"],
                            data={'formatted': formatted}
                        )
                    except json.JSONDecodeError as e:
                        return HookResult(
                            success=False,
                            error=f"Invalid JSON: {e}"
                        )
                
                elif operation == 'minify':
                    try:
                        parsed = json.loads(json_text)
                        minified = json.dumps(parsed, separators=(',', ':'))
                        return HookResult(
                            success=True,
                            messages=[f"Minified JSON: {len(minified)} characters"],
                            data={'minified': minified}
                        )
                    except json.JSONDecodeError as e:
                        return HookResult(
                            success=False,
                            error=f"Invalid JSON: {e}"
                        )
                
                else:
                    return HookResult(
                        success=False,
                        error=f"Unknown operation: {operation}"
                    )
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )


class TextStatsHook:
    """Hook for analyzing text statistics"""
    
    async def __call__(self, event: HookEvent) -> HookResult:
        """Analyze text statistics"""
        try:
            if event.type.value == "command" and event.action == "stats":
                text = event.data.get('text', '')
                
                if not text:
                    return HookResult(
                        success=False,
                        error="No text provided for analysis"
                    )
                
                # Calculate statistics
                stats = {
                    'length': len(text),
                    'word_count': len(text.split()),
                    'line_count': len(text.split('\n')),
                    'char_count': len(text),
                    'char_count_no_spaces': len(text.replace(' ', '')),
                    'paragraph_count': len([p for p in text.split('\n\n') if p.strip()]),
                    'average_word_length': sum(len(word) for word in text.split()) / len(text.split()) if text.split() else 0,
                    'contains_digits': any(c.isdigit() for c in text),
                    'contains_uppercase': any(c.isupper() for c in text),
                    'contains_lowercase': any(c.islower() for c in text),
                    'contains_punctuation': any(c in '.,!?;:' for c in text)
                }
                
                # Generate summary message
                summary = (
                    f"Text Statistics:\n"
                    f"• Length: {stats['length']} characters\n"
                    f"• Words: {stats['word_count']}\n"
                    f"• Lines: {stats['line_count']}\n"
                    f"• Paragraphs: {stats['paragraph_count']}\n"
                    f"• Avg word length: {stats['average_word_length']:.1f} characters"
                )
                
                return HookResult(
                    success=True,
                    messages=[summary],
                    data={'stats': stats}
                )
            
            return HookResult(success=True)
            
        except Exception as e:
            return HookResult(
                success=False,
                error=str(e)
            )


# Create hook instances
echo_hook = EchoHook()
time_hook = TimeHook()
health_hook = HealthHook()
calculator_hook = CalculatorHook()
hash_hook = HashHook()
json_processor_hook = JSONProcessorHook()
text_stats_hook = TextStatsHook()


# Helper function to create utility hooks
def create_utility_hooks():
    """Create all utility hooks"""
    return {
        'echo': echo_hook,
        'time': time_hook,
        'health': health_hook,
        'calculator': calculator_hook,
        'hash': hash_hook,
        'json_processor': json_processor_hook,
        'text_stats': text_stats_hook
    }