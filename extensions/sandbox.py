"""
AgentBus扩展沙箱
AgentBus Extension Sandbox

扩展沙箱为扩展提供安全的执行环境，限制扩展的访问权限和资源使用，
确保系统的安全性和稳定性。

The Extension Sandbox provides a secure execution environment for extensions,
limiting access permissions and resource usage to ensure system security
and stability.

Author: MiniMax Agent
License: MIT
"""

import asyncio
import logging
import os
import sys
import time
import threading
try:
    import resource
except ImportError:
    resource = None
import tempfile
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Set, Callable, Union
from dataclasses import dataclass
from contextlib import contextmanager
from unittest.mock import Mock, patch
import importlib.util
import ast

from .base import Extension, ExtensionId, ExtensionSandboxInterface, ExtensionSecurityError


@dataclass
class ResourceLimits:
    """资源限制配置"""
    max_memory: int = 128 * 1024 * 1024  # 128MB
    max_cpu_time: float = 30.0  # 30秒
    max_file_descriptors: int = 256
    max_processes: int = 5
    max_threads: int = 10
    allowed_directories: List[str] = None
    forbidden_apis: List[str] = None
    
    def __post_init__(self):
        if self.allowed_directories is None:
            self.allowed_directories = []
        if self.forbidden_apis is None:
            self.forbidden_apis = [
                'subprocess.call', 'subprocess.run', 'subprocess.Popen',
                'os.system', 'os.exec', 'os.spawn',
                'eval', 'exec', 'compile'
            ]


@dataclass
class SecurityPolicy:
    """安全策略配置"""
    level: str = "strict"  # permissive, moderate, strict, maximum
    allow_network: bool = False
    allow_file_system: bool = True
    allow_subprocess: bool = False
    allow_dynamic_import: bool = False
    allowed_modules: Set[str] = None
    forbidden_modules: Set[str] = None
    
    def __post_init__(self):
        if self.allowed_modules is None:
            self.allowed_modules = set()
        if self.forbidden_modules is None:
            self.forbidden_modules = {
                'os', 'sys', 'subprocess', 'socket', 'urllib',
                'requests', 'http', 'ftplib', 'telnetlib'
            }


class ExtensionSandbox(ExtensionSandboxInterface):
    """扩展沙箱实现"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._logger = logging.getLogger("extension.sandbox")
        self._config = config or {}
        
        # 默认资源限制
        self._default_limits = ResourceLimits(
            max_memory=128 * 1024 * 1024,  # 128MB
            max_cpu_time=30.0,
            max_file_descriptors=256,
            max_processes=5,
            max_threads=10
        )
        
        # 默认安全策略
        self._default_policy = SecurityPolicy(
            level="strict",
            allow_network=False,
            allow_file_system=True,
            allow_subprocess=False,
            allowed_modules=set(),
            forbidden_modules={
                'os', 'sys', 'subprocess', 'socket', 'urllib',
                'requests', 'http', 'ftplib', 'telnetlib'
            }
        )
        
        # 扩展资源限制映射
        self._extension_limits: Dict[ExtensionId, ResourceLimits] = {}
        self._extension_policies: Dict[ExtensionId, SecurityPolicy] = {}
        
        # 活动执行会话
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._session_lock = threading.Lock()
        
        # 安全监控
        self._security_violations: List[Dict[str, Any]] = []
        self._execution_history: List[Dict[str, Any]] = []
        
        self._logger.info("扩展沙箱初始化完成")
    
    def execute_in_sandbox(
        self, 
        extension: Extension, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """在沙箱中执行函数"""
        session_id = f"{extension.id}_{int(time.time())}"
        
        try:
            with self._create_execution_session(extension, session_id):
                # 验证执行权限
                if not self.check_security(extension):
                    raise ExtensionSecurityError(f"扩展 {extension.id} 安全检查失败")
                
                # 设置资源限制
                limits = self.get_resource_limits(extension)
                
                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    # 异步函数
                    return asyncio.run(self._execute_with_limits(
                        extension, func, limits, *args, **kwargs
                    ))
                else:
                    # 同步函数
                    return self._execute_with_limits(
                        extension, func, limits, *args, **kwargs
                    )
                    
        except Exception as e:
            self._logger.error(f"沙箱执行失败 {extension.id}: {e}")
            raise
        finally:
            self._cleanup_session(session_id)
    
    async def _execute_with_limits(
        self, 
        extension: Extension, 
        func: Callable, 
        limits: ResourceLimits,
        *args, 
        **kwargs
    ) -> Any:
        """在资源限制下执行函数"""
        start_time = time.time()
        
        # 设置资源限制
        self._set_resource_limits(limits)
        
        try:
            # 执行函数
            result = func(*args, **kwargs)
            
            # 检查执行时间
            execution_time = time.time() - start_time
            if execution_time > limits.max_cpu_time:
                raise ExtensionSecurityError(
                    f"扩展 {extension.id} 执行超时: {execution_time:.2f}s"
                )
            
            # 记录执行历史
            self._record_execution(extension, func, execution_time, True, None)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._record_execution(extension, func, execution_time, False, str(e))
            raise
        finally:
            # 清理资源限制
            self._cleanup_resource_limits()
    
    def check_security(self, extension: Extension) -> bool:
        """安全检查"""
        try:
            policy = self.get_security_policy(extension)
            
            # 检查扩展代码安全性
            if not self._check_code_security(extension):
                self._logger.warning(f"扩展 {extension.id} 代码安全检查失败")
                return False
            
            # 检查资源访问权限
            if not self._check_resource_access(extension, policy):
                self._logger.warning(f"扩展 {extension.id} 资源访问检查失败")
                return False
            
            # 检查模块导入权限
            if not self._check_module_access(extension, policy):
                self._logger.warning(f"扩展 {extension.id} 模块访问检查失败")
                return False
            
            return True
            
        except Exception as e:
            self._logger.error(f"安全检查失败 {extension.id}: {e}")
            return False
    
    def _check_code_security(self, extension: Extension) -> bool:
        """检查扩展代码安全性"""
        try:
            # 检查扩展源码中的危险操作
            source_code = self._get_extension_source_code(extension)
            if not source_code:
                return True
            
            # 解析AST检查危险操作
            tree = ast.parse(source_code)
            
            dangerous_patterns = [
                'eval(', 'exec(', '__import__', 'open(', 'file(',
                'subprocess', 'os.system', 'os.popen'
            ]
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in ['eval', 'exec', '__import__']:
                            self._record_security_violation(
                                extension, f"Dangerous function: {func_name}"
                            )
                            return False
                    
                    elif isinstance(node.func, ast.Attribute):
                        attr_name = f"{node.func.value.id}.{node.func.attr}" if hasattr(node.func.value, 'id') else str(node.func.attr)
                        if any(pattern in attr_name for pattern in ['subprocess', 'os.system', 'os.popen']):
                            self._record_security_violation(
                                extension, f"Dangerous API call: {attr_name}"
                            )
                            return False
            
            return True
            
        except Exception as e:
            self._logger.error(f"代码安全检查失败 {extension.id}: {e}")
            return False
    
    def _check_resource_access(self, extension: Extension, policy: SecurityPolicy) -> bool:
        """检查资源访问权限"""
        try:
            # 检查网络访问
            if not policy.allow_network:
                # 模拟检查网络访问（实际实现中需要更复杂的监控）
                pass
            
            # 检查文件系统访问
            if not policy.allow_file_system:
                # 模拟检查文件系统访问
                pass
            
            return True
            
        except Exception as e:
            self._logger.error(f"资源访问检查失败 {extension.id}: {e}")
            return False
    
    def _check_module_access(self, extension: Extension, policy: SecurityPolicy) -> bool:
        """检查模块访问权限"""
        try:
            # 检查是否导入了禁止的模块
            forbidden_found = policy.forbidden_modules.intersection(
                self._get_imported_modules(extension)
            )
            
            if forbidden_found:
                self._record_security_violation(
                    extension, f"Forbidden modules imported: {forbidden_found}"
                )
                return False
            
            return True
            
        except Exception as e:
            self._logger.error(f"模块访问检查失败 {extension.id}: {e}")
            return False
    
    def set_resource_limits(self, extension: Extension, **limits) -> bool:
        """设置资源限制"""
        try:
            current_limits = self._extension_limits.get(extension.id, self._default_limits)
            
            # 更新限制
            for key, value in limits.items():
                if hasattr(current_limits, key):
                    setattr(current_limits, key, value)
            
            self._extension_limits[extension.id] = current_limits
            self._logger.debug(f"为扩展 {extension.id} 设置资源限制: {limits}")
            return True
            
        except Exception as e:
            self._logger.error(f"设置资源限制失败 {extension.id}: {e}")
            return False
    
    def get_resource_limits(self, extension: Extension) -> ResourceLimits:
        """获取资源限制"""
        return self._extension_limits.get(extension.id, self._default_limits)
    
    def set_security_policy(self, extension: Extension, policy: SecurityPolicy):
        """设置安全策略"""
        self._extension_policies[extension.id] = policy
        self._logger.debug(f"为扩展 {extension.id} 设置安全策略: {policy.level}")
    
    def get_security_policy(self, extension: Extension) -> SecurityPolicy:
        """获取安全策略"""
        return self._extension_policies.get(extension.id, self._default_policy)
    
    def monitor_execution(self, extension: Extension) -> Dict[str, Any]:
        """监控执行"""
        return {
            "security_violations": [
                v for v in self._security_violations 
                if v.get("extension_id") == extension.id
            ],
            "execution_history": [
                h for h in self._execution_history 
                if h.get("extension_id") == extension.id
            ],
            "current_limits": self.get_resource_limits(extension).__dict__,
            "current_policy": self.get_security_policy(extension).__dict__
        }
    
    def _get_extension_source_code(self, extension: Extension) -> Optional[str]:
        """获取扩展源码"""
        try:
            # 尝试从文件系统获取源码
            if hasattr(extension, '_file_path') and extension._file_path:
                with open(extension._file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # 尝试从模块获取
            if hasattr(extension, '__module__'):
                module = sys.modules.get(extension.__module__)
                if module and hasattr(module, '__file__'):
                    with open(module.__file__, 'r', encoding='utf-8') as f:
                        return f.read()
            
            return None
            
        except Exception as e:
            self._logger.debug(f"获取扩展源码失败 {extension.id}: {e}")
            return None
    
    def _get_imported_modules(self, extension: Extension) -> Set[str]:
        """获取扩展导入的模块"""
        try:
            imported_modules = set()
            
            if hasattr(extension, '__module__'):
                module = sys.modules.get(extension.__module__)
                if module:
                    # 简化的模块导入检测
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if hasattr(attr, '__module__'):
                            imported_modules.add(attr.__module__)
            
            return imported_modules
            
        except Exception as e:
            self._logger.debug(f"获取导入模块失败 {extension.id}: {e}")
            return set()
    
    def _record_security_violation(self, extension: Extension, violation: str):
        """记录安全违规"""
        violation_record = {
            "extension_id": extension.id,
            "extension_name": extension.name,
            "violation": violation,
            "timestamp": time.time(),
            "policy_level": self.get_security_policy(extension).level
        }
        
        self._security_violations.append(violation_record)
        
        # 保持记录大小
        if len(self._security_violations) > 1000:
            self._security_violations = self._security_violations[-500:]
        
        self._logger.warning(f"安全违规 [{extension.id}]: {violation}")
    
    def _record_execution(
        self, 
        extension: Extension, 
        func: Callable, 
        execution_time: float, 
        success: bool, 
        error: Optional[str]
    ):
        """记录执行历史"""
        execution_record = {
            "extension_id": extension.id,
            "extension_name": extension.name,
            "function": func.__name__ if hasattr(func, '__name__') else str(func),
            "execution_time": execution_time,
            "success": success,
            "error": error,
            "timestamp": time.time()
        }
        
        self._execution_history.append(execution_record)
        
        # 保持记录大小
        if len(self._execution_history) > 1000:
            self._execution_history = self._execution_history[-500:]
    
    def _create_execution_session(self, extension: Extension, session_id: str):
        """创建执行会话"""
        session = {
            "extension_id": extension.id,
            "start_time": time.time(),
            "resource_usage": {},
            "thread_id": threading.get_ident()
        }
        
        with self._session_lock:
            self._active_sessions[session_id] = session
        
        return self._session_context_manager(session_id)
    
    def _session_context_manager(self, session_id: str):
        """会话上下文管理器"""
        @contextmanager
        def session_context():
            try:
                yield
            finally:
                self._cleanup_session(session_id)
        
        return session_context()
    
    def _cleanup_session(self, session_id: str):
        """清理会话"""
        with self._session_lock:
            self._active_sessions.pop(session_id, None)
    
    def _set_resource_limits(self, limits: ResourceLimits):
        """设置系统资源限制"""
        if resource is None:
            return

        try:
            # 设置内存限制
            resource.setrlimit(resource.RLIMIT_AS, (limits.max_memory, limits.max_memory))
            
            # 设置CPU时间限制
            resource.setrlimit(resource.RLIMIT_CPU, (int(limits.max_cpu_time), int(limits.max_cpu_time)))
            
            # 设置文件描述符限制
            resource.setrlimit(resource.RLIMIT_NOFILE, (limits.max_file_descriptors, limits.max_file_descriptors))
            
        except Exception as e:
            self._logger.warning(f"设置资源限制失败: {e}")
    
    def _cleanup_resource_limits(self):
        """清理资源限制"""
        if resource is None:
            return

        try:
            # 恢复默认限制
            resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
            resource.setrlimit(resource.RLIMIT_CPU, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
            resource.setrlimit(resource.RLIMIT_NOFILE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
            
        except Exception as e:
            self._logger.warning(f"清理资源限制失败: {e}")
    
    def create_safe_environment(self, extension: Extension) -> Dict[str, Any]:
        """创建安全的执行环境"""
        policy = self.get_security_policy(extension)
        
        # 创建安全的globals
        safe_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round,
                "isinstance": isinstance,
                "hasattr": hasattr,
                "getattr": getattr,
                "setattr": setattr,
                "type": type,
                "callable": callable
            },
            "__name__": f"extension_{extension.id}",
            "extension_id": extension.id,
            "extension_name": extension.name
        }
        
        # 添加允许的模块
        if policy.allowed_modules:
            for module_name in policy.allowed_modules:
                try:
                    safe_globals[module_name] = __import__(module_name)
                except ImportError:
                    pass
        
        return safe_globals
    
    def get_security_report(self) -> Dict[str, Any]:
        """获取安全报告"""
        return {
            "total_violations": len(self._security_violations),
            "total_executions": len(self._execution_history),
            "recent_violations": self._security_violations[-10:],
            "recent_executions": self._execution_history[-10:],
            "violations_by_extension": {},
            "execution_stats_by_extension": {}
        }
    
    def clear_security_logs(self):
        """清理安全日志"""
        self._security_violations.clear()
        self._execution_history.clear()
        self._logger.info("安全日志已清理")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup_all_sessions()
    
    def _cleanup_all_sessions(self):
        """清理所有会话"""
        with self._session_lock:
            self._active_sessions.clear()
        self._logger.info("所有沙箱会话已清理")