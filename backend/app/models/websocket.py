from datetime import datetime
from typing import Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field
from .search import StepType, StepStatus, StepMetadata

class WebSocketMessage(BaseModel):
    type: str
    timestamp: datetime
    data: Dict[str, Any]
    search_id: Optional[str] = None

class StepUpdateData(BaseModel):
    step_id: str
    step_type: StepType
    status: StepStatus
    title: str
    content: Optional[str] = ""
    metadata: Optional[StepMetadata] = None

class StepUpdateMessage(WebSocketMessage):
    type: Literal["step_update"] = "step_update"
    data: StepUpdateData

class SearchCompleteData(BaseModel):
    search_id: str
    result: str
    total_steps: int
    duration: float
    final_answer: str

class SearchCompleteMessage(WebSocketMessage):
    type: Literal["search_complete"] = "search_complete"
    data: SearchCompleteData

class ErrorData(BaseModel):
    error: str
    step_id: Optional[str] = None
    recoverable: bool = True
    error_code: Optional[str] = None

class ErrorMessage(WebSocketMessage):
    type: Literal["error"] = "error"
    data: ErrorData

class SessionResetData(BaseModel):
    message: str = "Session has been reset"
    reason: Optional[str] = None

class SessionResetMessage(WebSocketMessage):
    type: Literal["session_reset"] = "session_reset"
    data: SessionResetData

class ConnectionData(BaseModel):
    connected: bool
    client_id: str
    server_time: datetime

class ConnectionMessage(WebSocketMessage):
    type: Literal["connection"] = "connection"
    data: ConnectionData

class HeartbeatData(BaseModel):
    server_time: datetime
    client_count: int

class HeartbeatMessage(WebSocketMessage):
    type: Literal["heartbeat"] = "heartbeat"
    data: HeartbeatData

# Union type for all possible WebSocket messages
WSMessage = Union[
    StepUpdateMessage,
    SearchCompleteMessage,
    ErrorMessage,
    SessionResetMessage,
    ConnectionMessage,
    HeartbeatMessage
]
