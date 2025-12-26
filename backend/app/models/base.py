from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func

# SQLAlchemy Base
SQLBase = declarative_base()

# Pydantic Base Models
class BaseModelSchema(BaseModel):
    """Base Pydantic model with common configurations"""
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

class TimeStampedModel(BaseModelSchema):
    """Base model with created_at and updated_at timestamps"""
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class BaseSQLModel:
    """Base SQLAlchemy model with common columns"""
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class BaseMongoModel(BaseModelSchema):
    """Base MongoDB model with common fields"""
    id: Optional[str] = Field(None, alias="_id")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

class PaginationParams(BaseModelSchema):
    """Pagination parameters"""
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = Field("desc", pattern="^(asc|desc)$")

class FilterParams(BaseModelSchema):
    """Filter parameters for queries"""
    field: str
    operator: str = Field("=", pattern="^(=|!=|>|<|>=|<=|like|in)$")
    value: Any

class SearchParams(BaseModelSchema):
    """Search parameters"""
    query: str
    fields: Optional[list[str]] = None
    case_sensitive: bool = False

class ResponseModel(BaseModelSchema):
    """Base response model"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None
    pagination: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModelSchema):
    """Health check response"""
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database_connected: bool
    database_type: str
    agent_ready: bool
    chatgpt_available: bool

class DatabaseSchemaResponse(BaseModelSchema):
    """Database schema response"""
    tables: list[Dict[str, Any]] = []
    collections: list[Dict[str, Any]] = []
    relationships: list[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}