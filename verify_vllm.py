
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to sys.path
project_root = str(Path(__file__).parent.absolute())
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(Path(project_root) / ".env")

# Mock agentbus package for imports (as done in verify_glm.py)
import types
agentbus = types.ModuleType("agentbus")
sys.modules["agentbus"] = agentbus
import config.settings
agentbus_core = types.ModuleType("agentbus.core")
agentbus_core.settings = config.settings
sys.modules["agentbus.core"] = agentbus_core
setattr(agentbus, "core", agentbus_core)

# Import services
from services.multi_model_coordinator import MultiModelCoordinator, TaskRequest, TaskType, TaskPriority
from core.settings import settings

async def verify_vllm():
    # Set console encoding to UTF-8 for Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=== vLLM Integration Verification ===")
    
    # Reload settings more reliably
    os.environ["AGENTBUS_LOCAL_MODEL_ID"] = "qwen3_32B"
    os.environ["AGENTBUS_LOCAL_MODEL_BASE_URL"] = "http://127.0.0.1:8030/v1"
    os.environ["AGENTBUS_LOCAL_MODEL_API_KEY"] = "empty"
    
    from config.settings import ExtendedSettings
    current_settings = ExtendedSettings()
    
    print(f"Loaded Settings:")
    print(f" - Local Model ID: {current_settings.local_model_id}")
    print(f" - Base URL: {current_settings.local_model_base_url}")
    print(f" - API Key: {current_settings.local_model_api_key}")
    
    print("\nInitializing MultiModelCoordinator...")
    coordinator = MultiModelCoordinator()
    await coordinator.initialize()
    
    print("\nChecking registered models...")
    models = coordinator.get_available_models()
    local_model_id = getattr(current_settings, 'local_model_id', 'qwen3_32B')
    vllm_model = next((m for m in models if m.model_id == local_model_id), None)
    
    if vllm_model:
        print(f"OK: Model '{vllm_model.model_id}' is registered.")
        print(f" - Provider: {vllm_model.provider}")
        print(f" - Base URL: {vllm_model.base_url}")
    else:
        print(f"Error: Model '{local_model_id}' not found in registered models.")
        print(f"Available models: {[m.model_id for m in models]}")
        return

    print("\nAttempting to submit a test task to local model...")
    task_request = TaskRequest(
        task_id="test_vllm",
        task_type=TaskType.TEXT_GENERATION,
        content="你好，请介绍一下你自己。",
        preferred_models=[vllm_model.model_id],
        required_capabilities=[TaskType.TEXT_GENERATION] # Match model's capabilities
    )
    
    try:
        task_id = await coordinator.submit_task(task_request)
        print(f"Task submitted with ID: {task_id}")
        print("Waiting for response (expecting connection error if vLLM is not running)...")
        
        for _ in range(5):
            result = await coordinator.get_task_result(task_id)
            if result:
                if result.status.name == "COMPLETED":
                    print(f"\nTask Completed!")
                    print(f"Response: {result.final_content}")
                    return
                elif result.status.name == "FAILED":
                    print(f"\nTask Failed as expected (or actual failure):")
                    print(f"Error: {result.error}")
                    if "Connection error" in result.error or "ConnectError" in result.error or "127.0.0.1" in result.error:
                        print("OK-pass: The coordinator attempted to connect to the local vLLM endpoint.")
                    return
            await asyncio.sleep(1)
            print(".", end="", flush=True)
            
    except Exception as e:
        print(f"❌ Unexpected error during task submission: {e}")

if __name__ == "__main__":
    asyncio.run(verify_vllm())
