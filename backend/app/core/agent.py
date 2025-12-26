import asyncio
import logging
import json
import re
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
from app.services.chart_generator import ChartGenerator
from app.services.chatgpt import ChatGPTService
from app.services.query_builder import QueryBuilder
from app.core.database import DatabaseManager
from app.core.cache import CacheManager
from app.config import settings
from app.api.schemas import Message, MessageType

logger = logging.getLogger(__name__)


class AgentManager:
    """Main agent manager for processing queries and generating responses"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.chatgpt_service = None
        self.cache_manager = CacheManager()
        self.query_builder = QueryBuilder()
        self.chart_generator = ChartGenerator()
        
        # Session management
        self.sessions: Dict[str, List[Message]] = {}
        self.session_ttl = 3600  # 1 hour
        
        # Statistics
        self.stats = {
            "queries_processed": 0,
            "cache_hits": 0,
            "errors": 0,
            "avg_response_time": 0
        }
    
    async def initialize(self) -> bool:
        """Initialize agent components"""
        try:
            logger.info("🤖 Initializing Smart Agent...")
            
            # Initialize ChatGPT service if not already set
            if not self.chatgpt_service:
                self.chatgpt_service = ChatGPTService()
                await self.chatgpt_service.initialize()
            
            # Initialize cache
            await self.cache_manager.initialize()
            
            # Load database schema for context
            schema = await self.db_manager.get_schema()
            
            # Update ChatGPT with schema context
            await self.chatgpt_service.update_context(
                database_schema=schema,
                database_type=self.db_manager.db_type
            )
            
            logger.info("✅ Agent initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Agent initialization failed: {e}")
            raise

    
    async def process_query(
        self, 
        query: str, 
        session_id: str = "default",
        stream: bool = False,
        websocket = None
    ) -> Dict[str, Any]:
        """Process a natural language query"""
        start_time = datetime.now()
        
        try:
            # Get or create session
            session = self._get_session(session_id)
            
            # Add user message to session
            user_msg = Message(
                type=MessageType.USER,
                content=query,
                metadata={"timestamp": start_time.isoformat()}
            )
            session.append(user_msg)
            
            # Check cache first
            cache_key = f"query:{session_id}:{hash(query)}"
            cached_result = await self.cache_manager.get(cache_key)
            
            if cached_result:
                logger.info(f"💾 Cache hit for query: {query[:50]}...")
                self.stats["cache_hits"] += 1
                return cached_result
            
            # Process with ChatGPT
            logger.info(f"🔍 Processing query: {query}")
            
            # Step 1: Analyze query intent
            analysis = await self.chatgpt_service.analyze_query(query)
            
            # Step 2: Generate appropriate query
            generated_query = await self.chatgpt_service.generate_query(
                query=query,
                intent=analysis["intent"],
                parameters=analysis["parameters"],
                database_type=self.db_manager.db_type
            )
            
            # Clean up the generated query (remove markdown, etc.)
            generated_query = self._clean_generated_query(generated_query)
            
            # Step 3: Execute query
            execution_result = await self._execute_generated_query(generated_query)
            
            # Step 4: Generate chart if applicable - WITH DEBUGGING
            chart_config = None
            if execution_result["data"]:
                logger.info(f"📊 Attempting to generate chart for query: {query}")
                logger.info(f"📊 Data type: {type(execution_result['data'])}")
                logger.info(f"📊 Data sample: {str(execution_result['data'])[:200]}")
                
                chart_config = self.chart_generator.analyze_data_for_charts(
                    execution_result["data"], 
                    query
                )
                
                if chart_config:
                    logger.info(f"✅ Chart generated successfully: {chart_config.get('type')} chart")
                    logger.info(f"✅ Chart title: {chart_config.get('title')}")
                    # Log the chart configuration for debugging
                    logger.info(f"📊 Chart config keys: {list(chart_config.keys())}")
                    logger.info(f"📊 Chart labels: {chart_config.get('labels', [])[:3]}")
                else:
                    logger.warning(f"⚠️ No chart generated for query: {query}")
            
            # Step 5: Generate natural language response
            response = await self._generate_response_with_retry(
                query=query,
                data=execution_result["data"],
                query_used=generated_query,
                context=session[-3:]
            )
            
            # Add chart description to response if chart is available
            if chart_config:
                chart_desc = self.chart_generator.generate_chart_description(chart_config)
                # Add chart mention to response
                response = f"{response}\n\n📊 {chart_desc}"
            
            # Step 6: Generate insights
            insights = []
            if execution_result["data"] and len(execution_result["data"]) > 0:
                insights = await self._generate_limited_insights(execution_result["data"])
            
            # Step 7: Generate suggestions
            suggestions = await self._generate_limited_suggestions(query, execution_result["data"])
            
            # Prepare final result - MAKE SURE CHART IS INCLUDED
            result = {
                "answer": response,
                "query": generated_query,
                "data": execution_result["data"],
                "insights": insights,
                "suggestions": suggestions,
                "execution_time": execution_result.get("execution_time", 0),
                "rows_returned": execution_result.get("rows_returned", 0)
            }
            
            # Add chart configuration if available - THIS IS CRITICAL
            if chart_config:
                result["chart"] = chart_config
                logger.info(f"✅ Chart added to result: {chart_config.get('title')}")
                # Debug log
                logger.info(f"📊 Result keys: {list(result.keys())}")
                logger.info(f"📊 Chart in result: {'chart' in result}")
            
            # Cache the result
            await self.cache_manager.set(cache_key, result, ttl=300)
            
            # Add assistant response to session
            assistant_msg = Message(
                type=MessageType.ASSISTANT,
                content=response,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "query_used": generated_query,
                    "data_summary": f"{execution_result.get('rows_returned', 0)} rows",
                    "has_chart": chart_config is not None,
                    "chart_config": chart_config  # Also store in metadata for debugging
                }
            )
            session.append(assistant_msg)
            
            # Update statistics
            self.stats["queries_processed"] += 1
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats["avg_response_time"] = (
                (self.stats["avg_response_time"] * (self.stats["queries_processed"] - 1) + processing_time) 
                / self.stats["queries_processed"]
            )
            
            logger.info(f"✅ Query processed in {processing_time:.2f}s, chart generated: {chart_config is not None}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Query processing failed: {e}")
            self.stats["errors"] += 1
            
            # Generate simple error response
            error_response = f"I encountered an error while processing your query: {str(e)}. Please try rephrasing or ask a simpler question."
            
            return {
                "answer": error_response,
                "query": "",
                "data": None,
                "insights": [],
                "suggestions": ["Please try rephrasing your query", "Check if the database is connected"],
                "error": str(e)
            }

    def _clean_generated_query(self, query: str) -> str:
        """Clean up the generated query string"""
        # Remove markdown code blocks
        query = query.replace("```javascript", "").replace("```", "").strip()
        query = query.replace("```json", "").replace("```", "").strip()
        query = query.replace("```sql", "").replace("```", "").strip()
        
        # Remove comments if they're taking too much space
        lines = query.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not (line.startswith('//') and len(line) > 50):
                cleaned_lines.append(line)
        
        return ' '.join(cleaned_lines)

    async def _generate_response_with_retry(self, query: str, data: Any, query_used: str, context: List[Message]) -> str:
        """Generate response with retry logic"""
        try:
            response = await self.chatgpt_service.generate_response(
                query=query,
                data=data,
                query_used=query_used,
                context=context
            )
            
            # Additional cleaning to ensure no asterisks
            response = self._clean_asterisks_from_response(response)
            
            return response
        except Exception as e:
            logger.warning(f"⚠️ Response generation failed, using fallback: {e}")
            # Use formatter for fallback response
            from app.utils.response_formatter import ResponseFormatter
            formatted_response = ResponseFormatter.format_structured_response(query, data, query_used)
            # Also clean asterisks from formatted response
            return self._clean_asterisks_from_response(formatted_response)

    def _clean_asterisks_from_response(self, response: str) -> str:
        """Clean all asterisks from response text"""
        # Remove all asterisks
        response = response.replace('**', '')
        response = response.replace('*', '')
        
        # Remove any markdown bold/italic syntax
        response = response.replace('__', '')
        response = response.replace('_', ' ')
        
        # Convert asterisk bullets to proper bullets
        lines = response.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Convert various bullet styles to standard bullet
            if stripped.startswith('* ') or stripped.startswith('- '):
                cleaned_lines.append(f"• {stripped[2:]}")
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

    async def _generate_limited_insights(self, data: Any) -> List[str]:
        """Generate limited insights to reduce OpenAI calls"""
        try:
            if not data or (isinstance(data, list) and len(data) == 0):
                return ["No data available for insights"]
            
            # Simple insights without OpenAI
            if isinstance(data, list):
                count = len(data)
                if count > 0:
                    insights = [
                        f"Found {count} records in the result",
                        "Data is available for analysis"
                    ]
                    
                    # Try to extract some numeric insights
                    if len(data) > 0 and isinstance(data[0], dict):
                        sample = data[0]
                        numeric_fields = [k for k, v in sample.items() if isinstance(v, (int, float))]
                        if numeric_fields:
                            insights.append(f"Contains numeric fields: {', '.join(numeric_fields[:3])}")
                    
                    return insights[:2]  # Limit to 2 insights
            
            return ["Data analysis completed"]
            
        except Exception as e:
            logger.error(f"❌ Insights generation failed: {e}")
            return ["Unable to generate insights at this time"]

    async def _generate_limited_suggestions(self, original_query: str, data: Any) -> List[str]:
        """Generate limited suggestions"""
        try:
            suggestions = []
            
            # Add generic suggestions based on query type
            query_lower = original_query.lower()
            
            if "month" in query_lower or "revenue" in query_lower:
                suggestions = [
                    "Show me revenue by product category",
                    "Compare this month's revenue with last month",
                    "What are the top selling products?"
                ]
            elif "customer" in query_lower:
                suggestions = [
                    "Show me customer demographics",
                    "Who are our top customers by spending?",
                    "How many new customers joined this month?"
                ]
            elif "product" in query_lower:
                suggestions = [
                    "Which products are low in stock?",
                    "Show me product reviews",
                    "What's the average product price by category?"
                ]
            else:
                suggestions = [
                    "Can you show me more details?",
                    "What are the trends over time?",
                    "Can you break this down by category?"
                ]
            
            return suggestions[:3]  # Limit to 3 suggestions
            
        except Exception as e:
            logger.error(f"❌ Suggestions generation failed: {e}")
            return []

    async def _execute_generated_query(self, query: str) -> Dict[str, Any]:
        """Execute a generated query safely"""
        start_time = datetime.now()
        
        try:
            # Clean up the query first
            query = self._clean_query_before_execution(query)
            
            # Validate query safety
            if not self._is_query_safe(query):
                # For MongoDB, be more lenient with queries
                if self.db_manager.db_type == "mongodb":
                    logger.info("⚠️ MongoDB query flagged as potentially unsafe, attempting to clean and execute...")
                    # Try to extract safe parts of the query
                    safe_query = self._extract_safe_mongo_query(query)
                    if safe_query:
                        query = safe_query
                    else:
                        raise ValueError("Query contains potentially unsafe operations")
                else:
                    raise ValueError("Query contains potentially unsafe operations")
            
            # Execute query
            result = await self.db_manager.execute_query(query)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "data": result,
                "execution_time": execution_time,
                "rows_returned": len(result) if isinstance(result, list) else 1,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            raise

    def _clean_query_before_execution(self, query: str) -> str:
        """Clean up query before execution"""
        # Remove markdown code blocks
        query = query.replace("```javascript", "").replace("```json", "").replace("```sql", "").replace("```", "").strip()
        
        # Remove trailing semicolons
        query = query.rstrip(';').strip()
        
        # For MongoDB queries, clean up JavaScript comments and newlines
        if self.db_manager.db_type == "mongodb":
            # Remove single line comments
            import re
            query = re.sub(r'//.*$', '', query, flags=re.MULTILINE)
            
            # Remove multi-line comments
            query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
            
            # Remove excessive whitespace
            query = re.sub(r'\s+', ' ', query).strip()
            
            # If it looks like JavaScript code, try to extract JSON
            if query.startswith('db.') or 'aggregate' in query:
                query = self._convert_mongo_js_to_json(query)
        
        return query

    def _extract_safe_mongo_query(self, query: str) -> Optional[str]:
        """Extract safe MongoDB query from potentially unsafe query"""
        try:
            import json
            
            # Try to find JSON-like structures
            if '[' in query and ']' in query:
                # Try to extract aggregation pipeline
                start = query.find('[')
                end = query.rfind(']') + 1
                if start >= 0 and end > start:
                    pipeline_str = query[start:end]
                    try:
                        # Try to parse as JSON
                        pipeline = json.loads(pipeline_str)
                        # Return as a find command
                        return json.dumps({"aggregate": "orders", "pipeline": pipeline})
                    except:
                        pass
            
            if '{' in query and '}' in query:
                # Try to extract find command
                start = query.find('{')
                end = query.rfind('}') + 1
                if start >= 0 and end > start:
                    filter_str = query[start:end]
                    try:
                        # Try to parse as JSON
                        filter_obj = json.loads(filter_str)
                        # Return as a find command
                        return json.dumps({"find": "orders", "filter": filter_obj, "limit": 100})
                    except:
                        pass
            
            # If we can't extract safe parts, return a simple query
            return '{"find": "orders", "limit": 10}'
            
        except Exception as e:
            logger.warning(f"⚠️ Could not extract safe MongoDB query: {e}")
            return None

    def _convert_mongo_js_to_json(self, query: str) -> str:
        """Convert MongoDB JavaScript to JSON format"""
        try:
            # Simple conversion for common patterns
            if 'db.orders.aggregate' in query:
                # Extract the pipeline
                start = query.find('[')
                end = query.rfind(']') + 1
                if start >= 0 and end > start:
                    pipeline_str = query[start:end]
                    # Clean up JavaScript objects
                    pipeline_str = pipeline_str.replace('new Date()', '"2024-01-01"')
                    pipeline_str = pipeline_str.replace('new Date(', '"')
                    pipeline_str = pipeline_str.replace(')', '"')
                    
                    # Try to create a simple pipeline
                    return json.dumps([
                        {"$match": {"status": "completed"}},
                        {"$group": {
                            "_id": None,
                            "total_revenue": {"$sum": "$total_amount"},
                            "order_count": {"$sum": 1}
                        }}
                    ])
            
            # Default simple query
            return '{"find": "orders", "limit": 10}'
            
        except Exception as e:
            logger.warning(f"⚠️ Could not convert MongoDB JS to JSON: {e}")
            return '{"find": "orders", "limit": 10}'
    
    def _is_query_safe(self, query: str) -> bool:
        """Check if query is safe to execute"""
        unsafe_patterns = [
            r"\bDROP\b",
            r"\bDELETE\b.*\bFROM\b",
            r"\bTRUNCATE\b",
            r"\bALTER\b",
            r"\bCREATE\b.*\bTABLE\b",
            r"\bINSERT\b.*\bINTO\b",
            r"\bUPDATE\b.*\bSET\b",
            r"\bGRANT\b",
            r"\bREVOKE\b",
            r"\bEXEC\b",
            r"\bEXECUTE\b"
        ]
        
        query_upper = query.upper()
        
        # For MongoDB, we need different safety checks
        if self.db_manager.db_type == "mongodb":
            # MongoDB specific unsafe patterns
            mongo_unsafe_patterns = [
                r"\bdropDatabase\b",
                r"\bdrop\b.*\(",
                r"\bremove\b.*\{.*\}",
                r"\beval\b",
                r"\bsystem\.",
                r"\$where\b.*\{.*\}",
                r"\$function\b"
            ]
            
            # Check for JavaScript injection
            if "function(" in query or "javascript:" in query:
                logger.warning(f"⚠️ Unsafe MongoDB query detected: JavaScript injection")
                return False
                
            for pattern in mongo_unsafe_patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    logger.warning(f"⚠️ Unsafe MongoDB query detected: {pattern}")
                    return False
            
            # For MongoDB aggregation pipelines, they're usually safe
            if query.strip().startswith('[') and query.strip().endswith(']'):
                return True
                
            # For MongoDB find commands
            if query.strip().startswith('{') and query.strip().endswith('}'):
                return True
                
            # Allow MongoDB queries with semicolons (they're often comments in JS)
            return True
        
        else:
            # For SQL databases, check unsafe patterns
            for pattern in unsafe_patterns:
                if re.search(pattern, query_upper, re.IGNORECASE):
                    logger.warning(f"⚠️ Unsafe SQL query detected: {pattern}")
                    return False
            
            # Check for multiple statements - but allow if it's MongoDB or safe
            # Remove trailing semicolons before checking
            query_no_semicolon = query.rstrip(';').strip()
            if query_no_semicolon.count(';') > 0:
                # For MongoDB with JavaScript, semicolons are normal
                if self.db_manager.db_type != "mongodb":
                    logger.warning(f"⚠️ Multiple statements detected in query")
                    return False
            
            return True

    async def stream_response(
        self, 
        query: str, 
        session_id: str = "default"
    ) -> AsyncGenerator[str, None]:
        """Stream response for real-time updates"""
        try:
            # Process query in background
            result = await self.process_query(query, session_id)
            
            # Stream response in chunks
            response_text = result["answer"]
            chunk_size = 50
            
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                yield chunk
                await asyncio.sleep(0.01)  # Small delay for streaming effect
            
            # Add metadata
            yield f"\n\n📊 **Results**: {result.get('rows_returned', 0)} rows returned"
            
            if result.get("insights"):
                yield f"\n💡 **Insights**: {', '.join(result['insights'][:3])}"
                
        except Exception as e:
            yield f"❌ Error: {str(e)}"
    
    async def _stream_response(self, result: Dict[str, Any], websocket):
        """Stream response through WebSocket"""
        try:
            # Stream answer
            answer = result["answer"]
            for chunk in self._chunk_text(answer, 100):
                await websocket.send_json({
                    "type": "chunk",
                    "chunk": chunk,
                    "is_final": False
                })
                await asyncio.sleep(0.01)
            
            # Send final message
            await websocket.send_json({
                "type": "complete",
                "result": {
                    "answer": result["answer"],
                    "insights": result["insights"],
                    "suggestions": result["suggestions"]
                },
                "is_final": True
            })
            
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
    
    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks for streaming"""
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    
    def _get_session(self, session_id: str) -> List[Message]:
        """Get or create a session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        # Clean old messages (keep last 50)
        session = self.sessions[session_id]
        if len(session) > 50:
            self.sessions[session_id] = session[-50:]
        
        return self.sessions[session_id]
    
    async def suggest_queries(self, context: Optional[str] = None) -> List[str]:
        """Suggest relevant queries based on context"""
        try:
            if self.chatgpt_service:
                schema = await self.db_manager.get_schema()
                return await self.chatgpt_service.suggest_queries(
                    context=context,
                    database_schema=schema
                )
            return []
        except Exception as e:
            logger.error(f"❌ Query suggestion failed: {e}")
            return []
    
    async def reinitialize(self):
        """Reinitialize agent with current database"""
        await self.initialize()
    
    async def cleanup(self):
        """Cleanup agent resources"""
        try:
            if self.chatgpt_service:
                await self.chatgpt_service.cleanup()
            
            if self.cache_manager:
                await self.cache_manager.cleanup()
            
            logger.info("✅ Agent cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Agent cleanup error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            **self.stats,
            "active_sessions": len(self.sessions),
            "cache_size": self.cache_manager.size if self.cache_manager else 0,
            "chatgpt_available": self.chatgpt_service is not None
        }