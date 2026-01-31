
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to sys.path
project_root = str(Path(__file__).parent.absolute())
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(Path(project_root) / ".env")

# Create a mock agentbus package in sys.modules to redirect imports
# because the code uses 'from agentbus.core.settings' but the files are in 'd:\gitAgentBus\AgentBus\config'
# This project structure seems to have shifted 'agentbus' content to root.

import types

# Create 'agentbus' module
agentbus = types.ModuleType("agentbus")
sys.modules["agentbus"] = agentbus

# Create 'agentbus.core' module and map 'settings' to 'config.settings'
# The original code expects 'agentbus.core.settings' but the file is 'config/settings.py'
import config.settings
agentbus_core = types.ModuleType("agentbus.core")
agentbus_core.settings = config.settings
sys.modules["agentbus.core"] = agentbus_core
setattr(agentbus, "core", agentbus_core)

# Map 'agentbus.services' to 'services'
import services
sys.modules["agentbus.services"] = services
setattr(agentbus, "services", services)

# Map specific services that are imported in cli.py
import services.hitl
import services.knowledge_bus
import services.multi_model_coordinator
import services.stream_response
sys.modules["agentbus.services.hitl"] = services.hitl
sys.modules["agentbus.services.knowledge_bus"] = services.knowledge_bus
sys.modules["agentbus.services.multi_model_coordinator"] = services.multi_model_coordinator
sys.modules["agentbus.services.stream_response"] = services.stream_response


# Map 'agentbus.plugins'
# agentbus.plugins.manager -> plugins.manager (Assuming plugins folder exists in root)
# Let's check if plugins folder exists, list_dir showed it.
import plugins.manager
agentbus_plugins = types.ModuleType("agentbus.plugins")
agentbus_plugins.manager = plugins.manager
sys.modules["agentbus.plugins"] = agentbus_plugins
sys.modules["agentbus.plugins.manager"] = plugins.manager
setattr(agentbus, "plugins", agentbus_plugins)

# Map 'agentbus.channels'
import channels.manager
agentbus_channels = types.ModuleType("agentbus.channels")
agentbus_channels.manager = channels.manager
sys.modules["agentbus.channels"] = agentbus_channels
sys.modules["agentbus.channels.manager"] = channels.manager
setattr(agentbus, "channels", agentbus_channels)

# Now we can try running the CLI logic directly
import asyncio
from services.multi_model_coordinator import MultiModelCoordinator, TaskRequest, TaskType, TaskPriority

async def run_verification():
    print("Initializing Coordinator...")
    coordinator = MultiModelCoordinator()
    await coordinator.initialize()
    
    print("Available Models:")
    models = coordinator.get_available_models()
    for m in models:
        print(f" - {m.model_id}: {m.model_name} (Provider: {m.provider})")
        
    print("\nSubmitting Task to GLM-4.7...")
    task_request = TaskRequest(
        task_id="test_glm_47",
        task_type=TaskType.TEXT_GENERATION,
        content="作为一名营销专家，请为我的产品创作一个吸引人的口号。产品：智谱AI 开放平台",
        preferred_models=["glm-4-flash"],
        max_cost=1.0,
        required_capabilities=[TaskType.QUESTION_ANSWERING]
    )
    
    task_id = await coordinator.submit_task(task_request)
    print(f"Task Submitted: {task_id}")
    
    # Process it manually since the loop is in the background task in the service
    # We can just wait for the result if the loop is running, but let's check if we need to manually trigger.
    # The code: asyncio.create_task(self._task_processing_loop()) is called in initialize()
    
    print("Waiting for result...")
    for _ in range(20): # Wait up to 20 seconds
        result = await coordinator.get_task_result(task_id)
        if result and result.status.name == "COMPLETED":
            print("\nSUCCESS! Task Completed.")
            print(f"Content: {result.final_content}")
            print(f"Model Results: {[r.model_id for r in result.model_results]}")
            return
        elif result and result.status.name == "FAILED":
             print(f"\nFAILED! Error: {result.error}")
             return
        await asyncio.sleep(1)
        print(".", end="", flush=True)

    print("\nTimeout waiting for result.")

if __name__ == "__main__":
    asyncio.run(run_verification())
