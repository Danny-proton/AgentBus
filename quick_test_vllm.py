#!/usr/bin/env python3
"""
简单的 vLLM 测试验证脚本
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

print("="*60)
print("vLLM 测试套件验证")
print("="*60)

# 测试 1: 检查文件存在
print("\n[1] 检查测试文件...")
required_files = [
    "tests/test_vllm_mock.py",
    "tests/test_vllm_integration.py",
    "tests/conftest.py",
    "mock_vllm_server.py",
]

all_exist = True
for file in required_files:
    file_path = project_root / file
    if file_path.exists():
        print(f"  [OK] {file}")
    else:
        print(f"  [FAIL] 缺少: {file}")
        all_exist = False

# 测试 2: 检查导入
print("\n[2] 检查模块导入...")
try:
    import tests.test_vllm_mock
    print("  [OK] test_vllm_mock 导入成功")
except Exception as e:
    print(f"  [FAIL] test_vllm_mock: {e}")
    all_exist = False

try:
    import tests.test_vllm_integration  
    print("  [OK] test_vllm_integration 导入成功")
except Exception as e:
    print(f"  [FAIL] test_vllm_integration: {e}")
    all_exist = False

try:
    import mock_vllm_server
    print("  [OK] mock_vllm_server 导入成功")
except Exception as e:
    print(f"  [FAIL] mock_vllm_server: {e}")
    all_exist = False

# 测试 3: 检查 fixtures
print("\n[3] 检查 pytest fixtures...")
try:
    from tests.conftest import mock_vllm_server, vllm_base_url, vllm_settings
    print("  [OK] vLLM fixtures 已定义")
except Exception as e:
    print(f"  [FAIL] fixtures: {e}")
    all_exist = False

# 总结
print("\n" + "="*60)
if all_exist:
    print("[SUCCESS] 所有检查通过!")
    print("\n使用方法:")
    print("  1. 启动 mock 服务器:")
    print("     python mock_vllm_server.py")
    print("\n  2. 在另一个终端运行测试:")
    print("     pytest tests/test_vllm_mock.py -v")
    print("     pytest tests/test_vllm_integration.py -v")
    print("\n  3. 或使用简单测试脚本:")
    print("     python test_mock_vllm.py")
else:
    print("[FAILED] 部分检查失败")

print("="*60)
