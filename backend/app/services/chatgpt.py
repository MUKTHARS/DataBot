import asyncio
import logging
import json
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime

import openai
from openai import AsyncOpenAI

from app.config import settings
from app.api.schemas import Message, MessageType

logger = logging.getLogger(__name__)


class ChatGPTService:
    """Service for interacting with OpenAI's ChatGPT API"""
    
    def __init__(self):
        self.client = None
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE
        self.system_prompt = settings.AGENT_SYSTEM_PROMPT
        self.context = {}
        
    async def initialize(self) -> bool:
        """Initialize ChatGPT service"""
        try:
            logger.info("🤖 Initializing ChatGPT service...")
            
            # Initialize OpenAI client
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Test connection
            await self.test_connection()
            
            logger.info(f"✅ ChatGPT service initialized (model: {self.model})")
            return True
            
        except Exception as e:
            logger.error(f"❌ ChatGPT initialization failed: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test ChatGPT API connection"""
        try:
            # Make a simple completion to test
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            if response.choices:
                logger.info("✅ ChatGPT API connection successful")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ ChatGPT API connection failed: {e}")
            raise
    
    async def update_context(self, database_schema: Dict[str, Any], database_type: str):
        """Update agent context with database schema"""
        self.context = {
            "database_type": database_type,
            "database_schema": database_schema,
            "last_updated": datetime.now().isoformat()
        }
        
        # Update system prompt with schema
        schema_summary = self._generate_schema_summary(database_schema)
        
        # Updated system prompt WITHOUT asterisks
        self.system_prompt = f"""You are a sophisticated data analytics assistant with access to a live database.
    Your capabilities include:
    1. Understanding natural language queries about data
    2. Generating appropriate SQL or MongoDB queries
    3. Analyzing query results
    4. Providing insights and recommendations
    5. Answering follow-up questions

    IMPORTANT FORMATTING RULES:
    - NEVER use asterisks (*) in your responses
    - NEVER use markdown formatting (**, __, etc.)
    - Use bullet points (•) for lists
    - Use numbered points (1., 2., 3.) for sequences
    - Use line breaks and spacing for structure
    - Use capitalization for emphasis when needed
    - Keep responses clean and professional

    SAFETY RULES:
    - Always verify query safety before execution
    - Never execute DROP, DELETE, or other destructive operations
    - Provide explanations for your queries
    - Suggest related analyses when appropriate
    - Admit when you don't know something

    Current Database: {database_type}

    Database Schema:
    {schema_summary}

    Guidelines:
    1. Generate queries appropriate for {database_type}
    2. Use proper syntax for {database_type}
    3. Consider table relationships
    4. Optimize queries for performance
    5. Handle NULL values appropriately"""
        
    def _generate_schema_summary(self, schema: Dict[str, Any]) -> str:
        """Generate human-readable schema summary"""
        summary = []
        
        # Add tables
        if "tables" in schema and schema["tables"]:
            summary.append("Tables:")
            for table in schema["tables"][:10]:  # Limit to 10 tables
                table_name = table.get("name", "unknown")
                columns = table.get("columns", [])
                summary.append(f"  - {table_name}: {len(columns)} columns")
        
        # Add collections for MongoDB
        if "collections" in schema and schema["collections"]:
            summary.append("\nCollections:")
            for collection in schema["collections"][:10]:
                collection_name = collection.get("name", "unknown")
                summary.append(f"  - {collection_name}")
        
        # Add relationships
        if "relationships" in schema and schema["relationships"]:
            summary.append("\nRelationships:")
            for rel in schema["relationships"][:5]:
                summary.append(f"  - {rel.get('from')} → {rel.get('to')}")
        
        return "\n".join(summary)
    
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze natural language query to determine intent"""
        try:
            prompt = f"""Analyze this database query request and determine:

1. Intent (what the user wants to know/do)
2. Query type (select, aggregate, analytics, etc.)
3. Key parameters
4. Suggested database query structure

Query: "{query}"

Respond in JSON format:
{{
    "intent": "string describing the intent",
    "query_type": "select|aggregate|analytics|etc.",
    "confidence": 0.0-1.0,
    "parameters": {{}},
    "suggested_query": "sample query structure",
    "safety_level": "safe|warning|dangerous"
}}"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a database query analyzer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"🔍 Query analysis: {result.get('intent')} (confidence: {result.get('confidence')})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Query analysis failed: {e}")
            return {
                "intent": "unknown",
                "query_type": "unknown",
                "confidence": 0.0,
                "parameters": {},
                "safety_level": "unknown"
            }
    
    async def generate_query(
        self, 
        query: str, 
        intent: str, 
        parameters: Dict[str, Any],
        database_type: str
    ) -> str:
        """Generate database query from natural language"""
        try:
            prompt = f"""Generate a {database_type.upper()} query for this request:

User Request: "{query}"
Intent: {intent}
Parameters: {json.dumps(parameters)}

Database Type: {database_type}

Requirements:
1. Generate valid {database_type} syntax
2. Keep it simple and efficient
3. Use appropriate collection names (customers, products, orders)
4. For MongoDB, return a simple find query or aggregation
5. Add comments explaining the query

Respond with ONLY the query (no additional text):"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are a {database_type} query generator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300  # Reduced to make it faster
            )
            
            generated_query = response.choices[0].message.content.strip()
            
            # Clean up the query
            generated_query = self._clean_query(generated_query, database_type)
            
            logger.info(f"📝 Generated {database_type} query: {generated_query[:100]}...")
            return generated_query
            
        except Exception as e:
            logger.error(f"❌ Query generation failed: {e}")
            # Return a simple default query
            if database_type == "mongodb":
                return '{"find": "orders", "limit": 10}'
            else:
                return "SELECT * FROM orders LIMIT 10"
    
    def _clean_query(self, query: str, database_type: str) -> str:
        """Clean up generated query"""
        # Remove markdown code blocks
        query = query.replace("```javascript", "").replace("```json", "").replace("```sql", "").replace("```", "").strip()
        
        # Remove excessive whitespace
        import re
        query = re.sub(r'\s+', ' ', query)
        
        # For MongoDB, ensure it's valid JSON if it's a find command
        if database_type == "mongodb" and query.startswith("{"):
            try:
                import json
                # Try to parse as JSON to validate
                json.loads(query)
            except:
                # If not valid JSON, wrap it in a find command
                query = f'{{"find": "orders", "filter": {query}}}'
        
        return query
    

    async def generate_response(
        self, 
        query: str, 
        data: Any, 
        query_used: str,
        context: List[Message]
    ) -> str:
        """Generate natural language response from query results"""
        try:
            # Prepare data summary
            data_summary = self._summarize_data(data)
            
            # Updated prompt WITHOUT any asterisk formatting
            prompt = f"""Generate a professional, structured response based on the following:

    User Question: "{query}"
    Query Used: {query_used}
    Data Summary: {data_summary}

    GUIDELINES FOR RESPONSE:
    1. Structure your response with clear sections
    2. Use bullet points for lists and numbered points for sequences
    3. DO NOT use any asterisks (*), underscores (_), or markdown formatting
    4. Use capitalization and spacing for emphasis instead
    5. If no relevant data is found, explain clearly
    6. Provide actionable insights when possible
    7. Keep response concise but comprehensive

    FORMAT REQUIREMENTS:
    - Start with a direct answer to the question
    - Use bullet points (•) for lists
    - Use numbered points (1., 2., 3.) for steps or sequences
    - Add clear section headers
    - End with relevant follow-up suggestions
    - DO NOT use **bold** or *italic* or __any__ markdown
    - Use line breaks and spacing for structure instead

    RESPONSE TONE:
    - Professional and analytical
    - Data-driven
    - Clear and direct
    - Helpful and informative

    Generate the response WITHOUT any asterisks:"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self._messages_to_openai(context[-3:]),
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Clean any remaining asterisks that might slip through
            answer = self._clean_response_text(answer)
            
            logger.info(f"💬 Generated response: {answer[:100]}...")
            return answer
            
        except Exception as e:
            logger.error(f"❌ Response generation failed: {e}")
            # Return a clean fallback response without asterisks
            return self._create_fallback_response(query, data)
        
    def _clean_response_text(self, text: str) -> str:
        """Clean response text by removing all asterisks"""
        # Remove all asterisks
        text = text.replace('**', '')
        text = text.replace('*', '')
        
        # Remove asterisks used as bullets
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Convert asterisk bullets to proper bullet points
            if stripped.startswith('* '):
                cleaned_lines.append(f"• {stripped[2:]}")
            elif stripped.startswith('- '):
                cleaned_lines.append(f"• {stripped[2:]}")
            else:
                cleaned_lines.append(line)
        
        # Remove any remaining double asterisks that might appear
        cleaned_text = '\n'.join(cleaned_lines)
        cleaned_text = cleaned_text.replace('**', '')
        cleaned_text = cleaned_text.replace('*', '')
        
        return cleaned_text

    def _create_fallback_response(self, query: str, data: Any) -> str:
        """Create fallback response without asterisks"""
        if data:
            if isinstance(data, list):
                if len(data) > 0:
                    return f"Analysis Complete\n\nFound {len(data)} records matching your query\nData shows relevant information based on your request\n\nNext Steps: Consider refining your query for more specific insights."
                else:
                    return "No Results Found\n\nNo records were found matching your query. Please try:\n1. Broadening your search criteria\n2. Checking your spelling\n3. Using different keywords"
            else:
                return f"Data Analysis\n\nFound relevant data:\n{str(data)[:200]}..."
        else:
            return "Query Processed\n\nYour query has been processed successfully, but no data was returned. This could mean:\n• The requested data doesn't exist\n• Your query needs refinement\n• There are no matching records"




    def _summarize_data(self, data: Any) -> str:
        """Create a summary of the data for the prompt"""
        if data is None:
            return "No data returned"
        
        if isinstance(data, list):
            if len(data) == 0:
                return "Empty result set"
            
            # Sample first few items
            sample = data[:3]
            return f"{len(data)} rows returned. Sample: {json.dumps(sample, default=str)}"
        
        elif isinstance(data, dict):
            return f"Object with keys: {list(data.keys())}"
        
        else:
            return str(data)
    
    async def generate_insights(self, data: Any) -> List[str]:
        """Generate insights from data"""
        try:
            if not data or (isinstance(data, list) and len(data) == 0):
                return ["No data available for insights"]
            
            data_summary = self._summarize_data(data)
            
            prompt = f"""Generate 3-5 key insights from this data:

Data: {data_summary}

Requirements:
1. Focus on patterns and trends
2. Highlight anomalies if any
3. Provide business implications
4. Keep each insight concise
5. Use bullet points

Respond with only the insights (one per line):"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data analyst generating insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            insights_text = response.choices[0].message.content.strip()
            insights = [i.strip() for i in insights_text.split("\n") if i.strip()]
            
            logger.info(f"💡 Generated {len(insights)} insights")
            return insights[:5]  # Limit to 5 insights
            
        except Exception as e:
            logger.error(f"❌ Insights generation failed: {e}")
            return ["Unable to generate insights at this time"]
    
    async def suggest_followup(self, original_query: str, data: Any) -> List[str]:
        """Suggest follow-up questions"""
        try:
            data_summary = self._summarize_data(data)
            
            prompt = f"""Based on this query and data, suggest 3-5 follow-up questions:

Original Query: "{original_query}"
Data Summary: {data_summary}

Requirements:
1. Suggest logical next questions
2. Consider deeper analysis paths
3. Include different perspectives
4. Make questions actionable
5. Keep questions concise

Respond with only the questions (one per line):"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You suggest relevant follow-up questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=300
            )
            
            suggestions_text = response.choices[0].message.content.strip()
            suggestions = [s.strip() for s in suggestions_text.split("\n") if s.strip()]
            
            logger.info(f"🤔 Generated {len(suggestions)} follow-up suggestions")
            return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            logger.error(f"❌ Follow-up suggestions failed: {e}")
            return []
    
    async def suggest_queries(
        self, 
        context: Optional[str] = None,
        database_schema: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Suggest relevant queries based on context"""
        try:
            schema_summary = self._generate_schema_summary(database_schema) if database_schema else ""
            
            prompt = f"""Suggest 5-7 useful database queries based on:

Context: {context or 'General data analysis'}
Database Schema: {schema_summary}

Requirements:
1. Include different types of queries (analytics, reporting, exploration)
2. Cover different tables/collections
3. Make queries actionable
4. Include time-based analysis
5. Suggest aggregation queries

Respond with only the queries (one per line, no explanations):"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You suggest useful database queries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=400
            )
            
            queries_text = response.choices[0].message.content.strip()
            queries = [q.strip() for q in queries_text.split("\n") if q.strip()]
            
            return queries[:7]  # Limit to 7 queries
            
        except Exception as e:
            logger.error(f"❌ Query suggestions failed: {e}")
            return []
    
    async def generate_error_response(self, query: str, error: str) -> str:
        """Generate helpful error response"""
        prompt = f"""The user asked: "{query}"
But there was an error: {error}

Generate a helpful, apologetic response that:
1. Acknowledges the error
2. Explains what might have gone wrong (in simple terms)
3. Suggests alternatives or fixes
4. Maintains a positive tone

Keep it concise and helpful:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You help users when queries fail."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
        except:
            return f"I'm sorry, but I encountered an error while processing your query: {error}. Please try rephrasing or check if the database is available."
    
    async def stream_completion(
        self, 
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream ChatGPT completion"""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            yield f"Error: {str(e)}"
    
    def _messages_to_openai(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert internal messages to OpenAI format"""
        openai_messages = []
        
        for msg in messages:
            role_map = {
                MessageType.USER: "user",
                MessageType.ASSISTANT: "assistant",
                MessageType.SYSTEM: "system"
            }
            
            role = role_map.get(msg.type, "user")
            content = msg.content
            
            # Add metadata as system message if present
            if msg.metadata and msg.type == MessageType.ASSISTANT:
                metadata_str = json.dumps(msg.metadata, default=str)
                openai_messages.append({
                    "role": "system",
                    "content": f"Previous response metadata: {metadata_str}"
                })
            
            openai_messages.append({"role": role, "content": content})
        
        return openai_messages
    
    async def cleanup(self):
        """Cleanup ChatGPT service"""
        try:
            if self.client:
                # OpenAI client doesn't need explicit cleanup
                pass
            logger.info("✅ ChatGPT service cleaned up")
        except Exception as e:
            logger.error(f"❌ ChatGPT cleanup error: {e}")