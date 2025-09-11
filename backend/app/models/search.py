from datetime import datetime
from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field
from enum import Enum

class SearchStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"

class StepType(str, Enum):
    PLAN = "plan"
    SEARCH = "search"
    CODE = "code"
    LLM = "llm"
    SOLVE = "solve"
    REPLAN = "replan"

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# Source Models
class SourceInfo(BaseModel):
    title: str
    link: str
    snippet: Optional[str] = None

# Request Models
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="The search query")

class CancelSearchRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for cancellation")

# Response Models
class SearchResponse(BaseModel):
    search_id: str = Field(..., description="Unique identifier for the search")
    status: Literal["started"] = "started"
    message: str = "Search initiated"

class SearchStatusResponse(BaseModel):
    search_id: str
    status: SearchStatus
    current_step: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage")

class NewChatResponse(BaseModel):
    status: Literal["reset"] = "reset"
    message: str = "Previous session cleared"

class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    version: str
    timestamp: datetime
    uptime_seconds: float

class CancelResponse(BaseModel):
    status: Literal["cancelled"] = "cancelled"
    message: str = "Search cancelled successfully"

# Step Models
class StepMetadata(BaseModel):
    search_query: Optional[str] = Field(None, alias="searchQuery")
    code_result: Optional[str] = Field(None, alias="codeResult")
    llm_result: Optional[str] = Field(None, alias="llmResult")
    plan_steps: Optional[List[str]] = Field(None, alias="planSteps")
    error: Optional[str] = None
    execution_time: Optional[float] = Field(None, alias="executionTime")
    sources: Optional[List[Union[str, SourceInfo]]] = None
    
    model_config = {"populate_by_name": True}

class ThinkingStep(BaseModel):
    id: str
    type: StepType
    status: StepStatus
    title: str
    content: Optional[str] = ""
    timestamp: datetime
    metadata: Optional[StepMetadata] = None

class SearchResult(BaseModel):
    id: str
    query: str
    status: SearchStatus
    steps: List[ThinkingStep] = []
    final_answer: Optional[str] = None
    sources: Optional[List[SourceInfo]] = []
    start_time: datetime
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None

# Error Models
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    timestamp: datetime
    search_id: Optional[str] = None
