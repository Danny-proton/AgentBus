#!/usr/bin/env python3
"""
完整会话管理系统演示脚本
Complete Session Management System Demo

展示如何使用新的完整会话管理系统功能：
1. 会话管理
2. 会话同步
3. 会话持久化
4. 会话状态跟踪
5. 会话过期处理
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 导入新的会话管理系统
from agentbus.sessions import (
    # 完整系统
    initialize_sessions,
    create_default_session_system,
    get_development_config,
    get_production_config,
    
    # 核心类和枚举
    SessionContext,
    SessionType,
    SessionStatus,
    Platform,
    
    # 事件类型
    EventType,
    
    # 通知回调
    default_notification_callback,
    create_email_notification_callback,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_basic_system():
    """演示基础会话管理功能"""
    logger.info("=== 基础会话管理系统演示 ===")
    
    # 初始化基础会话系统
    system = await initialize_sessions(
        storage_type="MEMORY",
        enable_cleanup=True,
        cleanup_interval=60
    )
    
    try:
        # 创建会话
        session = await system.create_session(
            chat_id="chat_001",
            user_id="user_001",
            platform=Platform.TELEGRAM,
            session_type=SessionType.PRIVATE
        )
        
        logger.info(f"创建会话: {session.session_id}")
        
        # 添加消息
        await system.track_event(
            session.session_id,
            EventType.MESSAGE_RECEIVED,
            content="你好！这是第一条消息",
            user_id="user_001"
        )
        
        # 获取会话
        retrieved_session = await system.get_session(session.session_id)
        logger.info(f"获取会话: {retrieved_session.session_id}")
        logger.info(f"会话状态: {retrieved_session.get_status()}")
        logger.info(f"消息数量: {len(retrieved_session.conversation_history)}")
        
        # 清理过期会话
        results = await system.cleanup_expired_sessions()
        logger.info(f"清理结果: {len(results)} 个会话被处理")
        
    finally:
        await system.stop()


async def demo_complete_system():
    """演示完整会话管理系统"""
    logger.info("=== 完整会话管理系统演示 ===")
    
    # 创建配置
    config = get_development_config()
    config.update({
        "enable_sync": True,
        "enable_persistence": True,
        "enable_tracking": True,
        "enable_expiry": True,
        "archive_dir": Path("./demo_archive"),
        "backup_dir": Path("./demo_backups"),
    })
    
    # 添加通知回调
    async def custom_notification(notification_data):
        logger.info(f"通知: {notification_data['message']}")
    
    config.notification_callbacks = [default_notification_callback, custom_notification]
    
    # 初始化完整系统
    system = await initialize_sessions(
        storage_type="DATABASE",
        storage_config={"db_path": "./demo_sessions.db"},
        enable_all_features=True,
        **config.__dict__
    )
    
    try:
        # 创建多个会话
        sessions = []
        for i in range(3):
            session = await system.create_session(
                chat_id=f"chat_{i+1:03d}",
                user_id=f"user_{i+1:03d}",
                platform=Platform.TELEGRAM,
                session_type=SessionType.PRIVATE,
                ai_model="gpt-3.5-turbo"
            )
            sessions.append(session)
            logger.info(f"创建会话 {i+1}: {session.session_id}")
        
        # 添加事件和消息
        for i, session in enumerate(sessions):
            # 跟踪不同类型的事件
            await system.track_event(
                session.session_id,
                EventType.MESSAGE_RECEIVED,
                content=f"这是第{i+1}条消息",
                user_id=session.user_id
            )
            
            await system.track_event(
                session.session_id,
                EventType.USER_ACTIVITY,
                activity_type="typing",
                timestamp=datetime.now().isoformat()
            )
            
            # 状态变更
            await system.track_event(
                session.session_id,
                EventType.STATE_CHANGE,
                from_status=SessionStatus.ACTIVE.value,
                to_status=SessionStatus.IDLE.value,
                reason="用户空闲"
            )
        
        # 演示会话同步
        logger.info("演示会话同步...")
        source_session = sessions[0]
        synced_ids = await system.sync_sessions(source_session.session_id)
        logger.info(f"同步结果: {synced_ids}")
        
        # 创建备份
        logger.info("创建备份...")
        backup_id = await system.create_backup(
            description="演示备份",
            tags=["demo", "test"]
        )
        logger.info(f"备份创建: {backup_id}")
        
        # 获取系统状态
        logger.info("系统状态:")
        status = await system.get_system_status()
        logger.info(f"状态: {status['system']['status']}")
        logger.info(f"活跃会话: {status['metrics']['active_sessions']}")
        logger.info(f"同步操作: {status['metrics']['sync_operations']}")
        logger.info(f"备份数量: {status['metrics']['backup_count']}")
        
        # 健康检查
        logger.info("健康检查:")
        health = await system.get_health_check()
        logger.info(f"健康状态: {health['status']}")
        
        # 清理过期会话（干运行）
        logger.info("演示过期清理（干运行）...")
        results = await system.cleanup_expired_sessions(dry_run=True)
        logger.info(f"清理模拟结果: {len(results)} 个会话将被处理")
        
        # 等待一段时间模拟活动
        logger.info("等待5秒模拟时间流逝...")
        await asyncio.sleep(5)
        
        # 实际清理过期会话
        logger.info("执行过期清理...")
        results = await system.cleanup_expired_sessions()
        logger.info(f"实际清理结果: {len(results)} 个会话被处理")
        
    finally:
        await system.stop()


async def demo_custom_config():
    """演示自定义配置"""
    logger.info("=== 自定义配置演示 ===")
    
    # 创建自定义配置
    config = get_production_config(
        storage_config={"db_path": "./prod_sessions.db"},
        backup_dir=Path("./production_backups"),
        archive_dir=Path("./production_archive")
    )
    
    # 自定义过期规则
    from agentbus.sessions import ExpiryRule, ExpiryStrategy, CleanupAction
    
    # 24小时后归档
    archive_rule = ExpiryRule(
        rule_id="24h_archive",
        name="24小时归档规则",
        strategy=ExpiryStrategy.TIME_BASED,
        conditions={"default_hours": 24},
        actions=[CleanupAction.ARCHIVE],
        priority=1
    )
    
    # 7天后删除
    delete_rule = ExpiryRule(
        rule_id="7d_delete",
        name="7天删除规则",
        strategy=ExpiryStrategy.TIME_BASED,
        conditions={"default_hours": 168},  # 7天
        actions=[CleanupAction.DELETE],
        priority=2
    )
    
    # 创建系统
    system = await create_default_session_system(
        storage_type="DATABASE",
        storage_config={"db_path": "./custom_sessions.db"},
        enable_all_features=True,
        archive_dir=Path("./custom_archive"),
        backup_dir=Path("./custom_backups"),
        auto_cleanup_interval=60,  # 每分钟清理
        history_retention_days=60   # 保留60天历史
    )
    
    try:
        # 创建会话
        session = await system.create_session(
            chat_id="custom_chat",
            user_id="custom_user",
            platform=Platform.SLACK,
            session_type=SessionType.GROUP
        )
        
        logger.info(f"自定义会话: {session.session_id}")
        
        # 添加活动
        for i in range(5):
            await system.track_event(
                session.session_id,
                EventType.MESSAGE_RECEIVED,
                content=f"消息 {i+1}",
                user_id="custom_user"
            )
            await asyncio.sleep(1)
        
        # 获取统计信息
        status = await system.get_system_status()
        logger.info(f"自定义系统状态: {status['system']['status']}")
        logger.info(f"运行时间: {status['system']['uptime_seconds']:.2f} 秒")
        
    finally:
        await system.stop()


async def demo_performance_test():
    """性能测试演示"""
    logger.info("=== 性能测试演示 ===")
    
    system = await initialize_sessions(
        storage_type="MEMORY",
        enable_all_features=True,
        enable_tracking=True,
        enable_expiry=True,
        cleanup_interval=10  # 更频繁的清理
    )
    
    try:
        # 创建大量会话进行性能测试
        start_time = datetime.now()
        session_count = 100
        
        logger.info(f"创建 {session_count} 个会话...")
        
        tasks = []
        for i in range(session_count):
            task = system.create_session(
                chat_id=f"perf_chat_{i}",
                user_id=f"perf_user_{i}",
                platform=Platform.TELEGRAM,
                session_type=SessionType.PRIVATE
            )
            tasks.append(task)
        
        sessions = await asyncio.gather(*tasks)
        
        creation_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"创建 {session_count} 个会话耗时: {creation_time:.2f} 秒")
        logger.info(f"平均创建时间: {creation_time/session_count*1000:.2f} 毫秒/会话")
        
        # 添加消息测试
        start_time = datetime.now()
        
        message_tasks = []
        for i, session in enumerate(sessions[:50]):  # 测试前50个会话
            for j in range(5):
                task = system.track_event(
                    session.session_id,
                    EventType.MESSAGE_RECEIVED,
                    content=f"性能测试消息 {j+1}",
                    user_id=session.user_id
                )
                message_tasks.append(task)
        
        await asyncio.gather(*message_tasks)
        
        message_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"添加 {len(message_tasks)} 条消息耗时: {message_time:.2f} 秒")
        logger.info(f"平均消息处理时间: {message_time/len(message_tasks)*1000:.2f} 毫秒/消息")
        
        # 系统状态检查
        status = await system.get_system_status()
        logger.info(f"系统状态: {status['metrics']['active_sessions']} 个活跃会话")
        
    finally:
        await system.stop()


async def main():
    """主演示函数"""
    logger.info("开始完整会话管理系统演示...")
    
    try:
        # 1. 基础系统演示
        await demo_basic_system()
        await asyncio.sleep(2)
        
        # 2. 完整系统演示
        await demo_complete_system()
        await asyncio.sleep(2)
        
        # 3. 自定义配置演示
        await demo_custom_config()
        await asyncio.sleep(2)
        
        # 4. 性能测试演示
        await demo_performance_test()
        
        logger.info("所有演示完成！")
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())