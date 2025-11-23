"""
Pydantic models for Claude Code Web interface.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    TEXT = "text"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    STATUS = "status"


class SessionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"


class Message(BaseModel):
    """A single message in a conversation."""
    id: str = Field(default_factory=lambda: datetime.now().isoformat())
    role: MessageRole
    content: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class Conversation(BaseModel):
    """A conversation session with Claude Code."""
    id: str
    workspace: str
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: SessionStatus = SessionStatus.IDLE


class ChatRequest(BaseModel):
    """Request to send a message to Claude Code."""
    message: str
    workspace: str = "."
    conversation_id: Optional[str] = None
    stream: bool = True


class ChatResponse(BaseModel):
    """Response from Claude Code."""
    conversation_id: str
    message: Message
    status: SessionStatus


class WorkspaceInfo(BaseModel):
    """Information about a workspace."""
    path: str
    name: str
    is_git_repo: bool = False
    git_branch: Optional[str] = None
    files_count: int = 0


class SystemInfo(BaseModel):
    """System information."""
    claude_code_version: Optional[str] = None
    claude_code_installed: bool = False
    python_version: str
    platform: str
    working_directory: str


class StreamChunk(BaseModel):
    """A chunk of streaming response."""
    type: str  # "text", "tool_use", "tool_result", "status", "error", "done"
    content: str
    conversation_id: str
    metadata: Optional[Dict[str, Any]] = None


class ToolExecution(BaseModel):
    """Information about a tool execution."""
    tool_name: str
    input: Dict[str, Any]
    output: Optional[str] = None
    status: str = "pending"  # pending, running, completed, error
    timestamp: datetime = Field(default_factory=datetime.now)


class ProjectConfig(BaseModel):
    """Configuration for a project."""
    workspace: str
    allowed_tools: List[str] = []
    denied_tools: List[str] = []
    auto_approve: bool = False
    max_turns: int = 50
