import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uuid

class Message(BaseModel):
    role: str
    content: str
    timestamp: float = 0.0

class Session:
    def __init__(self, session_id: str, cwd: str):
        self.session_id = session_id
        self.cwd = cwd
        self.history: List[Dict[str, Any]] = [] # OpenAI 的原始消息
        self.env_vars: Dict[str, str] = os.environ.copy()
        
    def add_message(self, role: str, content: Optional[str], **kwargs):
        """
        Add a message to history.
        kwargs can include 'tool_calls', 'function_call', 'name', 'tool_call_id' etc.
        """
        msg = {"role": role, "content": content}
        msg.update(kwargs)
        self.history.append(msg)

    def update_cwd(self, new_cwd: str):
        if os.path.isabs(new_cwd):
            self.cwd = new_cwd
        else:
            self.cwd = os.path.abspath(os.path.join(self.cwd, new_cwd))

_sessions: Dict[str, Session] = {}

def get_session(session_id: str) -> Optional[Session]:
    return _sessions.get(session_id)

def create_session(cwd: str = None) -> Session:
    if cwd is None:
        cwd = os.getcwd()
    session_id = str(uuid.uuid4())
    session = Session(session_id, cwd)
    _sessions[session_id] = session
    return session
