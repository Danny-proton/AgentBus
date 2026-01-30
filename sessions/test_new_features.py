#!/usr/bin/env python3
"""
新功能验证脚本
New Features Validation Script

快速验证新添加的会话管理功能是否正常工作
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_new_features():
    """测试新功能"""
    try:
        print("🔧 正在测试新功能...")
        
        # 测试导入
        print("1. 测试模块导入...")
        from sessions import (
            SessionSynchronizer,
            SessionPersistence,
            SessionStateTracker,
            SessionExpiryManager,
            SessionSystem,
            SyncStrategy,
            BackupFormat,
            EventType,
            ExpiryStrategy,
            CleanupAction
        )
        print("   ✅ 所有新模块导入成功")
        
        # 测试配置
        print("2. 测试配置系统...")
        from sessions import (
            SessionSystemConfig,
            get_development_config,
            get_production_config
        )
        
        dev_config = get_development_config()
        prod_config = get_production_config()
        print("   ✅ 配置系统工作正常")
        
        # 测试枚举类
        print("3. 测试枚举类...")
        print(f"   SyncStrategy.AUTO = {SyncStrategy.AUTO.value}")
        print(f"   BackupFormat.JSON_GZ = {BackupFormat.JSON_GZ.value}")
        print(f"   EventType.MESSAGE_RECEIVED = {EventType.MESSAGE_RECEIVED.value}")
        print(f"   ExpiryStrategy.TIME_BASED = {ExpiryStrategy.TIME_BASED.value}")
        print(f"   CleanupAction.ARCHIVE = {CleanupAction.ARCHIVE.value}")
        print("   ✅ 枚举类工作正常")
        
        # 测试完整系统创建
        print("4. 测试完整系统创建...")
        from sessions import create_session_system
        
        config = SessionSystemConfig(
            storage_type="MEMORY",
            enable_cleanup=True,
            enable_sync=False,  # 暂时禁用同步以简化测试
            enable_persistence=False,
            enable_tracking=False,
            enable_expiry=True
        )
        
        system = create_session_system(config)
        print("   ✅ 完整系统创建成功")
        
        # 测试系统状态
        print("5. 测试系统状态...")
        status = await system.get_system_status()
        print(f"   系统状态: {status['system']['status']}")
        print("   ✅ 系统状态检查正常")
        
        print("\n🎉 所有新功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_new_features())
    sys.exit(0 if success else 1)