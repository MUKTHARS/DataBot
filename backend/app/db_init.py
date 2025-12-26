import asyncio
import logging
from sqlalchemy import create_engine
from app.models.sql_models import SQLBase
from app.config import settings
import asyncpg

logger = logging.getLogger(__name__)

async def initialize_database():
    """Initialize database with tables"""
    try:
        logger.info("📁 Initializing database tables...")
        
        # Create sync engine for table creation
        connection_url = settings.POSTGRES_URL
        if not connection_url:
            raise ValueError("POSTGRES_URL not configured")
        
        # Extract database name
        db_name = "analytics_db"  # Default database name
        
        # First, connect to PostgreSQL server to create database if not exists
        try:
            # Parse connection URL to get credentials
            # postgresql://user:pass@localhost:5432/dbname
            parts = connection_url.split('://')[1].split('@')
            auth, host_port_db = parts[0], parts[1]
            user, password = auth.split(':')
            host_port, db_name = host_port_db.split('/')
            
            # Connect to default postgres database to create our database
            admin_conn = await asyncpg.connect(
                user=user,
                password=password,
                host=host_port.split(':')[0],
                port=host_port.split(':')[1] if ':' in host_port else '5432',
                database='postgres'
            )
            
            # Check if database exists
            exists = await admin_conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            
            if not exists:
                logger.info(f"📁 Creating database: {db_name}")
                await admin_conn.execute(f'CREATE DATABASE "{db_name}"')
                logger.info(f"✅ Database {db_name} created")
            
            await admin_conn.close()
            
        except Exception as e:
            logger.warning(f"⚠️ Could not check/create database: {e}")
        
        # Now create tables using SQLAlchemy
        engine = create_engine(connection_url)
        
        # Create all tables
        SQLBase.metadata.create_all(bind=engine)
        
        logger.info("✅ Database tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False