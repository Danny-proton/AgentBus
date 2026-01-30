"""
AgentBus任务调度系统集成组件

将TaskManager、CronHandler、WorkflowEngine整合为一个完整的调度系统
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class SchedulerConfig:
    """调度器配置"""
    storage_path: str = "./data/scheduler"
    max_workers: int = 5
    enable_persistence: bool = True
    cleanup_interval_hours: int = 24
    max_task_age_days: int = 7
    max_workflow_age_hours: int = 24
    enable_monitoring: bool = True
    log_level: str = "INFO"


class AgentBusScheduler:
    """AgentBus调度器主类"""
    
    def __init__(self, config: SchedulerConfig = None):
        """初始化调度器"""
        self.config = config or SchedulerConfig()
        self.storage_path = Path(self.config.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化各个组件
        from task_manager import TaskManager
        from cron_handler import CronHandler
        from workflow import WorkflowEngine
        
        self.task_manager = TaskManager(
            storage_path=str(self.storage_path / "tasks"),
            max_workers=self.config.max_workers
        )
        
        self.cron_handler = CronHandler(self.task_manager)
        self.workflow_engine = WorkflowEngine(self.task_manager)
        
        # 设置日志
        self.logger = self._setup_logging()
        
        # 运行状态
        self.running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # 监控和统计
        self.monitoring_enabled = self.config.enable_monitoring
        self.metrics: Dict[str, Any] = {}
        
        # 事件总线
        self.event_handlers: Dict[str, List[Callable]] = {
            'task_created': [],
            'task_started': [],
            'task_completed': [],
            'task_failed': [],
            'workflow_started': [],
            'workflow_completed': [],
            'workflow_failed': [],
            'scheduled_task_executed': []
        }
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("agentbus_scheduler")
        logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def start(self):
        """启动调度器"""
        if self.running:
            self.logger.warning("调度器已经在运行中")
            return
        
        self.logger.info("启动AgentBus调度器...")
        
        try:
            # 启动各个组件
            await self.task_manager.start()
            await self.cron_handler.start()
            
            # 设置事件回调
            self._setup_event_callbacks()
            
            # 启动清理任务
            if self.monitoring_enabled:
                self._start_cleanup_task()
            
            self.running = True
            self.logger.info("AgentBus调度器启动完成")
            
        except Exception as e:
            self.logger.error(f"启动调度器失败: {e}")
            raise
    
    async def stop(self):
        """停止调度器"""
        if not self.running:
            return
        
        self.logger.info("停止AgentBus调度器...")
        
        try:
            # 停止清理任务
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # 停止各个组件
            await self.cron_handler.stop()
            await self.task_manager.stop()
            
            self.running = False
            self.logger.info("AgentBus调度器已停止")
            
        except Exception as e:
            self.logger.error(f"停止调度器失败: {e}")
            raise
    
    def _setup_event_callbacks(self):
        """设置事件回调"""
        # 任务事件回调
        self.task_manager.add_callback('created', self._on_task_created)
        self.task_manager.add_callback('started', self._on_task_started)
        self.task_manager.add_callback('completed', self._on_task_completed)
        self.task_manager.add_callback('failed', self._on_task_failed)
        
        # 工作流事件回调
        self.workflow_engine.add_callback('workflow_started', self._on_workflow_started)
        self.workflow_engine.add_callback('workflow_completed', self._on_workflow_completed)
        self.workflow_engine.add_callback('workflow_failed', self._on_workflow_failed)
        
        # 定时任务事件回调
        self.cron_handler.add_execution_callback(self._on_scheduled_task_executed)
    
    def _on_task_created(self, task):
        """任务创建事件"""
        self._emit_event('task_created', task)
        self._update_metrics()
    
    def _on_task_started(self, task):
        """任务开始事件"""
        self._emit_event('task_started', task)
        self._update_metrics()
    
    def _on_task_completed(self, task):
        """任务完成事件"""
        self._emit_event('task_completed', task)
        self._update_metrics()
    
    def _on_task_failed(self, task):
        """任务失败事件"""
        self._emit_event('task_failed', task)
        self._update_metrics()
    
    def _on_workflow_started(self, workflow):
        """工作流开始事件"""
        self._emit_event('workflow_started', workflow)
        self._update_metrics()
    
    def _on_workflow_completed(self, workflow):
        """工作流完成事件"""
        self._emit_event('workflow_completed', workflow)
        self._update_metrics()
    
    def _on_workflow_failed(self, workflow):
        """工作流失败事件"""
        self._emit_event('workflow_failed', workflow)
        self._update_metrics()
    
    def _on_scheduled_task_executed(self, task, result, error):
        """定时任务执行事件"""
        self._emit_event('scheduled_task_executed', {
            'task': task,
            'result': result,
            'error': error
        })
        self._update_metrics()
    
    def _emit_event(self, event_name: str, data: Any):
        """触发事件"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(data))
                    else:
                        handler(data)
                except Exception as e:
                    self.logger.error(f"事件处理器错误 ({event_name}): {e}")
    
    def add_event_handler(self, event_name: str, handler: Callable):
        """添加事件处理器"""
        if event_name in self.event_handlers:
            self.event_handlers[event_name].append(handler)
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_loop():
            while self.running:
                try:
                    await asyncio.sleep(self.config.cleanup_interval_hours * 3600)
                    await self._cleanup_old_data()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"清理任务错误: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def _cleanup_old_data(self):
        """清理旧数据"""
        self.logger.info("开始清理旧数据...")
        
        # 清理已完成的任务
        task_count = self.task_manager.cleanup_completed_tasks(
            max_age_days=self.config.max_task_age_days
        )
        
        # 清理已禁用和完成次数已到的定时任务
        cron_count = self.cron_handler.cleanup_disabled_tasks()
        
        # 清理已完成的工作流
        workflow_count = self.workflow_engine.cleanup_completed_workflows(
            max_age_hours=self.config.max_workflow_age_hours
        )
        
        self.logger.info(
            f"清理完成: 任务 {task_count} 个, "
            f"Cron {cron_count} 个, "
            f"工作流 {workflow_count} 个"
        )
    
    def _update_metrics(self):
        """更新指标"""
        if not self.monitoring_enabled:
            return
        
        self.metrics.update({
            'tasks': self.task_manager.get_task_stats(),
            'workflows': self.workflow_engine.get_workflow_statistics(),
            'cron': self.cron_handler.get_statistics(),
            'last_update': asyncio.get_event_loop().time()
        })
    
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            'running': self.running,
            'components': {
                'task_manager': self.task_manager is not None,
                'cron_handler': self.cron_handler is not None,
                'workflow_engine': self.workflow_engine is not None
            },
            'metrics': self.metrics if self.monitoring_enabled else None,
            'config': {
                'storage_path': str(self.storage_path),
                'max_workers': self.config.max_workers,
                'enable_persistence': self.config.enable_persistence,
                'cleanup_interval_hours': self.config.cleanup_interval_hours,
                'enable_monitoring': self.monitoring_enabled
            }
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取详细指标"""
        if not self.monitoring_enabled:
            return {'error': 'Monitoring is disabled'}
        
        return {
            'timestamp': asyncio.get_event_loop().time(),
            'tasks': self.task_manager.get_task_stats(),
            'workflows': self.workflow_engine.get_workflow_statistics(),
            'cron': self.cron_handler.get_statistics(),
            'system': {
                'storage_path': str(self.storage_path),
                'storage_exists': self.storage_path.exists()
            }
        }
    
    def save_config(self, config_path: Optional[str] = None):
        """保存配置"""
        if not self.config.enable_persistence:
            return
        
        config_file = Path(config_path) if config_path else self.storage_path / "config.json"
        
        config_data = {
            'storage_path': str(self.storage_path),
            'max_workers': self.config.max_workers,
            'cleanup_interval_hours': self.config.cleanup_interval_hours,
            'max_task_age_days': self.config.max_task_age_days,
            'max_workflow_age_hours': self.config.max_workflow_age_hours,
            'enable_monitoring': self.monitoring_enabled,
            'log_level': self.config.log_level
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"配置已保存到: {config_file}")
    
    @classmethod
    def load_config(cls, config_path: str) -> 'AgentBusScheduler':
        """从配置文件加载"""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        config = SchedulerConfig(
            storage_path=config_data.get('storage_path', './data/scheduler'),
            max_workers=config_data.get('max_workers', 5),
            cleanup_interval_hours=config_data.get('cleanup_interval_hours', 24),
            max_task_age_days=config_data.get('max_task_age_days', 7),
            max_workflow_age_hours=config_data.get('max_workflow_age_hours', 24),
            enable_monitoring=config_data.get('enable_monitoring', True),
            log_level=config_data.get('log_level', 'INFO')
        )
        
        scheduler = cls(config)
        return scheduler
    
    # 便利方法
    async def create_scheduled_task(
        self,
        name: str,
        cron_expression: str,
        func: Callable,
        args: tuple = None,
        kwargs: dict = None,
        **cron_options
    ) -> str:
        """创建定时任务的便利方法"""
        task_id = self.cron_handler.add_scheduled_task(
            name=name,
            cron_expression=cron_expression,
            func=func,
            args=args,
            kwargs=kwargs,
            **cron_options
        )
        
        self.logger.info(f"创建定时任务: {name} ({task_id})")
        return task_id
    
    async def create_workflow_task(
        self,
        name: str,
        workflow_func: Callable,
        args: tuple = None,
        kwargs: dict = None,
        **task_options
    ) -> str:
        """创建工作流任务的便利方法"""
        from task_manager import TaskConfig
        config = TaskConfig(**task_options) if task_options else None
        
        task_id = self.task_manager.create_task(
            name=name,
            func=workflow_func,
            args=args,
            kwargs=kwargs,
            config=config
        )
        
        self.logger.info(f"创建工作流任务: {name} ({task_id})")
        return task_id
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health = {
            'status': 'healthy',
            'timestamp': asyncio.get_event_loop().time(),
            'components': {}
        }
        
        # 检查各个组件
        try:
            task_stats = self.task_manager.get_task_stats()
            health['components']['task_manager'] = {
                'status': 'healthy',
                'total_tasks': task_stats['total'],
                'running_tasks': task_stats['running']
            }
        except Exception as e:
            health['components']['task_manager'] = {'status': 'unhealthy', 'error': str(e)}
            health['status'] = 'degraded'
        
        try:
            cron_stats = self.cron_handler.get_statistics()
            health['components']['cron_handler'] = {
                'status': 'healthy',
                'total_tasks': cron_stats['total_scheduled_tasks'],
                'enabled_tasks': cron_stats['enabled_tasks']
            }
        except Exception as e:
            health['components']['cron_handler'] = {'status': 'unhealthy', 'error': str(e)}
            health['status'] = 'degraded'
        
        try:
            workflow_stats = self.workflow_engine.get_workflow_statistics()
            health['components']['workflow_engine'] = {
                'status': 'healthy',
                'total_workflows': workflow_stats['total'],
                'running_workflows': workflow_stats['running']
            }
        except Exception as e:
            health['components']['workflow_engine'] = {'status': 'unhealthy', 'error': str(e)}
            health['status'] = 'degraded'
        
        return health
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if self.running:
            asyncio.create_task(self.stop())


# 便捷函数
async def create_scheduler(
    storage_path: str = "./data/scheduler",
    max_workers: int = 5,
    **config_options
) -> AgentBusScheduler:
    """创建调度器的便捷函数"""
    config = SchedulerConfig(
        storage_path=storage_path,
        max_workers=max_workers,
        **config_options
    )
    
    scheduler = AgentBusScheduler(config)
    await scheduler.start()
    
    return scheduler


async def quick_demo():
    """快速演示"""
    print("AgentBus调度器快速演示")
    
    # 创建调度器
    scheduler = await create_scheduler("./data/demo_scheduler")
    
    try:
        # 添加一个简单的定时任务
        async def demo_task():
            print(f"[{asyncio.get_event_loop().time():.1f}] 演示任务执行")
            return "演示完成"
        
        # 每3秒执行一次，共执行3次
        task_id = await scheduler.create_scheduled_task(
            name="演示定时任务",
            cron_expression="*/3 * * * * *",
            func=demo_task,
            max_runs=3
        )
        
        print(f"创建定时任务: {task_id}")
        
        # 运行10秒演示
        await asyncio.sleep(10)
        
        # 显示状态
        status = scheduler.get_status()
        print(f"调度器状态: {status['status']}")
        
        # 健康检查
        health = await scheduler.health_check()
        print(f"健康状态: {health['status']}")
        
    finally:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(quick_demo())