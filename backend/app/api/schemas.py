from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    QUERY = "query"
    RESULT = "result"


class DatabaseType(str, Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"
    MONGODB = "mongodb"


class QueryType(str, Enum):
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    AGGREGATE = "aggregate"
    ANALYTICS = "analytics"
    UNKNOWN = "unknown"


class Message(BaseModel):
    type: MessageType
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    stream: bool = False
    context: Optional[List[Message]] = None


class ChartConfig(BaseModel):
    """Chart configuration"""
    type: str  # bar, line, pie, etc.
    title: str
    labels: List[str]
    datasets: List[Dict[str, Any]]
    options: Optional[Dict[str, Any]] = None
    
    class Config:
        # Allow extra fields in case chart generator adds more properties
        extra = "allow"

class ChatResponse(BaseModel):
    response: str
    query_used: Optional[str] = None
    data: Optional[Any] = None
    insights: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None
    processing_time: Optional[float] = None
    chart: Optional[ChartConfig] = None  # This should accept ChartConfig
    
    class Config:
        # Allow extra fields to accommodate chart data
        extra = "allow"

class DatabaseConfig(BaseModel):
    database_type: DatabaseType
    connection_url: str
    database_name: Optional[str] = None


class QueryAnalysis(BaseModel):
    intent: str
    query_type: QueryType
    confidence: float = Field(ge=0.0, le=1.0)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    suggested_query: Optional[str] = None
    safety_level: str = Field(default="safe")  # safe, warning, dangerous


class DatabaseSchema(BaseModel):
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    collections: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentStatus(BaseModel):
    agent_ready: bool
    database_connected: bool
    database_type: str
    chatgpt_available: bool
    last_updated: Optional[datetime] = None
    active_sessions: int = 0


class StreamingChunk(BaseModel):
    chunk: str
    is_final: bool = False
    metadata: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    error: str
    details: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None