from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
import json
import asyncio
import re
from typing import List, Optional

from app.api.schemas import (
    ChatRequest, ChatResponse, DatabaseConfig, 
    QueryAnalysis, DatabaseSchema, AgentStatus
)
from app.core.agent import AgentManager
from app.core.database import DatabaseManager
from app.services.chatgpt import ChatGPTService
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["agent"])

# Global manager instances
agent_manager: Optional[AgentManager] = None
db_manager: Optional[DatabaseManager] = None
chatgpt_service: Optional[ChatGPTService] = None


def get_agent_manager():
    global agent_manager
    if not agent_manager:
        # Try to import from main if not available
        try:
            from app.main import agent_manager as main_agent_manager
            if main_agent_manager:
                agent_manager = main_agent_manager
                return agent_manager
        except ImportError:
            pass
        
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return agent_manager


def get_db_manager():
    global db_manager
    if not db_manager:
        # Try to import from main if not available
        try:
            from app.main import db_manager as main_db_manager
            if main_db_manager:
                db_manager = main_db_manager
                return db_manager
        except ImportError:
            pass
        
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db_manager


def get_chatgpt_service():
    if not chatgpt_service:
        raise HTTPException(status_code=503, detail="ChatGPT service not initialized")
    return chatgpt_service


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    manager: AgentManager = Depends(get_agent_manager)
):
    """Process natural language queries with intelligent response"""
    try:
        # Make sure manager is properly initialized
        if manager is None:
            raise HTTPException(status_code=503, detail="Agent manager not available")
            
        response = await manager.process_query(
            query=request.query,
            session_id=request.session_id,
            stream=request.stream
        )
        
        # Create response with ALL fields including chart
        chat_response = {
            "response": response["answer"],
            "query_used": response.get("query", ""),
            "data": response.get("data"),
            "insights": response.get("insights", []),
            "suggestions": response.get("suggestions", []),
            "session_id": request.session_id
        }
        
        # IMPORTANT: Add chart to response if it exists
        if "chart" in response:
            chart_data = response["chart"]
            # Clean the chart data - remove any functions
            if isinstance(chart_data, dict):
                # Remove any callable objects from options
                if "options" in chart_data:
                    options = chart_data["options"]
                    if isinstance(options, dict) and "plugins" in options:
                        plugins = options["plugins"]
                        if isinstance(plugins, dict) and "tooltip" in plugins:
                            tooltip = plugins["tooltip"]
                            if isinstance(tooltip, dict) and "callbacks" in tooltip:
                                # Remove callbacks as they contain functions
                                del tooltip["callbacks"]
                
                chat_response["chart"] = chart_data
        
        return ChatResponse(**chat_response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    manager: AgentManager = Depends(get_agent_manager)
):
    """Streaming chat endpoint for real-time responses"""
    async def generate():
        try:
            # Initialize streaming response
            query = request.query
            session_id = request.session_id or "default"
            
            # Process in chunks for streaming
            if manager:
                async for chunk in manager.stream_response(query, session_id):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/analyze-query", response_model=QueryAnalysis)
async def analyze_query(
    query: str,
    service: ChatGPTService = Depends(get_chatgpt_service)
):
    """Analyze a query without executing it"""
    try:
        analysis = await service.analyze_query(query)
        return QueryAnalysis(**analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch-database")
async def switch_database(
    config: DatabaseConfig,
    manager: AgentManager = Depends(get_agent_manager),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Switch database connection dynamically"""
    try:
        await db.switch_database(
            db_type=config.database_type,
            connection_url=config.connection_url
        )
        
        # Reinitialize agent with new database
        await manager.reinitialize()
        
        return {
            "status": "success",
            "message": f"Switched to {config.database_type}",
            "database_type": config.database_type
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-connection")
async def test_database_connection(config: DatabaseConfig):
    """Test database connection without switching"""
    try:
        from app.services.database_factory import test_connection
        
        success, message = await test_connection(
            db_type=config.database_type,
            connection_url=config.connection_url
        )
        
        return {
            "success": success,
            "message": message,
            "database_type": config.database_type
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "database_type": config.database_type
        }


@router.get("/schema", response_model=DatabaseSchema)
async def get_database_schema(db: DatabaseManager = Depends(get_db_manager)):
    """Get current database schema"""
    try:
        schema = await db.get_schema()
        return DatabaseSchema(**schema)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=AgentStatus)
async def get_agent_status(
    agent: AgentManager = Depends(get_agent_manager),
    db: DatabaseManager = Depends(get_db_manager),
    service: ChatGPTService = Depends(get_chatgpt_service)
):
    """Get current agent and database status"""
    stats = agent.get_stats() if agent else {}
    return AgentStatus(
        agent_ready=agent is not None,
        database_connected=db.connected if db else False,
        database_type=db.db_type if db else "unknown",
        chatgpt_available=service is not None,
        last_updated=db.last_updated if db else None,
        active_sessions=stats.get("active_sessions", 0)
    )

@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    agent: AgentManager = Depends(get_agent_manager)
):
    """Get chat history for a session"""
    try:
        if agent and hasattr(agent, 'sessions'):
            session = agent.sessions.get(session_id, [])
            return {
                "session_id": session_id,
                "messages": [msg.dict() for msg in session] if session else [],
                "timestamp": None
            }
        return {
            "session_id": session_id,
            "messages": [],
            "timestamp": None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggest-queries")
async def suggest_queries(
    context: Optional[str] = None,
    agent: AgentManager = Depends(get_agent_manager)
):
    """Suggest relevant queries based on context"""
    try:
        if agent:
            suggestions = await agent.suggest_queries(context)
            return {"suggestions": suggestions}
        else:
            return {"suggestions": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current-db-config")
async def get_current_db_config(db: DatabaseManager = Depends(get_db_manager)):
    """Get current database configuration"""
    try:
        # Load from ConfigManager
        from app.core.config_manager import ConfigManager
        config = ConfigManager.get_current_config()
        
        return {
            "database_type": config.get("database_type", "postgres"),
            "connection_url": config.get("connection_url", ""),
            "last_updated": config.get("last_updated"),
            "currently_connected": db.connected if db else False,
            "current_db_type": db.db_type if db else "unknown"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))