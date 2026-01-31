
from config.config_types import ConfigSnapshot
import pydantic
from typing import Dict, Any

print(f"Pydantic Version: {pydantic.__version__}")

try:
    snapshot = ConfigSnapshot(
        id="test",
        timestamp=0.0,
        environment="development",
        profile="default",
        data={},
        checksum="abcd"
    )
    print("Instance created successfully")
    
    if hasattr(snapshot, "model_dump_json"):
        print("model_dump_json exists")
    else:
        print("model_dump_json MISSING")
        
    if hasattr(snapshot, "json"):
        print("json() exists (v1 style)")
    else:
        print("json() MISSING")
        
except Exception as e:
    print(f"Error: {e}")
