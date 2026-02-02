"""
WebExplorer Agent FSM - 有限状态机
"""

import logging
from typing import Dict, Callable, Optional
from .types import ExplorerState


logger = logging.getLogger(__name__)


class ExplorerFSM:
    """WebExplorer状态机"""
    
    def __init__(self):
        self.current_state = ExplorerState.IDLE
        self.previous_state: Optional[ExplorerState] = None
        
        # 状态转换表
        self.transitions: Dict[ExplorerState, list] = {
            ExplorerState.IDLE: [
                ExplorerState.LOCATING,
                ExplorerState.TESTING,
                ExplorerState.COMPLETED
            ],
            ExplorerState.LOCATING: [
                ExplorerState.ANALYZING,
                ExplorerState.DECIDING,
                ExplorerState.ERROR
            ],
            ExplorerState.ANALYZING: [
                ExplorerState.DECIDING,
                ExplorerState.ERROR
            ],
            ExplorerState.DECIDING: [
                ExplorerState.ACTING,
                ExplorerState.BACKTRACKING,
                ExplorerState.COMPLETED,
                ExplorerState.ERROR
            ],
            ExplorerState.ACTING: [
                ExplorerState.REFLECTING,
                ExplorerState.ERROR
            ],
            ExplorerState.REFLECTING: [
                ExplorerState.LOCATING,
                ExplorerState.BACKTRACKING,
                ExplorerState.ERROR
            ],
            ExplorerState.BACKTRACKING: [
                ExplorerState.LOCATING,
                ExplorerState.DECIDING,
                ExplorerState.COMPLETED,
                ExplorerState.ERROR
            ],
            ExplorerState.TESTING: [
                ExplorerState.TELEPORTING,
                ExplorerState.COMPLETED,
                ExplorerState.ERROR
            ],
            ExplorerState.TELEPORTING: [
                ExplorerState.TESTING,
                ExplorerState.ERROR
            ],
            ExplorerState.ERROR: [
                ExplorerState.IDLE,
                ExplorerState.COMPLETED
            ],
            ExplorerState.COMPLETED: []
        }
    
    def can_transition(self, to_state: ExplorerState) -> bool:
        """检查是否可以转换到目标状态"""
        allowed_states = self.transitions.get(self.current_state, [])
        return to_state in allowed_states
    
    def transition(self, to_state: ExplorerState) -> bool:
        """执行状态转换"""
        if not self.can_transition(to_state):
            logger.warning(
                f"无效的状态转换: {self.current_state.value} -> {to_state.value}"
            )
            return False
        
        logger.info(f"状态转换: {self.current_state.value} -> {to_state.value}")
        self.previous_state = self.current_state
        self.current_state = to_state
        return True
    
    def reset(self):
        """重置状态机"""
        self.current_state = ExplorerState.IDLE
        self.previous_state = None
        logger.info("状态机已重置")
