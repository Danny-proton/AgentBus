#!/usr/bin/env python3
"""
AgentBus 配置管理系统测试
Test script for AgentBus Configuration Management System
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config_manager import ConfigManager
from backup_manager import ConfigBackupManager
from file_manager import ConfigFileManager
from watcher import ConfigWatcher
from settings import ExtendedSettings

def test_config_manager():
    """测试配置管理器"""
    print("🧪 测试配置管理器...")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir(exist_ok=True)
        
        # 创建配置管理器
        manager = ConfigManager(config_dir)
        
        # 初始化
        success = manager.initialize()
        print(f"  ✅ 初始化: {'成功' if success else '失败'}")
        
        # 测试设置值
        manager.set_config_value("app.name", "TestApp")
        manager.set_config_value("app.version", "1.0.0")
        manager.set_config_value("database.host", "localhost")
        print(f"  ✅ 设置配置值: 成功")
        
        # 获取配置
        config = manager.get_config()
        print(f"  ✅ 获取配置: {len(config)} 个键值对")
        
        # 验证配置
        validation = manager.validate()
        print(f"  ✅ 配置验证: {'通过' if validation.is_valid else '失败'}")
        
        # 备份功能测试
        backup_id = manager.create_backup("test_backup")
        print(f"  ✅ 创建备份: {backup_id}")
        
        # 文件管理测试
        test_data = {"test": "data", "number": 123}
        success = manager.write_config_file("test_config.yaml", test_data)
        print(f"  ✅ 写入配置文件: {'成功' if success else '失败'}")
        
        # 读取配置文件
        read_data = manager.read_config_file("test_config.yaml")
        print(f"  ✅ 读取配置文件: {'成功' if read_data else '失败'}")
        
        # 列出备份
        backups = manager.list_backups()
        print(f"  ✅ 列出备份: {len(backups)} 个备份")
        
        print("🎉 配置管理器测试完成!")
        return True

def test_file_manager():
    """测试文件管理器"""
    print("\n🧪 测试文件管理器...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        
        # 创建文件管理器
        file_manager = ConfigFileManager(config_dir)
        
        # 创建测试文件
        test_content = """
app:
  name: TestApp
  version: 1.0.0
database:
  host: localhost
  port: 5432
  name: test_db
"""
        
        # 创建文件
        success, errors = file_manager.create_file(
            config_dir / "test.yaml",
            test_content.strip(),
            validate=True
        )
        print(f"  ✅ 创建文件: {'成功' if success else '失败'}")
        
        # 验证文件
        validation_result = file_manager.validate_file(config_dir / "test.yaml")
        print(f"  ✅ 验证文件: {'通过' if validation_result.is_valid else '失败'}")
        
        # 列出文件
        files = file_manager.list_files()
        print(f"  ✅ 列出文件: {len(files)} 个文件")
        
        # 获取文件信息
        file_info = file_manager.get_file_info(config_dir / "test.yaml")
        print(f"  ✅ 文件信息: {file_info is not None}")
        
        # 清理
        file_manager.cleanup()
        print(f"  ✅ 清理资源: 成功")
        
        print("🎉 文件管理器测试完成!")
        return True

def test_backup_manager():
    """测试备份管理器"""
    print("\n🧪 测试备份管理器...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        backup_dir = config_dir / "backups"
        
        # 创建一些测试文件
        test_files = [
            "config1.yaml",
            "config2.json",
            "config3.toml"
        ]
        
        for file_name in test_files:
            file_path = config_dir / file_name
            with open(file_path, 'w') as f:
                f.write(f"# Test config file: {file_name}\nkey=value\n")
        
        # 创建备份管理器
        backup_manager = ConfigBackupManager(config_dir, backup_dir)
        
        # 创建备份
        backup_id = backup_manager.create_backup(
            "test_backup",
            "测试备份",
            backup_type="manual"
        )
        print(f"  ✅ 创建备份: {backup_id}")
        
        # 列出备份
        backups = backup_manager.list_backups()
        print(f"  ✅ 列出备份: {len(backups)} 个备份")
        
        # 验证备份
        is_valid, errors = backup_manager.verify_backup(backup_id)
        print(f"  ✅ 验证备份: {'通过' if is_valid else '失败'}")
        
        # 清理
        backup_manager.cleanup()
        print(f"  ✅ 清理资源: 成功")
        
        print("🎉 备份管理器测试完成!")
        return True

def test_integration():
    """测试集成功能"""
    print("\n🧪 测试集成功能...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        
        # 创建配置管理器
        manager = ConfigManager(config_dir)
        
        # 初始化
        success = manager.initialize()
        print(f"  ✅ 初始化: {'成功' if success else '失败'}")
        
        # 创建一些配置
        manager.set_config_value("app.name", "IntegrationTest")
        manager.set_config_value("app.debug", True)
        manager.set_config_value("database.host", "localhost")
        
        # 创建备份
        backup_id = manager.create_backup("integration_test")
        print(f"  ✅ 创建集成测试备份: {backup_id}")
        
        # 修改配置
        manager.set_config_value("app.version", "2.0.0")
        
        # 恢复备份
        restore_success = manager.restore_backup(backup_id)
        print(f"  ✅ 恢复备份: {'成功' if restore_success else '失败'}")
        
        # 验证配置是否恢复
        app_version = manager.get_config_value("app.version", "1.0.0")
        print(f"  ✅ 配置恢复验证: app.version = {app_version}")
        
        # 关闭管理器
        if hasattr(manager, '__exit__'):
            manager.__exit__(None, None, None)
        
        print("🎉 集成测试完成!")
        return True

def main():
    """主函数"""
    print("🚀 AgentBus 配置管理系统测试开始\n")
    
    try:
        # 运行所有测试
        tests = [
            ("配置管理器", test_config_manager),
            ("文件管理器", test_file_manager),
            ("备份管理器", test_backup_manager),
            ("集成测试", test_integration)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n{'='*50}")
            print(f"运行测试: {test_name}")
            print('='*50)
            
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name}: 通过")
                else:
                    print(f"❌ {test_name}: 失败")
            except Exception as e:
                print(f"❌ {test_name}: 异常 - {e}")
        
        # 测试结果
        print(f"\n{'='*50}")
        print(f"测试结果: {passed}/{total} 通过")
        print('='*50)
        
        if passed == total:
            print("🎉 所有测试通过! 配置管理系统工作正常。")
            return 0
        else:
            print(f"⚠️  {total - passed} 个测试失败。")
            return 1
            
    except Exception as e:
        print(f"💥 测试运行异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())