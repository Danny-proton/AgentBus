#!/usr/bin/env python3
"""
AgentBus Hook System Demo

Demonstrates the features and usage of the AgentBus hook system.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Add the workspace to the path
sys.path.insert(0, str(Path(__file__).parent))

from agentbus.hooks import (
    initialize_system, get_system, shutdown_system,
    HookEventType, HookExecutionContext, trigger_command,
    trigger_session_event, trigger_error_event,
    get_system_info, create_utility_hooks,
    HookPriority, HookConfig
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def demo_basic_functionality():
    """Demonstrate basic hook system functionality"""
    logger.info("=== Basic Hook System Demo ===")
    
    # Initialize the system
    config = HookConfig(
        debug=True,
        enabled=True,
        load_bundled_hooks=True,
        load_workspace_hooks=True
    )
    
    system = await initialize_system(config, "/tmp/agentbus_demo")
    
    try:
        # Create a simple hook
        async def my_custom_hook(event):
            logger.info(f"🎯 Custom hook triggered: {event.type.value}:{event.action}")
            return {"success": True, "message": "Custom hook executed"}
        
        # Register the hook
        system.register_hook(
            event_key="command:*",
            handler=my_custom_hook,
            priority=HookPriority.HIGH
        )
        
        # Trigger a command event
        logger.info("Triggering command event...")
        results = await trigger_command(
            command="analyze",
            session_key="demo_session_123",
            context=HookExecutionContext(
                session_key="demo_session_123",
                agent_id="demo_agent",
                channel_id="demo_channel",
                user_id="demo_user"
            ),
            args=["data.json"],
            success=True,
            duration=1.5
        )
        
        logger.info(f"Command event results: {len(results)} hooks executed")
        for result in results:
            logger.info(f"  - Success: {result.success}")
        
        # Get system status
        status = system.get_status()
        logger.info(f"System status: {status['status']}")
        
    finally:
        await shutdown_system()


async def demo_event_types():
    """Demonstrate different event types"""
    logger.info("=== Event Types Demo ===")
    
    system = await initialize_system()
    
    try:
        # Demo different event types
        events_to_demo = [
            ("command", "help", {"command": "help", "args": []}),
            ("session", "start", {"session_type": "chat"}),
            ("session", "end", {"duration": 120, "events_count": 15}),
            ("error", "validation", {"error_type": "validation", "message": "Invalid input"}),
            ("message", "received", {"message_type": "text", "content": "Hello!"}),
            ("health", "check", {"check_type": "system"})
        ]
        
        for event_type, action, data in events_to_demo:
            logger.info(f"Triggering {event_type}:{action}...")
            
            event_type_enum = HookEventType(event_type)
            
            results = await trigger_session_event(
                action=action,
                session_key="demo_session_456",
                context=HookExecutionContext(
                    session_key="demo_session_456",
                    agent_id="demo_agent",
                    channel_id="demo_channel",
                    user_id="demo_user"
                ),
                **data
            )
            
            logger.info(f"  Executed {len(results)} hooks")
        
    finally:
        await shutdown_system()


async def demo_utility_hooks():
    """Demonstrate built-in utility hooks"""
    logger.info("=== Utility Hooks Demo ===")
    
    system = await initialize_system()
    
    try:
        # Create utility hooks
        utility_hooks = create_utility_hooks()
        
        # Register some utility hooks
        for name, hook in utility_hooks.items():
            if name in ['echo', 'time', 'health']:
                system.register_hook(
                    event_key=f"command:{name}",
                    handler=hook,
                    priority=HookPriority.NORMAL
                )
        
        # Test utility hooks
        test_commands = [
            ("echo", {"message": "Hello, AgentBus!"}),
            ("time", {}),
            ("health", {}),
            ("calc", {"expression": "2 + 3 * 4"}),
            ("hash", {"text": "secret_password", "algorithm": "md5"})
        ]
        
        for command, data in test_commands:
            logger.info(f"Testing {command} command...")
            
            results = await trigger_command(
                command=command,
                session_key="utility_demo",
                context=HookExecutionContext(
                    session_key="utility_demo",
                    agent_id="utility_agent"
                ),
                **data
            )
            
            for result in results:
                if result.messages:
                    logger.info(f"  Response: {result.messages[0]}")
                logger.info(f"  Success: {result.success}")
        
    finally:
        await shutdown_system()


async def demo_performance_monitoring():
    """Demonstrate performance monitoring features"""
    logger.info("=== Performance Monitoring Demo ===")
    
    system = await initialize_system()
    
    try:
        # Create a slow hook for testing
        async def slow_hook(event):
            logger.info("⏳ Simulating slow operation...")
            await asyncio.sleep(0.1)  # Simulate slow operation
            return {"success": True, "duration": 0.1}
        
        # Register slow hook with high priority
        system.register_hook(
            event_key="command:slow",
            handler=slow_hook,
            priority=HookPriority.HIGH
        )
        
        # Create a fast hook
        async def fast_hook(event):
            logger.info("⚡ Fast operation")
            return {"success": True, "duration": 0.001}
        
        # Register fast hook with low priority
        system.register_hook(
            event_key="command:fast",
            handler=fast_hook,
            priority=HookPriority.LOW
        )
        
        # Test performance
        commands = ["slow", "fast"]
        
        for command in commands:
            logger.info(f"Testing {command} command...")
            
            start_time = asyncio.get_event_loop().time()
            
            results = await trigger_command(
                command=command,
                session_key="perf_demo",
                context=HookExecutionContext(session_key="perf_demo")
            )
            
            end_time = asyncio.get_event_loop().time()
            total_time = end_time - start_time
            
            logger.info(f"  Total time: {total_time:.3f}s")
            logger.info(f"  Hooks executed: {len(results)}")
            
            for result in results:
                logger.info(f"    Hook execution time: {result.execution_time:.3f}s")
        
        # Get performance statistics
        system_info = get_system_info()
        stats = system_info.get('statistics', {})
        
        logger.info("Performance Statistics:")
        logger.info(f"  Registry stats: {stats.get('registry', {})}")
        logger.info(f"  Engine stats: {stats.get('engine', {})}")
        
    finally:
        await shutdown_system()


async def demo_error_handling():
    """Demonstrate error handling features"""
    logger.info("=== Error Handling Demo ===")
    
    system = await initialize_system()
    
    try:
        # Create a failing hook
        async def failing_hook(event):
            logger.info("❌ This hook will fail...")
            raise Exception("Intentional failure for demo")
        
        # Create a recovery hook
        async def recovery_hook(event):
            logger.info("🛠️ Recovery hook handling error...")
            return {"success": True, "recovered": True}
        
        # Register hooks
        system.register_hook(
            event_key="command:failing",
            handler=failing_hook,
            priority=HookPriority.HIGH
        )
        
        system.register_hook(
            event_key="error",
            handler=recovery_hook,
            priority=HookPriority.NORMAL
        )
        
        # Trigger failing command
        logger.info("Triggering command that will fail...")
        
        results = await trigger_command(
            command="failing",
            session_key="error_demo",
            context=HookExecutionContext(session_key="error_demo")
        )
        
        logger.info(f"Results: {len(results)} hooks executed")
        
        for result in results:
            logger.info(f"  Success: {result.success}")
            if not result.success:
                logger.info(f"  Error: {result.error}")
        
        # Trigger error event directly
        logger.info("Triggering error event...")
        
        error_results = await trigger_error_event(
            error_type="demo_error",
            error_message="This is a demo error",
            session_key="error_demo"
        )
        
        logger.info(f"Error event results: {len(error_results)} hooks executed")
        
    finally:
        await shutdown_system()


async def demo_configuration():
    """Demonstrate configuration management"""
    logger.info("=== Configuration Demo ===")
    
    try:
        from agentbus.hooks.config import get_config_manager, HookConfig
        
        # Get config manager
        config_manager = get_config_manager()
        
        # Create custom configuration
        custom_config = HookConfig(
            enabled=True,
            debug=True,
            load_bundled_hooks=True,
            load_workspace_hooks=True,
            execution_timeout=60,
            max_concurrent=5
        )
        
        # Save configuration
        success = config_manager.save_config(custom_config)
        logger.info(f"Configuration saved: {success}")
        
        # Get configuration summary
        summary = config_manager.get_config_summary()
        logger.info("Configuration Summary:")
        for key, value in summary.items():
            logger.info(f"  {key}: {value}")
        
        # Update hook configuration
        update_success = config_manager.update_hook_config("session-memory", {
            "enabled": True,
            "priority": 200,
            "timeout": 30
        })
        logger.info(f"Hook config updated: {update_success}")
        
    finally:
        await shutdown_system()


async def demo_health_monitoring():
    """Demonstrate health monitoring"""
    logger.info("=== Health Monitoring Demo ===")
    
    system = await initialize_system()
    
    try:
        # Create a health check hook
        async def health_check_hook(event):
            import psutil
            import time
            
            health_data = {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "timestamp": time.time()
            }
            
            logger.info(f"🏥 Health check: CPU {health_data['cpu_percent']}%, "
                       f"Memory {health_data['memory_percent']}%, "
                       f"Disk {health_data['disk_percent']}%")
            
            return {
                "success": True,
                "health_data": health_data,
                "status": "healthy" if health_data['memory_percent'] < 80 else "degraded"
            }
        
        # Register health check hook
        system.register_hook(
            event_key="health:check",
            handler=health_check_hook,
            priority=HookPriority.LOW
        )
        
        # Trigger health check
        logger.info("Triggering health check...")
        
        results = await trigger_session_event(
            action="check",
            session_key="health_demo",
            context=HookExecutionContext(session_key="health_demo"),
            check_type="system"
        )
        
        for result in results:
            if result.success and result.data:
                health_data = result.data.get('health_data', {})
                status = result.data.get('status', 'unknown')
                logger.info(f"Health status: {status}")
                logger.info(f"Health data: {health_data}")
        
        # Get system health
        system_info = get_system_info()
        logger.info(f"Overall system health: {system_info.get('metrics', {}).get('health', {})}")
        
    finally:
        await shutdown_system()


async def main():
    """Run all demos"""
    demos = [
        ("Basic Functionality", demo_basic_functionality),
        ("Event Types", demo_event_types),
        ("Utility Hooks", demo_utility_hooks),
        ("Performance Monitoring", demo_performance_monitoring),
        ("Error Handling", demo_error_handling),
        ("Configuration", demo_configuration),
        ("Health Monitoring", demo_health_monitoring)
    ]
    
    for demo_name, demo_func in demos:
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running {demo_name} Demo")
            logger.info(f"{'='*50}")
            
            await demo_func()
            
            logger.info(f"✅ {demo_name} Demo completed successfully")
            
        except Exception as e:
            logger.error(f"❌ {demo_name} Demo failed: {e}")
        
        # Brief pause between demos
        await asyncio.sleep(1)
    
    logger.info(f"\n{'='*50}")
    logger.info("🎉 All demos completed!")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())