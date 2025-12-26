import os
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import validator, field_validator
import logging
from typing import Union


class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    
    # ChatGPT Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.1
    
    # Database Configuration
    DATABASE_TYPE: str = "mongodb"  # postgres, mysql, mongodb
    POSTGRES_URL: Optional[str] = None
    MYSQL_URL: Optional[str] = None
    MONGODB_URL: Optional[str] = None
    
    # Cache Configuration
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 300  # 5 minutes
    
    # Agent Configuration
    AGENT_SYSTEM_PROMPT: str = """You are a sophisticated data analytics assistant with access to a live database.
    Your capabilities include:
    1. Understanding natural language queries about data
    2. Generating appropriate SQL or MongoDB queries
    3. Analyzing query results
    4. Providing insights and recommendations
    5. Answering follow-up questions

    RESPONSE FORMATTING REQUIREMENTS:
    - Use **bold text** for key metrics and important findings
    - Use • bullet points for lists
    - Use numbered points (1., 2., 3.) for sequences or steps
    - Structure responses with clear sections
    - Use markdown formatting appropriately
    - Highlight numerical values clearly
    - End with relevant suggestions or next steps

    IMPORTANT RULES:
    - Always verify query safety before execution
    - Never execute DROP, DELETE, or other destructive operations
    - Provide explanations for your queries
    - Suggest related analyses when appropriate
    - Admit when you don't know something
    - Format responses professionally with proper structure

    Database schema will be provided in the conversation context."""
        
    # Security - Fixed: Use string instead of List for environment variable
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @field_validator("DATABASE_TYPE")
    @classmethod
    def validate_database_type(cls, v):
        valid_types = ["postgres", "mysql", "mongodb"]
        if v not in valid_types:
            raise ValueError(f"Database type must be one of {valid_types}")
        return v
    
    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_key(cls, v):
        if not v:
            print("⚠️  Warning: OPENAI_API_KEY is not set. ChatGPT features will not work.")
        return v
    
    @field_validator("CORS_ORIGINS")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string to list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Initialize settings
settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Log startup configuration (without sensitive data)
logger = logging.getLogger(__name__)
logger.info(f"🚀 Starting Smart Data Analytics Agent...")
logger.info(f"📁 Environment file: {os.path.abspath('.env') if os.path.exists('.env') else 'Not found'}")
logger.info(f"🌐 CORS Origins: {settings.CORS_ORIGINS}")
logger.info(f"🗄️  Database Type: {settings.DATABASE_TYPE}")
logger.info(f"🤖 ChatGPT Model: {settings.OPENAI_MODEL}")