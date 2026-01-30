"""
AgentBus Hook System Types

Defines all type specifications for the AgentBus hook system,
including metadata, events, handlers, and configuration structures.
"""

from typing import Any, Callable, Dict, List, Optional, Union, Protocol
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class HookSource(Enum):
    """Source types for hooks"""
    BUNDLED = "agentbus-bundled"       # Built-in hooks
    MANAGED = "agentbus-managed"        # User-managed hooks
    WORKSPACE = "agentbus-workspace"   # Workspace hooks
    PLUGIN = "agentbus-plugin"         # Plugin hooks
    THIRD_PARTY = "agentbus-third-party"  # External hooks


class HookEventType(Enum):
    """Core event types for the hook system"""
    COMMAND = "command"
    SESSION = "session"
    AGENT = "agent"
    GATEWAY = "gateway"
    MESSAGE = "message"
    ERROR = "error"
    LIFECYCLE = "lifecycle"
    SECURITY = "security"


@dataclass
class HookInstallSpec:
    """Specification for hook installation"""
    id: Optional[str] = None
    kind: str = "bundled"  # bundled, npm, git
    label: Optional[str] = None
    package: Optional[str] = None
    repository: Optional[str] = None
    bins: List[str] = field(default_factory=list)


@dataclass
class HookRequirements:
    """Requirements for hook execution"""
    bins: List[str] = field(default_factory=list)
    any_bins: List[str] = field(default_factory=list)
    env: List[str] = field(default_factory=list)
    config: List[str] = field(default_factory=list)
    python_version: Optional[str] = None


@dataclass
class HookMetadata:
    """Metadata for hook configuration"""
    always: bool = False
    hook_key: Optional[str] = None
    emoji: Optional[str] = None
    homepage: Optional[str] = None
    events: List[str] = field(default_factory=list)
    export: str = "default"
    os: List[str] = field(default_factory=list)
    priority: int = 0
    timeout: Optional[int] = None
    retry_count: int = 0
    requires: Optional[HookRequirements] = None
    install: List[HookInstallSpec] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"


@dataclass
class HookInvocationPolicy:
    """Policy for hook invocation"""
    enabled: bool = True
    priority: int = 0
    timeout: Optional[int] = None
    retry_count: int = 0
    fail_silent: bool = False


@dataclass
class HookExecutionContext:
    """Context for hook execution"""
    session_key: str
    agent_id: Optional[str] = None
    channel_id: Optional[str] = None
    user_id: Optional[str] = None
    workspace_dir: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    environment: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HookEvent:
    """Event structure for hook triggers"""
    type: HookEventType
    action: str
    session_key: str
    context: HookExecutionContext
    timestamp: datetime = field(default_factory=datetime.now)
    messages: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "agentbus"


@dataclass
class HookResult:
    """Result from hook execution"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    messages: List[str] = field(default_factory=list)
    error: Optional[str] = None
    execution_time: float = 0.0
    warnings: List[str] = field(default_factory=list)


class HookHandler(Protocol):
    """Protocol for hook handler functions"""
    async def __call__(self, event: HookEvent) -> HookResult:
        ...


@dataclass
class Hook:
    """Hook definition"""
    name: str
    description: str
    source: HookSource
    plugin_id: Optional[str] = None
    file_path: str = ""
    base_dir: str = ""
    handler_path: str = ""


@dataclass
class HookEntry:
    """Complete hook entry with metadata"""
    hook: Hook
    frontmatter: Dict[str, str] = field(default_factory=dict)
    metadata: Optional[HookMetadata] = None
    invocation: Optional[HookInvocationPolicy] = None


@dataclass
class HookEligibilityContext:
    """Context for determining hook eligibility"""
    remote: Optional[Dict[str, Any]] = None
    platform: str = ""
    has_bin: Optional[Callable[[str], bool]] = None
    has_any_bin: Optional[Callable[[List[str]], bool]] = None


@dataclass
class HookSnapshot:
    """Snapshot of hook state"""
    hooks: List[Dict[str, Any]] = field(default_factory=list)
    resolved_hooks: List[Hook] = field(default_factory=list)
    version: int = 1
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class HookStatistics:
    """Statistics for hook system"""
    total_hooks: int = 0
    enabled_hooks: int = 0
    executed_hooks: int = 0
    successful_hooks: int = 0
    failed_hooks: int = 0
    average_execution_time: float = 0.0
    last_execution: Optional[datetime] = None


# Type aliases for common use cases
HookEventHandler = HookHandler
HookFilter = Callable[[HookEntry], bool]
HookProcessor = Callable[[HookEvent, List[HookEntry]], List[HookResult]]