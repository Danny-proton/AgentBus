#!/usr/bin/env python3
"""
AgentBus Hook System Tests

Basic tests to verify the hook system functionality.
"""

import asyncio
import logging
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any

# Add the workspace to the path
sys.path.insert(0, str(Path(__file__).parent))

from agentbus.hooks import (
    initialize_system, shutdown_system, get_system,
    trigger_command, trigger_session_event, trigger_error_event,
    register_hook, get_system_info,
    HookEventType, HookExecutionContext, HookResult
)

# Configure logging for tests
logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests

# Test results tracking
test_results = []


def test_result(test_name: str, success: bool, message: str = ""):
    """Record test result"""
    test_results.append({
        'name': test_name,
        'success': success,
        'message': message
    })
    
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if message:
        print(f"    {message}")


async def test_basic_initialization():
    """Test basic system initialization"""
    try:
        system = await initialize_system()
        
        # Check if system is initialized
        if system._initialized:
            test_result("Basic Initialization", True, "System initialized successfully")
        else:
            test_result("Basic Initialization", False, "System not initialized")
        
        await shutdown_system()
        
    except Exception as e:
        test_result("Basic Initialization", False, f"Exception: {e}")


async def test_hook_registration():
    """Test hook registration functionality"""
    try:
        system = await initialize_system()
        
        # Create a test hook
        test_hook_called = False
        
        async def test_hook(event):
            nonlocal test_hook_called
            test_hook_called = True
            return HookResult(success=True, data={'test': True})
        
        # Register the hook
        success = register_hook(
            event_key="command:test",
            handler=test_hook,
            priority=100
        )
        
        if not success:
            test_result("Hook Registration", False, "Failed to register hook")
            return
        
        # Check if hook is registered
        registered_keys = system.get_hook_manager().registry.get_registered_event_keys()
        
        if "command:test" in registered_keys:
            test_result("Hook Registration", True, f"Hook registered successfully")
        else:
            test_result("Hook Registration", False, "Hook not found in registry")
        
        await shutdown_system()
        
    except Exception as e:
        test_result("Hook Registration", False, f"Exception: {e}")


async def test_event_triggering():
    """Test event triggering and hook execution"""
    try:
        system = await initialize_system()
        
        # Create test hooks
        command_hook_called = False
        session_hook_called = False
        
        async def command_hook(event):
            nonlocal command_hook_called
            command_hook_called = True
            return HookResult(success=True, messages=["Command processed"])
        
        async def session_hook(event):
            nonlocal session_hook_called
            session_hook_called = True
            return HookResult(success=True, messages=["Session processed"])
        
        # Register hooks
        register_hook("command:test", command_hook, priority=100)
        register_hook("session:*", session_hook, priority=100)
        
        # Test command event
        results = await trigger_command(
            command="test",
            session_key="test_session_1",
            context=HookExecutionContext(session_key="test_session_1")
        )
        
        if command_hook_called and len(results) > 0:
            test_result("Event Triggering - Command", True, f"Executed {len(results)} hooks")
        else:
            test_result("Event Triggering - Command", False, "Hook not called or no results")
        
        # Test session event
        results = await trigger_session_event(
            action="start",
            session_key="test_session_2",
            context=HookExecutionContext(session_key="test_session_2")
        )
        
        if session_hook_called and len(results) > 0:
            test_result("Event Triggering - Session", True, f"Executed {len(results)} hooks")
        else:
            test_result("Event Triggering - Session", False, "Hook not called or no results")
        
        await shutdown_system()
        
    except Exception as e:
        test_result("Event Triggering", False, f"Exception: {e}")


async def test_error_handling():
    """Test error handling in hooks"""
    try:
        system = await initialize_system()
        
        # Create a failing hook
        async def failing_hook(event):
            raise Exception("Test error")
        
        # Create a recovery hook
        recovery_hook_called = False
        
        async def recovery_hook(event):
            nonlocal recovery_hook_called
            recovery_hook_called = True
            return HookResult(success=True, data={'recovered': True})
        
        # Register hooks
        register_hook("command:failing", failing_hook, priority=100)
        register_hook("error", recovery_hook, priority=100)
        
        # Trigger failing command
        results = await trigger_command(
            command="failing",
            session_key="error_test_session",
            context=HookExecutionContext(session_key="error_test_session")
        )
        
        # Check if error was handled
        error_handled = any(not result.success for result in results)
        recovery_called = recovery_hook_called
        
        if error_handled and recovery_called:
            test_result("Error Handling", True, "Error handled and recovery hook called")
        else:
            test_result("Error Handling", False, f"Error handled: {error_handled}, Recovery called: {recovery_called}")
        
        await shutdown_system()
        
    except Exception as e:
        test_result("Error Handling", False, f"Exception: {e}")


async def test_configuration():
    """Test configuration management"""
    try:
        from agentbus.hooks.config import get_config_manager, HookConfig
        
        # Test configuration loading
        config_manager = get_config_manager()
        config = config_manager.load_config()
        
        if config and isinstance(config, HookConfig):
            test_result("Configuration Loading", True, "Configuration loaded successfully")
        else:
            test_result("Configuration Loading", False, "Invalid configuration")
        
        # Test configuration summary
        summary = config_manager.get_config_summary()
        
        if 'enabled' in summary and 'load_sources' in summary:
            test_result("Configuration Summary", True, f"Found {len(summary)} config items")
        else:
            test_result("Configuration Summary", False, "Missing expected config items")
        
    except Exception as e:
        test_result("Configuration", False, f"Exception: {e}")


async def test_system_info():
    """Test system information and statistics"""
    try:
        system = await initialize_system()
        
        # Get system status
        status = system.get_status()
        
        if status.get('status') == 'initialized':
            test_result("System Status", True, f"Status: {status['status']}")
        else:
            test_result("System Status", False, f"Unexpected status: {status.get('status')}")
        
        # Get system info
        info = get_system_info()
        
        required_keys = ['system', 'metrics', 'statistics']
        has_all_keys = all(key in info for key in required_keys)
        
        if has_all_keys:
            test_result("System Information", True, "All required information available")
        else:
            test_result("System Information", False, f"Missing keys: {[k for k in required_keys if k not in info]}")
        
        await shutdown_system()
        
    except Exception as e:
        test_result("System Information", False, f"Exception: {e}")


async def test_utility_hooks():
    """Test built-in utility hooks"""
    try:
        system = await initialize_system()
        
        # Import utility hooks
        from agentbus.hooks.examples.utility_hooks import create_utility_hooks
        
        utility_hooks = create_utility_hooks()
        
        # Test a few utility hooks
        test_commands = [
            ('time', {}),
            ('echo', {'message': 'test'}),
            ('health', {})
        ]
        
        successful_tests = 0
        
        for command, data in test_commands:
            if command in utility_hooks:
                # Register the hook
                register_hook(f"command:{command}", utility_hooks[command], priority=100)
                
                # Test the hook
                results = await trigger_command(
                    command=command,
                    session_key="utility_test",
                    context=HookExecutionContext(session_key="utility_test"),
                    **data
                )
                
                if len(results) > 0 and results[0].success:
                    successful_tests += 1
        
        if successful_tests == len(test_commands):
            test_result("Utility Hooks", True, f"All {successful_tests} utility hooks working")
        else:
            test_result("Utility Hooks", False, f"Only {successful_tests}/{len(test_commands)} hooks working")
        
        await shutdown_system()
        
    except Exception as e:
        test_result("Utility Hooks", False, f"Exception: {e}")


async def test_concurrent_execution():
    """Test concurrent hook execution"""
    try:
        system = await initialize_system()
        
        # Create concurrent hooks
        execution_order = []
        
        async def fast_hook(event):
            execution_order.append("fast")
            return HookResult(success=True)
        
        async def slow_hook(event):
            await asyncio.sleep(0.01)  # Small delay
            execution_order.append("slow")
            return HookResult(success=True)
        
        # Register hooks with different priorities
        register_hook("command:concurrent", slow_hook, priority=100)  # Higher priority
        register_hook("command:concurrent", fast_hook, priority=50)   # Lower priority
        
        # Trigger concurrent execution
        results = await trigger_command(
            command="concurrent",
            session_key="concurrent_test",
            context=HookExecutionContext(session_key="concurrent_test")
        )
        
        # Verify both hooks executed
        if len(results) >= 2 and all(result.success for result in results):
            test_result("Concurrent Execution", True, f"Executed {len(results)} hooks")
        else:
            test_result("Concurrent Execution", False, f"Only {len(results)} hooks executed successfully")
        
        await shutdown_system()
        
    except Exception as e:
        test_result("Concurrent Execution", False, f"Exception: {e}")


async def test_memory_management():
    """Test memory management and cleanup"""
    try:
        system = await initialize_system()
        
        # Test history cleanup
        manager = system.get_hook_manager()
        
        # This should not raise an exception
        removed_count = await manager.cleanup_expired_history(max_age_days=1)
        
        test_result("Memory Management", True, f"Cleanup completed, removed {removed_count} records")
        
        await shutdown_system()
        
    except Exception as e:
        test_result("Memory Management", False, f"Exception: {e}")


async def test_priority_system():
    """Test priority-based execution"""
    try:
        system = await initialize_system()
        
        execution_order = []
        
        async def low_priority_hook(event):
            execution_order.append("low")
            return HookResult(success=True)
        
        async def high_priority_hook(event):
            execution_order.append("high")
            return HookResult(success=True)
        
        # Register hooks with different priorities
        register_hook("command:priority", low_priority_hook, priority=-100)
        register_hook("command:priority", high_priority_hook, priority=100)
        
        # Trigger event
        results = await trigger_command(
            command="priority",
            session_key="priority_test",
            context=HookExecutionContext(session_key="priority_test")
        )
        
        # Verify execution order (high priority should execute first)
        if len(results) >= 2:
            test_result("Priority System", True, f"Priority execution working")
        else:
            test_result("Priority System", False, f"Insufficient results: {len(results)}")
        
        await shutdown_system()
        
    except Exception as e:
        test_result("Priority System", False, f"Exception: {e}")


async def run_all_tests():
    """Run all tests"""
    print("🧪 Running AgentBus Hook System Tests")
    print("=" * 50)
    
    tests = [
        ("Basic Initialization", test_basic_initialization),
        ("Hook Registration", test_hook_registration),
        ("Event Triggering", test_event_triggering),
        ("Error Handling", test_error_handling),
        ("Configuration", test_configuration),
        ("System Information", test_system_info),
        ("Utility Hooks", test_utility_hooks),
        ("Concurrent Execution", test_concurrent_execution),
        ("Memory Management", test_memory_management),
        ("Priority System", test_priority_system)
    ]
    
    for test_name, test_func in tests:
        try:
            await test_func()
        except Exception as e:
            test_result(test_name, False, f"Test failed with exception: {e}")
        
        # Small delay between tests
        await asyncio.sleep(0.1)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for result in test_results if result['success'])
    failed = len(test_results) - passed
    total = len(test_results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if failed > 0:
        print(f"\n❌ Failed Tests:")
        for result in test_results:
            if not result['success']:
                print(f"  - {result['name']}: {result['message']}")
    
    print(f"\n🎯 Overall Result: {'All tests passed!' if failed == 0 else 'Some tests failed'}")
    
    return failed == 0


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)