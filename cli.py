"""
AgentBus CLI 工具接口
AgentBus CLI Tool Interface

本模块提供AgentBus的命令行接口，支持智能协作功能的CLI操作，
包括服务管理、配置、监控等功能。
"""

import asyncio
import click
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from loguru import logger

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentbus.core.settings import settings
from agentbus.services.hitl import HITLService
from agentbus.services.knowledge_bus import KnowledgeBus
from agentbus.services.multi_model_coordinator import MultiModelCoordinator
from agentbus.services.stream_response import StreamResponseProcessor
from agentbus.plugins.manager import PluginManager
from agentbus.channels.manager import ChannelManager
from agentbus.cli.commands import PluginCommands, ChannelCommands


# CLI工具类
class AgentBusCLI:
    """AgentBus命令行工具核心类"""
    
    def __init__(self):
        self.services = {}
        self.plugin_manager = None
        self.channel_manager = None
        self.initialized = False
    
    async def initialize(self):
        """初始化CLI工具"""
        try:
            # 初始化各个服务
            self.services = {
                "hitl": HITLService(),
                "knowledge_bus": KnowledgeBus(),
                "multi_model_coordinator": MultiModelCoordinator(),
                "stream_response": StreamResponseProcessor()
            }
            
            # 初始化插件管理器
            self.plugin_manager = PluginManager()
            
            # 初始化渠道管理器
            self.channel_manager = ChannelManager()
            
            # 启动服务
            await self.services["hitl"].start()
            await self.services["knowledge_bus"].initialize()
            await self.services["multi_model_coordinator"].initialize()
            await self.services["stream_response"].initialize()
            
            # 启动管理器
            await self.channel_manager.start()
            
            self.initialized = True
            click.echo("✅ AgentBus CLI工具初始化完成")
            
        except Exception as e:
            click.echo(f"❌ CLI工具初始化失败: {e}", err=True)
            sys.exit(1)
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 清理服务
            for name, service in self.services.items():
                if hasattr(service, 'shutdown'):
                    await service.shutdown()
                elif hasattr(service, 'stop'):
                    await service.stop()
            
            # 清理渠道管理器
            if self.channel_manager:
                await self.channel_manager.stop()
            
            self.initialized = False
            click.echo("✅ CLI工具资源清理完成")
            
        except Exception as e:
            click.echo(f"⚠️ 资源清理时发生错误: {e}", err=True)
    
    async def get_service_status(self, service_name: str = None) -> Dict[str, Any]:
        """获取服务状态"""
        if not self.initialized:
            return {"status": "not_initialized"}
        
        if service_name:
            if service_name not in self.services:
                return {"status": "service_not_found"}
            
            service = self.services[service_name]
            
            if service_name == "hitl":
                stats = await service.get_hitl_statistics()
                return {"service": service_name, "status": "running", "stats": stats}
            
            elif service_name == "knowledge_bus":
                stats = await service.get_knowledge_stats()
                return {"service": service_name, "status": "running", "stats": stats}
            
            elif service_name == "multi_model_coordinator":
                stats = await service.get_coordinator_stats()
                return {"service": service_name, "status": "running", "stats": stats}
            
            elif service_name == "stream_response":
                stats = await service.get_stream_stats()
                return {"service": service_name, "status": "running", "stats": stats}
            
            return {"service": service_name, "status": "running"}
        
        else:
            # 返回所有服务状态
            status = {}
            for name in self.services:
                status[name] = await self.get_service_status(name)
            return status


# CLI命令组
@click.group()
@click.option('--config', '-c', help='配置文件路径')
@click.option('--verbose', '-v', is_flag=True, help='详细输出')
@click.pass_context
def cli(ctx, config, verbose):
    """AgentBus命令行工具"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config'] = config
    
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")


@cli.command()
@click.option('--force', '-f', is_flag=True, help='强制重新初始化')
@click.pass_context
def init(ctx, force):
    """初始化AgentBus CLI工具"""
    verbose = ctx.obj.get('verbose', False)
    
    async def _init():
        cli_tool = AgentBusCLI()
        
        if verbose:
            click.echo("🔧 开始初始化AgentBus CLI工具...")
        
        await cli_tool.initialize()
        
        if verbose:
            click.echo("✅ 初始化完成")
        
        # 保存上下文供其他命令使用
        ctx.obj['cli_tool'] = cli_tool
        ctx.obj['plugin_manager'] = cli_tool.plugin_manager
        ctx.obj['channel_manager'] = cli_tool.channel_manager
    
    try:
        asyncio.run(_init())
    except Exception as e:
        click.echo(f"❌ 初始化失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--service', '-s', help='指定服务名称')
@click.pass_context
def status(ctx, service):
    """查看服务状态"""
    cli_tool = ctx.obj.get('cli_tool')
    
    if not cli_tool or not cli_tool.initialized:
        click.echo("❌ CLI工具未初始化，请先运行 'init' 命令", err=True)
        sys.exit(1)
    
    async def _status():
        status_data = await cli_tool.get_service_status(service)
        
        if service:
            click.echo(f"📊 {service} 服务状态:")
            click.echo(f"   状态: {status_data.get('status', 'unknown')}")
            
            if 'stats' in status_data:
                stats = status_data['stats']
                click.echo("   统计信息:")
                for key, value in stats.items():
                    click.echo(f"     - {key}: {value}")
        else:
            click.echo("📊 所有服务状态:")
            for name, info in status_data.items():
                click.echo(f"   {name}: {info.get('status', 'unknown')}")
    
    try:
        asyncio.run(_status())
    except Exception as e:
        click.echo(f"❌ 获取状态失败: {e}", err=True)


@cli.group()
def hitl():
    """人在回路 (HITL) 相关命令"""
    pass


@hitl.command()
@click.option('--limit', '-l', default=10, help='限制结果数量')
@click.pass_context
def requests(ctx, limit):
    """查看活跃的HITL请求"""
    cli_tool = ctx.obj.get('cli_tool')
    
    if not cli_tool or not cli_tool.initialized:
        click.echo("❌ CLI工具未初始化", err=True)
        sys.exit(1)
    
    async def _requests():
        stats = await cli_tool.services["hitl"].get_hitl_statistics()
        
        click.echo("🚨 活跃HITL请求:")
        if stats.get('active_requests', 0) > 0:
            click.echo(f"   活跃请求数: {stats['active_requests']}")
            click.echo(f"   总请求数: {stats['total_requests']}")
            click.echo(f"   完成率: {stats['completion_rate']:.2%}")
        else:
            click.echo("   当前没有活跃的HITL请求")
    
    try:
        asyncio.run(_requests())
    except Exception as e:
        click.echo(f"❌ 获取HITL请求失败: {e}", err=True)


@hitl.command()
@click.option('--agent-id', required=True, help='智能体ID')
@click.option('--title', required=True, help='请求标题')
@click.option('--description', required=True, help='请求描述')
@click.option('--priority', default='medium', help='优先级 (low, medium, high, urgent)')
@click.option('--timeout', default=30, help='超时时间(分钟)')
@click.pass_context
def request(ctx, agent_id, title, description, priority, timeout):
    """创建HITL请求"""
    cli_tool = ctx.obj.get('cli_tool')
    
    if not cli_tool or not cli_tool.initialized:
        click.echo("❌ CLI工具未初始化", err=True)
        sys.exit(1)
    
    async def _request():
        request_id = await cli_tool.services["hitl"].create_hitl_request(
            agent_id=agent_id,
            title=title,
            description=description,
            priority=priority,
            timeout_minutes=timeout
        )
        
        click.echo(f"✅ HITL请求已创建: {request_id}")
        click.echo(f"   智能体: {agent_id}")
        click.echo(f"   标题: {title}")
        click.echo(f"   优先级: {priority}")
        click.echo(f"   超时: {timeout}分钟")
    
    try:
        asyncio.run(_request())
    except Exception as e:
        click.echo(f"❌ 创建HITL请求失败: {e}", err=True)


@cli.group()
def knowledge():
    """知识总线相关命令"""
    pass


@knowledge.command()
@click.option('--type', 'knowledge_type', help='知识类型过滤')
@click.option('--limit', '-l', default=10, help='限制结果数量')
@click.pass_context
def search(ctx, knowledge_type, limit):
    """搜索知识"""
    cli_tool = ctx.obj.get('cli_tool')
    
    if not cli_tool or not cli_tool.initialized:
        click.echo("❌ CLI工具未初始化", err=True)
        sys.exit(1)
    
    async def _search():
        from agentbus.services.knowledge_bus import KnowledgeQuery, KnowledgeType
        
        # 构建查询
        query = KnowledgeQuery(
            query=click.prompt("请输入搜索关键词", type=str),
            knowledge_types=[KnowledgeType(knowledge_type)] if knowledge_type else None,
            limit=limit
        )
        
        results = await cli_tool.services["knowledge_bus"].search_knowledge(query)
        
        click.echo(f"🔍 搜索到 {len(results)} 条知识:")
        for i, result in enumerate(results, 1):
            knowledge = result.knowledge
            click.echo(f"   {i}. {knowledge.title}")
            click.echo(f"      类型: {knowledge.type.value}")
            click.echo(f"      相关性: {result.relevance_score:.2f}")
            click.echo(f"      内容: {knowledge.content[:100]}...")
            click.echo()
    
    try:
        asyncio.run(_search())
    except Exception as e:
        click.echo(f"❌ 搜索知识失败: {e}", err=True)


@knowledge.command()
@click.option('--type', 'knowledge_type', required=True, help='知识类型')
@click.option('--title', required=True, help='知识标题')
@click.option('--content', required=True, help='知识内容')
@click.option('--tags', help='标签（逗号分隔）')
@click.pass_context
def add(ctx, knowledge_type, title, content, tags):
    """添加知识"""
    cli_tool = ctx.obj.get('cli_tool')
    
    if not cli_tool or not cli_tool.initialized:
        click.echo("❌ CLI工具未初始化", err=True)
        sys.exit(1)
    
    async def _add():
        from agentbus.services.knowledge_bus import KnowledgeType, KnowledgeSource
        
        tag_list = [tag.strip() for tag in tags.split(',')] if tags else []
        
        knowledge_id = await cli_tool.services["knowledge_bus"].add_knowledge(
            title=title,
            content=content,
            type=KnowledgeType(knowledge_type),
            source=KnowledgeSource.USER,
            tags=tag_list
        )
        
        click.echo(f"✅ 知识已添加: {knowledge_id}")
        click.echo(f"   标题: {title}")
        click.echo(f"   类型: {knowledge_type}")
        click.echo(f"   标签: {', '.join(tag_list) if tag_list else '无'}")
    
    try:
        asyncio.run(_add())
    except Exception as e:
        click.echo(f"❌ 添加知识失败: {e}", err=True)


@cli.group()
def model():
    """多模型协调器相关命令"""
    pass


@model.command()
@click.pass_context
def list(ctx):
    """列出可用模型"""
    cli_tool = ctx.obj.get('cli_tool')
    
    if not cli_tool or not cli_tool.initialized:
        click.echo("❌ CLI工具未初始化", err=True)
        sys.exit(1)
    
    async def _list():
        models = cli_tool.services["multi_model_coordinator"].get_available_models()
        
        click.echo("🤖 可用AI模型:")
        for model in models:
            click.echo(f"   {model.model_id} ({model.model_name})")
            click.echo(f"      提供者: {model.provider}")
            click.echo(f"      能力: {', '.join([cap.value for cap in model.capabilities])}")
            click.echo(f"      质量评分: {model.quality_score:.2f}")
            click.echo()
    
    try:
        asyncio.run(_list())
    except Exception as e:
        click.echo(f"❌ 获取模型列表失败: {e}", err=True)


@model.command()
@click.option('--task-type', required=True, help='任务类型')
@click.option('--content', required=True, help='任务内容')
@click.option('--max-cost', type=float, help='最大成本限制')
@click.pass_context
def submit(ctx, task_type, content, max_cost):
    """提交AI任务"""
    cli_tool = ctx.obj.get('cli_tool')
    
    if not cli_tool or not cli_tool.initialized:
        click.echo("❌ CLI工具未初始化", err=True)
        sys.exit(1)
    
    async def _submit():
        from agentbus.services.multi_model_coordinator import TaskRequest, TaskType, TaskPriority
        
        task_request = TaskRequest(
            task_id="cli_task_" + datetime.now().strftime("%Y%m%d_%H%M%S"),
            task_type=TaskType(task_type),
            content=content,
            priority=TaskPriority.NORMAL,
            max_cost=max_cost
        )
        
        task_id = await cli_tool.services["multi_model_coordinator"].submit_task(task_request)
        
        click.echo(f"✅ 任务已提交: {task_id}")
        click.echo(f"   任务类型: {task_type}")
        click.echo(f"   内容: {content[:50]}...")
        if max_cost:
            click.echo(f"   最大成本: ${max_cost}")
        
        # 等待任务完成
        click.echo("⏳ 等待任务完成...")
        await asyncio.sleep(2)
        
        result = await cli_tool.services["multi_model_coordinator"].get_task_result(task_id)
        if result:
            click.echo(f"✅ 任务完成:")
            click.echo(f"   状态: {result.status.value}")
            click.echo(f"   结果: {result.final_content[:200]}...")
            click.echo(f"   处理时间: {result.total_time:.2f}秒")
            click.echo(f"   成本: ${result.total_cost:.6f}")
        else:
            click.echo("⏳ 任务仍在处理中")
    
    try:
        asyncio.run(_submit())
    except Exception as e:
        click.echo(f"❌ 提交任务失败: {e}", err=True)


@cli.group()
def stream():
    """流式响应相关命令"""
    pass


@stream.command()
@click.pass_context
def list(ctx):
    """列出活跃流"""
    cli_tool = ctx.obj.get('cli_tool')
    
    if not cli_tool or not cli_tool.initialized:
        click.echo("❌ CLI工具未初始化", err=True)
        sys.exit(1)
    
    async def _list():
        active_streams = await cli_tool.services["stream_response"].list_active_streams()
        stats = await cli_tool.services["stream_response"].get_stream_stats()
        
        click.echo("🌊 活跃流:")
        click.echo(f"   总活跃流数: {len(active_streams)}")
        click.echo(f"   处理任务数: {stats['processing_tasks']}")
        
        if active_streams:
            click.echo("   流ID列表:")
            for stream_id in active_streams[:10]:  # 只显示前10个
                click.echo(f"     - {stream_id}")
            
            if len(active_streams) > 10:
                click.echo(f"     ... 还有 {len(active_streams) - 10} 个流")
        else:
            click.echo("   当前没有活跃的流")
    
    try:
        asyncio.run(_list())
    except Exception as e:
        click.echo(f"❌ 获取流列表失败: {e}", err=True)


@stream.command()
@click.option('--content', required=True, help='流内容')
@click.option('--type', 'stream_type', default='text', help='流类型')
@click.option('--chunk-size', default=5, help='数据块大小')
@click.pass_context
def create(ctx, content, stream_type, chunk_size):
    """创建流式传输"""
    cli_tool = ctx.obj.get('cli_tool')
    
    if not cli_tool or not cli_tool.initialized:
        click.echo("❌ CLI工具未初始化", err=True)
        sys.exit(1)
    
    async def _create():
        from agentbus.services.stream_response import StreamRequest, StreamHandlerType
        
        stream_request = StreamRequest(
            stream_id="cli_stream_" + datetime.now().strftime("%Y%m%d_%H%M%S"),
            content=content,
            stream_type=stream_type,
            chunk_size=chunk_size,
            delay_ms=100
        )
        
        stream_id = await cli_tool.services["stream_response"].create_stream(
            stream_request, "websocket"
        )
        
        click.echo(f"✅ 流已创建: {stream_id}")
        click.echo(f"   类型: {stream_type}")
        click.echo(f"   内容: {content[:50]}...")
        click.echo(f"   数据块大小: {chunk_size}")
        
        # 开始流处理
        await cli_tool.services["stream_response"].start_stream_processing(
            stream_id, cli_tool.services["stream_response"].simulate_ai_response
        )
        
        click.echo("🌊 流处理已开始...")
        
        # 监控流状态
        await asyncio.sleep(3)
        
        status = await cli_tool.services["stream_response"].get_stream_status(stream_id)
        if status:
            click.echo(f"   当前状态: {status.value}")
        
        # 清理流
        await cli_tool.services["stream_response"].cancel_stream(stream_id)
        click.echo("🧹 流已清理")
    
    try:
        asyncio.run(_create())
    except Exception as e:
        click.echo(f"❌ 创建流失败: {e}", err=True)


@cli.command()
@click.option('--service', '-s', help='指定服务名称')
@click.option('--format', 'output_format', default='json', type=click.Choice(['json', 'table']), help='输出格式')
@click.pass_context
def config(ctx, service, output_format):
    """查看配置信息"""
    if service:
        if service == "hitl":
            config_data = {
                "timeout_default": getattr(settings, 'hitl_timeout_default', 30),
                "max_retry": getattr(settings, 'hitl_max_retry', 3)
            }
        elif service == "knowledge":
            config_data = {
                "file": getattr(settings, 'knowledge_bus_file', './data/knowledge_bus.json'),
                "enabled": getattr(settings, 'knowledge_enabled', True),
                "retention_days": getattr(settings, 'knowledge_retention_days', 730)
            }
        elif service == "multi_model":
            config_data = {
                "enabled": getattr(settings, 'multi_model_enabled', True),
                "max_concurrent_tasks": getattr(settings, 'multi_model_max_concurrent_tasks', 10),
                "default_timeout": getattr(settings, 'multi_model_default_timeout', 300)
            }
        elif service == "stream":
            config_data = {
                "enabled": True,  # 流处理总是启用
                "default_chunk_size": 10,
                "default_delay_ms": 50
            }
        else:
            click.echo(f"❌ 未知服务: {service}", err=True)
            sys.exit(1)
        
        if output_format == 'json':
            click.echo(json.dumps(config_data, indent=2, ensure_ascii=False))
        else:
            click.echo(f"📋 {service} 配置:")
            for key, value in config_data.items():
                click.echo(f"   {key}: {value}")
    else:
        # 显示所有配置
        config_data = {
            "app": {
                "name": settings.app_name,
                "version": settings.app_version,
                "debug": settings.debug
            },
            "server": {
                "host": settings.host,
                "port": settings.port
            },
            "hitl": {
                "timeout_default": getattr(settings, 'hitl_timeout_default', 30),
                "max_retry": getattr(settings, 'hitl_max_retry', 3)
            },
            "knowledge": {
                "file": getattr(settings, 'knowledge_bus_file', './data/knowledge_bus.json'),
                "enabled": getattr(settings, 'knowledge_enabled', True)
            },
            "multi_model": {
                "enabled": getattr(settings, 'multi_model_enabled', True),
                "max_concurrent_tasks": getattr(settings, 'multi_model_max_concurrent_tasks', 10)
            }
        }
        
        if output_format == 'json':
            click.echo(json.dumps(config_data, indent=2, ensure_ascii=False))
        else:
            click.echo("📋 AgentBus 配置:")
            for service, configs in config_data.items():
                click.echo(f"   {service}:")
                for key, value in configs.items():
                    click.echo(f"     {key}: {value}")


@cli.command()
@click.pass_context
def health(ctx):
    """健康检查"""
    cli_tool = ctx.obj.get('cli_tool')
    
    if not cli_tool or not cli_tool.initialized:
        click.echo("❌ CLI工具未初始化", err=True)
        sys.exit(1)
    
    async def _health():
        click.echo("🏥 AgentBus 健康检查")
        click.echo("=" * 30)
        
        try:
            status_data = await cli_tool.get_service_status()
            
            all_healthy = True
            for service_name, service_info in status_data.items():
                status = service_info.get('status', 'unknown')
                if status == 'running':
                    click.echo(f"✅ {service_name}: 健康")
                else:
                    click.echo(f"❌ {service_name}: {status}")
                    all_healthy = False
            
            if all_healthy:
                click.echo("\n🎉 所有服务健康状况良好")
            else:
                click.echo("\n⚠️ 部分服务存在问题")
                
        except Exception as e:
            click.echo(f"❌ 健康检查失败: {e}", err=True)
    
    try:
        asyncio.run(_health())
    except Exception as e:
        click.echo(f"❌ 执行健康检查失败: {e}", err=True)


@cli.command()
@click.pass_context
def cleanup(ctx):
    """清理资源"""
    cli_tool = ctx.obj.get('cli_tool')
    
    if not cli_tool:
        click.echo("ℹ️  CLI工具未初始化，无需清理")
        return
    
    async def _cleanup():
        click.echo("🧹 开始清理AgentBus资源...")
        await cli_tool.cleanup()
        click.echo("✅ 清理完成")
    
    try:
        asyncio.run(_cleanup())
    except Exception as e:
        click.echo(f"❌ 清理失败: {e}", err=True)


# 导入插件和渠道管理命令
from agentbus.cli.commands.plugin_commands import plugin
from agentbus.cli.commands.channel_commands import channel

# 注册插件和渠道管理命令组
cli.add_command(plugin)
cli.add_command(channel)


# 主函数
if __name__ == '__main__':
    cli()