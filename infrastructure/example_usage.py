"""
AgentBus 基础设施系统使用示例

演示如何使用基础设施系统的各个功能模块：
1. 网络管理
2. 文件系统管理
3. 进程管理
4. 系统监控
5. 设备管理
"""

import asyncio
import json
from pathlib import Path

# 导入基础设施模块
from .net import NetworkManager, SsrFProtection, NetworkConfig
from .filesystem import FileSystemManager, ArchiveManager, ArchiveKind
from .process import ProcessManager, BinaryManager
from .monitoring import MonitoringManager, DiagnosticEventType
from .device import DeviceManager, DeviceType, DeviceStatus


async def network_management_example():
    """网络管理示例"""
    print("=== 网络管理示例 ===")
    
    # 创建SSRF保护
    ssrf_protection = SsrFProtection()
    
    # 创建网络管理器
    network_manager = NetworkManager(ssrf_protection)
    
    try:
        # 获取网络接口信息
        interfaces = await network_manager.get_network_interfaces()
        print(f"网络接口数量: {len(interfaces)}")
        for interface in interfaces:
            print(f"  - {interface['name']}: {interface['is_up']}")
        
        # 测试连接性
        connectivity = await network_manager.test_connectivity("8.8.8.8", 53)
        print(f"到8.8.8.8的连接测试: {'成功' if connectivity else '失败'}")
        
        # 检查URL安全性
        safe_url = ssrf_protection.is_safe_url("https://www.google.com")
        unsafe_url = ssrf_protection.is_safe_url("http://localhost:8080")
        print(f"Google URL安全: {safe_url}")
        print(f"localhost URL安全: {unsafe_url}")
        
    except Exception as e:
        print(f"网络管理示例错误: {e}")


async def filesystem_management_example():
    """文件系统管理示例"""
    print("\n=== 文件系统管理示例 ===")
    
    # 创建文件系统管理器
    fs_manager = FileSystemManager()
    
    try:
        # 创建测试目录
        test_dir = Path("test_infrastructure")
        await fs_manager.create_directory(test_dir)
        print(f"创建测试目录: {test_dir}")
        
        # 创建测试文件
        test_file = test_dir / "test.txt"
        await fs_manager.write_file("Hello, Infrastructure!", test_file)
        print(f"创建测试文件: {test_file}")
        
        # 获取文件信息
        file_info = await fs_manager.get_file_info(test_file)
        print(f"文件信息: {file_info.name}, 大小: {file_info.size} 字节")
        
        # 列出目录内容
        contents = await fs_manager.list_directory(test_dir)
        print(f"目录内容: {[item.name for item in contents]}")
        
        # 获取磁盘使用情况
        disk_usage = await fs_manager.get_disk_usage(test_dir)
        print(f"磁盘使用情况: {disk_usage}")
        
    except Exception as e:
        print(f"文件系统管理示例错误: {e}")
    
    finally:
        # 清理测试文件
        try:
            await fs_manager.delete_directory(test_dir, recursive=True)
            print("清理测试文件完成")
        except Exception:
            pass


async def archive_management_example():
    """存档管理示例"""
    print("\n=== 存档管理示例 ===")
    
    # 创建存档管理器
    archive_manager = ArchiveManager()
    
    try:
        # 创建测试文件用于存档
        test_dir = Path("archive_test")
        test_file = test_dir / "data.txt"
        await test_file.parent.mkdir(exist_ok=True)
        await test_file.write_text("Test data for archiving")
        
        # 创建ZIP存档
        archive_path = Path("test_archive.zip")
        success = await archive_manager.create_archive(
            source_path=test_dir,
            archive_path=archive_path,
            kind=ArchiveKind.ZIP
        )
        print(f"创建ZIP存档: {'成功' if success else '失败'}")
        
        if success:
            # 列出存档内容
            contents = await archive_manager.list_archive_contents(archive_path)
            print(f"存档内容: {[entry.name for entry in contents]}")
            
            # 获取存档统计
            stats = await archive_manager.get_archive_stats(archive_path)
            if stats:
                print(f"存档统计: {stats.total_entries}个条目, 压缩率: {stats.compression_ratio:.1f}%")
            
            # 验证存档
            verification = await archive_manager.verify_archive(archive_path)
            print(f"存档验证: {'通过' if verification['valid'] else '失败'}")
        
        # 提取存档到临时目录
        extract_path = Path("extracted")
        if archive_path.exists():
            extract_success = await archive_manager.extract_archive(archive_path, extract_path)
            print(f"提取存档: {'成功' if extract_success else '失败'}")
            
            if extract_success:
                # 列出提取的内容
                extracted_contents = await fs_manager.list_directory(extract_path)
                print(f"提取的内容: {[item.name for item in extracted_contents]}")
                
                # 清理提取目录
                await fs_manager.delete_directory(extract_path, recursive=True)
        
        # 清理测试文件
        await fs_manager.delete_directory(test_dir, recursive=True)
        if archive_path.exists():
            archive_path.unlink()
            
    except Exception as e:
        print(f"存档管理示例错误: {e}")


async def process_management_example():
    """进程管理示例"""
    print("\n=== 进程管理示例 ===")
    
    # 创建进程管理器
    process_manager = ProcessManager()
    
    try:
        # 获取系统资源使用情况
        system_resources = await process_manager.get_system_resources()
        print(f"CPU使用率: {system_resources.cpu_percent:.1f}%")
        print(f"内存使用率: {system_resources.memory_percent:.1f}%")
        print(f"进程数量: {system_resources.process_count}")
        
        # 列出进程
        processes = await process_manager.list_processes(limit=5, sort_by='cpu')
        print(f"CPU使用率最高的进程:")
        for process in processes:
            print(f"  - {process.name} (PID: {process.pid}): {process.cpu_percent:.1f}%")
        
        # 获取进程树
        current_process = await process_manager.get_process_info(os.getpid())
        if current_process:
            print(f"当前进程: {current_process.name} (PID: {current_process.pid})")
        
    except Exception as e:
        print(f"进程管理示例错误: {e}")


async def binary_management_example():
    """二进制管理示例"""
    print("\n=== 二进制管理示例 ===")
    
    # 创建二进制管理器
    binary_manager = BinaryManager()
    
    try:
        # 添加必需二进制文件
        binary_manager.add_required_binary("python")
        binary_manager.add_required_binary("ls")
        
        # 检查必需二进制文件
        required_status = await binary_manager.check_required_binaries()
        print("必需二进制文件状态:")
        for binary, found in required_status.items():
            print(f"  - {binary}: {'已找到' if found else '未找到'}")
        
        # 查找二进制文件
        python_path = await binary_manager.find_binary("python")
        if python_path:
            print(f"Python路径: {python_path}")
            
            # 获取二进制信息
            binary_info = await binary_manager._get_binary_info(python_path)
            if binary_info:
                print(f"Python版本: {binary_info.version}")
                print(f"Python大小: {binary_info.size} 字节")
        
    except Exception as e:
        print(f"二进制管理示例错误: {e}")


async def monitoring_example():
    """监控示例"""
    print("\n=== 监控示例 ===")
    
    # 创建监控管理器
    monitoring_manager = MonitoringManager()
    
    try:
        # 添加自定义告警规则
        from .monitoring.system_metrics import AlertRule
        
        monitoring_manager.add_alert_rule(AlertRule(
            name="test_cpu_alert",
            metric="cpu_percent",
            operator=">",
            threshold=50.0,
            severity="WARNING",
            duration_seconds=30
        ))
        
        # 开始监控（短期）
        await monitoring_manager.start_monitoring(
            metrics_interval=2.0,
            process_monitoring=True,
            network_monitoring=False  # 简化示例
        )
        
        print("监控已启动，等待收集数据...")
        await asyncio.sleep(10)  # 等待收集数据
        
        # 获取当前指标
        current_metrics = monitoring_manager.get_current_metrics()
        if current_metrics:
            print(f"当前CPU使用率: {current_metrics.cpu_percent:.1f}%")
            print(f"当前内存使用率: {current_metrics.memory_percent:.1f}%")
            print(f"当前磁盘使用率: {current_metrics.disk_percent:.1f}%")
        
        # 获取活跃告警
        active_alerts = monitoring_manager.get_active_alerts()
        print(f"活跃告警数量: {len(active_alerts)}")
        
        # 获取系统统计
        stats = monitoring_manager.get_system_statistics()
        print(f"监控统计: {stats}")
        
        # 发出自定义事件
        monitoring_manager.emit_custom_event(
            DiagnosticEventType.SYSTEM_INFO,
            "example",
            "示例监控事件",
            data={"test": True}
        )
        
        # 停止监控
        await monitoring_manager.stop_monitoring()
        print("监控已停止")
        
    except Exception as e:
        print(f"监控示例错误: {e}")


async def device_management_example():
    """设备管理示例"""
    print("\n=== 设备管理示例 ===")
    
    # 创建设备管理器
    device_manager = DeviceManager()
    
    try:
        # 创建设备身份
        device_info = await device_manager.create_device(
            device_name="AgentBus Infrastructure Demo",
            device_type=DeviceType.SERVER,
            capabilities=["monitoring", "management"],
            metadata={"version": "1.0", "description": "Infrastructure demo device"}
        )
        
        print(f"创建设备: {device_info.device_name} (ID: {device_info.device_id})")
        
        # 获取设备统计
        stats = device_manager.get_device_statistics()
        print(f"设备统计: {stats}")
        
        # 模拟设备发现（简化版）
        print("模拟设备发现...")
        discovered_devices = await device_manager.discover_devices(timeout=2.0)
        print(f"发现设备数量: {len(discovered_devices)}")
        
    except Exception as e:
        print(f"设备管理示例错误: {e}")


async def comprehensive_integration_example():
    """综合集成示例"""
    print("\n=== 综合集成示例 ===")
    
    try:
        # 创建基础设施组件
        ssrf_protection = SsrFProtection()
        fs_manager = FileSystemManager()
        archive_manager = ArchiveManager()
        process_manager = ProcessManager()
        binary_manager = BinaryManager()
        monitoring_manager = MonitoringManager(ssrf_protection)
        device_manager = DeviceManager()
        
        # 执行健康检查
        print("执行系统健康检查...")
        
        # 1. 系统指标
        system_resources = await process_manager.get_system_resources()
        print(f"系统CPU使用率: {system_resources.cpu_percent:.1f}%")
        print(f"系统内存使用率: {system_resources.memory_percent:.1f}%")
        
        # 2. 网络状态
        interfaces = await (await NetworkManager(ssrf_protection)).get_network_interfaces()
        online_interfaces = [i for i in interfaces if i.get('is_up', False)]
        print(f"在线网络接口: {len(online_interfaces)}/{len(interfaces)}")
        
        # 3. 磁盘空间
        disk_usage = await fs_manager.get_disk_usage()
        print(f"磁盘使用率: {disk_usage.get('used_percent', 0):.1f}%")
        
        # 4. 进程状态
        processes = await process_manager.list_processes(limit=10)
        print(f"活跃进程数: {len(processes)}")
        
        # 5. 设备管理
        current_device = device_manager.get_current_device()
        if current_device:
            print(f"当前设备: {current_device.device_name}")
        
        # 6. 生成综合报告
        report = {
            "timestamp": asyncio.get_event_loop().time(),
            "system_health": {
                "cpu_percent": system_resources.cpu_percent,
                "memory_percent": system_resources.memory_percent,
                "disk_percent": disk_usage.get('used_percent', 0),
                "network_interfaces": len(online_interfaces),
                "active_processes": len(processes)
            },
            "components": {
                "network_protection": "active",
                "filesystem": "active",
                "process_monitoring": "active",
                "binary_management": "active",
                "device_management": "active"
            }
        }
        
        print("\n=== 综合健康报告 ===")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        
        return report
        
    except Exception as e:
        print(f"综合集成示例错误: {e}")
        return None


async def main():
    """主函数 - 运行所有示例"""
    print("AgentBus 基础设施系统演示")
    print("=" * 50)
    
    # 运行各个示例
    await network_management_example()
    await filesystem_management_example()
    await archive_management_example()
    await process_management_example()
    await binary_management_example()
    await monitoring_example()
    await device_management_example()
    await comprehensive_integration_example()
    
    print("\n" + "=" * 50)
    print("基础设施系统演示完成")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())