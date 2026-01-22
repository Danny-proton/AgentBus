"""
成本追踪服务
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from config.settings import get_model_config


logger = logging.getLogger(__name__)


@dataclass
class CostRecord:
    """成本记录"""
    timestamp: datetime
    model: str
    prompt_tokens: int
    completion_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    session_id: Optional[str] = None


@dataclass
class ModelCost:
    """模型成本统计"""
    total_cost: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    request_count: int = 0
    last_used: Optional[datetime] = None


class CostTracker:
    """
    成本追踪器
    追踪所有 API 调用的 token 使用和成本
    """
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._records: list[CostRecord] = []
        self._model_stats: Dict[str, ModelCost] = defaultdict(lambda: ModelCost())
        self._session_costs: Dict[str, float] = defaultdict(float)
    
    async def record(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        input_cost: float,
        output_cost: float,
        session_id: Optional[str] = None
    ) -> CostRecord:
        """
        记录一次 API 调用
        
        Args:
            model: 模型名称
            prompt_tokens: 输入 token 数
            completion_tokens: 输出 token 数
            input_cost: 输入成本
            output_cost: 输出成本
            session_id: 会话 ID
        
        Returns:
            CostRecord: 成本记录
        """
        async with self._lock:
            total_cost = input_cost + output_cost
            
            record = CostRecord(
                timestamp=datetime.now(),
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost,
                session_id=session_id
            )
            
            self._records.append(record)
            
            # 更新模型统计
            stats = self._model_stats[model]
            stats.total_cost += total_cost
            stats.prompt_tokens += prompt_tokens
            stats.completion_tokens += completion_tokens
            stats.request_count += 1
            stats.last_used = datetime.now()
            
            # 更新会话成本
            if session_id:
                self._session_costs[session_id] += total_cost
            
            logger.debug(
                f"Cost recorded: model={model}, tokens=({prompt_tokens}+{completion_tokens}), "
                f"cost=${total_cost:.4f}"
            )
            
            return record
    
    async def get_session_cost(self, session_id: str) -> float:
        """获取会话成本"""
        return self._session_costs.get(session_id, 0.0)
    
    async def get_total_cost(self) -> float:
        """获取总成本"""
        return sum(record.total_cost for record in self._records)
    
    async def get_model_cost(self, model: str) -> Optional[ModelCost]:
        """获取模型成本统计"""
        stats = self._model_stats.get(model)
        
        if stats:
            return stats
        
        return None
    
    async def get_all_model_costs(self) -> Dict[str, ModelCost]:
        """获取所有模型成本统计"""
        return dict(self._model_stats)
    
    async def get_cost_summary(
        self,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取成本汇总
        
        Args:
            session_id: 可选会话 ID
        
        Returns:
            Dict: 成本汇总信息
        """
        async with self._lock:
            if session_id:
                total_cost = self._session_costs.get(session_id, 0.0)
                
                # 过滤会话记录
                session_records = [
                    r for r in self._records 
                    if r.session_id == session_id
                ]
                
                by_model = {}
                for record in session_records:
                    if record.model not in by_model:
                        by_model[record.model] = ModelCost()
                    
                    stats = by_model[record.model]
                    stats.total_cost += record.total_cost
                    stats.prompt_tokens += record.prompt_tokens
                    stats.completion_tokens += record.completion_tokens
                    stats.request_count += 1
                    stats.last_used = record.timestamp
            
            else:
                total_cost = sum(r.total_cost for r in self._records)
                by_model = dict(self._model_stats)
            
            # 构建响应
            summary = {
                "total_cost": round(total_cost, 6),
                "by_model": {},
                "request_count": len(self._records)
            }
            
            for model_name, stats in by_model.items():
                model_config = get_model_config(model_name)
                provider = model_config.provider if model_config else "unknown"
                
                summary["by_model"][model_name] = {
                    "provider": provider,
                    "total_cost": round(stats.total_cost, 6),
                    "prompt_tokens": stats.prompt_tokens,
                    "completion_tokens": stats.completion_tokens,
                    "total_tokens": stats.prompt_tokens + stats.completion_tokens,
                    "request_count": stats.request_count,
                    "last_used": stats.last_used.isoformat() if stats.last_used else None
                }
            
            return summary
    
    async def get_token_usage(
        self,
        session_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        获取 token 使用统计
        
        Args:
            session_id: 可选会话 ID
        
        Returns:
            Dict: token 统计
        """
        async with self._lock:
            if session_id:
                records = [
                    r for r in self._records 
                    if r.session_id == session_id
                ]
            else:
                records = self._records
            
            return {
                "prompt_tokens": sum(r.prompt_tokens for r in records),
                "completion_tokens": sum(r.completion_tokens for r in records),
                "total_tokens": sum(
                    r.prompt_tokens + r.completion_tokens 
                    for r in records
                )
            }
    
    async def export_records(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[dict]:
        """
        导出成本记录
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            list[dict]: 记录列表
        """
        async with self._lock:
            records = self._records
            
            if start_date:
                records = [r for r in records if r.timestamp >= start_date]
            
            if end_date:
                records = [r for r in records if r.timestamp <= end_date]
            
            return [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "model": r.model,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "input_cost": r.input_cost,
                    "output_cost": r.output_cost,
                    "total_cost": r.total_cost,
                    "session_id": r.session_id
                }
                for r in records
            ]
    
    async def clear_session(self, session_id: str):
        """清除会话成本记录"""
        async with self._lock:
            # 清除记录
            self._records = [
                r for r in self._records 
                if r.session_id != session_id
            ]
            
            # 重置会话成本
            if session_id in self._session_costs:
                del self._session_costs[session_id]
    
    async def reset(self):
        """重置所有成本记录"""
        async with self._lock:
            self._records.clear()
            self._model_stats.clear()
            self._session_costs.clear()
            
            logger.info("Cost tracker reset")
