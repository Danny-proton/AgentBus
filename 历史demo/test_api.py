#!/usr/bin/env python3
"""
AgentBus API Test
AgentBus API测试脚本

快速测试AgentBus的核心功能
"""

import asyncio
import aiohttp
import json
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agentbus.api.main import create_app
from agentbus.services.workspace import init_workspace


async def test_api():
    """测试API功能"""
    
    print("🧪 开始测试AgentBus API...")
    
    # 初始化工作空间
    print("📁 初始化工作空间...")
    workspace = await init_workspace("./test_workspace")
    
    # 创建测试应用
    print("🚀 创建测试应用...")
    app = create_app()
    
    # 启动测试服务器
    import uvicorn
    config = uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="error")
    server = uvicorn.Server(config)
    
    # 在后台启动服务器
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(1)  # 等待服务器启动
    
    try:
        # 测试HTTP客户端
        async with aiohttp.ClientSession() as session:
            
            # 测试根端点
            print("📋 测试根端点...")
            async with session.get("http://127.0.0.1:8001/") as resp:
                data = await resp.json()
                assert resp.status == 200
                assert "AgentBus" in data["message"]
                print("✅ 根端点测试通过")
            
            # 测试健康检查
            print("❤️ 测试健康检查...")
            async with session.get("http://127.0.0.1:8001/health") as resp:
                data = await resp.json()
                assert resp.status == 200
                assert data["status"] == "healthy"
                print("✅ 健康检查测试通过")
            
            # 测试API信息
            print("🔍 测试API信息...")
            async with session.get("http://127.0.0.1:8001/api/info") as resp:
                data = await resp.json()
                assert resp.status == 200
                assert "endpoints" in data
                print("✅ API信息测试通过")
            
            # 测试会话创建
            print("💬 测试会话创建...")
            session_data = {
                "workspace": "./test_workspace",
                "agent_id": "test_agent",
                "model": "gpt-4"
            }
            async with session.post("http://127.0.0.1:8001/api/sessions/", json=session_data) as resp:
                data = await resp.json()
                assert resp.status == 200
                assert "id" in data
                session_id = data["id"]
                print(f"✅ 会话创建测试通过 (ID: {session_id})")
            
            # 测试工具注册表
            print("🔧 测试工具注册表...")
            async with session.get("http://127.0.0.1:8001/api/tools/registry") as resp:
                data = await resp.json()
                assert resp.status == 200
                assert "tools" in data
                assert len(data["tools"]) > 0
                print(f"✅ 工具注册表测试通过 ({len(data['tools'])} 个工具)")
            
            # 测试配置获取
            print("⚙️ 测试配置获取...")
            async with session.get("http://127.0.0.1:8001/api/config") as resp:
                data = await resp.json()
                assert resp.status == 200
                assert "version" in data
                assert "features" in data
                print("✅ 配置获取测试通过")
            
            # 测试工作空间统计
            print("📊 测试工作空间...")
            stats = await workspace.get_statistics()
            print(f"✅ 工作空间测试通过 ({stats.total_files} 文件, {stats.total_size_mb:.2f} MB)")
            
            print("\n🎉 所有测试通过！AgentBus API工作正常")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 关闭服务器
        server.should_exit = True
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        
        print("🔚 测试服务器已关闭")


async def test_workspace():
    """测试工作空间功能"""
    print("📁 测试工作空间功能...")
    
    # 初始化工作空间
    workspace = await init_workspace("./test_workspace")
    
    # 测试写入文件
    print("📝 测试写入脚本文件...")
    script_path = await workspace.write_script(
        "test_script.py",
        "#!/usr/bin/env python3\nprint('Hello, AgentBus!')\n"
    )
    print(f"✅ 脚本文件已写入: {script_path}")
    
    print("📋 测试写入计划文件...")
    plan_path = await workspace.write_plan(
        "test_plan.md",
        "# 测试计划\n\n这是一个测试计划文件\n"
    )
    print(f"✅ 计划文件已写入: {plan_path}")
    
    print("📄 测试写入上下文文件...")
    context_path = await workspace.write_context(
        "test_context.json",
        '{"test": true, "message": "Hello World"}'
    )
    print(f"✅ 上下文文件已写入: {context_path}")
    
    # 测试列出文件
    print("📂 测试列出文件...")
    files = await workspace.list_files()
    print(f"✅ 找到 {len(files)} 个文件")
    
    for file_info in files[:5]:  # 只显示前5个
        print(f"   - {file_info.name} ({file_info.file_type}, {file_info.size} bytes)")
    
    # 测试统计信息
    print("📊 测试统计信息...")
    stats = await workspace.get_statistics()
    print(f"✅ 统计信息:")
    print(f"   - 总文件数: {stats.total_files}")
    print(f"   - 总大小: {stats.total_size_mb:.2f} MB")
    print(f"   - 目录分布: {stats.directories}")


def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                 AgentBus API Test Suite                      ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # 运行工作空间测试
        asyncio.run(test_workspace())
        print()
        
        # 运行API测试
        asyncio.run(test_api())
        
    except KeyboardInterrupt:
        print("\n👋 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
