from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

from app.api.routes import router as api_router
from app.core.agent import AgentManager
from app.core.database import DatabaseManager
from app.services.chatgpt import ChatGPTService
from app.models.sql_models import create_sql_tables
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
agent_manager = None
db_manager = None
chatgpt_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global agent_manager, db_manager, chatgpt_service
    
    # Import here to avoid circular imports
    from app.api.routes import agent_manager as routes_agent_manager
    from app.api.routes import db_manager as routes_db_manager
    from app.api.routes import chatgpt_service as routes_chatgpt_service
    from app.core.config_manager import ConfigManager  # Add this import
    
    # Startup
    logger.info("🚀 Starting Smart Data Analytics Agent...")
    
    try:
        # Load saved configuration
        saved_config = ConfigManager.load_config()
        if saved_config:
            logger.info(f"📁 Loaded saved configuration for {saved_config.get('database_type', 'postgres')}")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Create tables if they don't exist
        if db_manager.db and hasattr(db_manager.db, 'async_engine'):
            try:
                await create_sql_tables(db_manager.db.async_engine)
                logger.info("✅ Database tables created/verified")
                
                # Try to insert sample data, but don't fail if it doesn't work
                await _try_insert_sample_data(db_manager)
            except Exception as e:
                logger.warning(f"⚠️ Could not create tables or insert sample data: {e}")
                logger.info("⚠️ Continuing without sample data...")
        
        # Initialize ChatGPT service
        chatgpt_service = ChatGPTService()
        await chatgpt_service.initialize()
        
        # Initialize agent manager
        agent_manager = AgentManager(db_manager)
        agent_manager.chatgpt_service = chatgpt_service
        await agent_manager.initialize()
        
        # Update global references in routes
        routes_agent_manager = agent_manager
        routes_db_manager = db_manager
        routes_chatgpt_service = chatgpt_service
        
        logger.info("✅ Agent initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down agent...")
    if agent_manager:
        await agent_manager.cleanup()
    if db_manager:
        await db_manager.cleanup()
    if chatgpt_service:
        await chatgpt_service.cleanup()
        
async def _try_insert_sample_data(db_manager):
    """Try to insert sample data, but don't fail if it doesn't work"""
    try:
        # First, check if there are existing customers
        check_customers_query = "SELECT id, email FROM customers LIMIT 3;"
        existing_customers = []
        
        try:
            result = await db_manager.execute_query(check_customers_query)
            if result and isinstance(result, list):
                existing_customers = [(row.get('id'), row.get('email')) for row in result]
                logger.info(f"📊 Found {len(existing_customers)} existing customers")
        except Exception as e:
            logger.warning(f"⚠️ Could not check existing customers: {e}")
        
        # Only insert customers if none exist
        if not existing_customers:
            # Insert sample customers - FIXED: Use ON CONFLICT DO NOTHING to avoid errors
            insert_customers_query = """
            INSERT INTO customers (name, email, phone, city, country) 
            VALUES 
            ('John Doe', 'john@example.com', '+1234567890', 'New York', 'USA'),
            ('Jane Smith', 'jane@example.com', '+1987654321', 'London', 'UK'),
            ('Bob Johnson', 'bob@example.com', '+1122334455', 'Sydney', 'Australia')
            ON CONFLICT (email) DO NOTHING;
            """
            
            try:
                result = await db_manager.execute_query(insert_customers_query)
                logger.info("✅ Attempted to insert sample customers")
                
                # Now get the actual customer IDs that exist
                get_customers_query = "SELECT id, email FROM customers WHERE email IN ('john@example.com', 'jane@example.com', 'bob@example.com') ORDER BY id;"
                result = await db_manager.execute_query(get_customers_query)
                if result and isinstance(result, list):
                    existing_customers = [(row.get('id'), row.get('email')) for row in result]
                    logger.info(f"📊 Found {len(existing_customers)} customers after insertion attempt")
                else:
                    logger.warning("⚠️ No customers found after insertion attempt")
                    return  # Don't try other inserts if no customers
            except Exception as e:
                logger.warning(f"⚠️ Could not insert customers: {e}")
                return  # Don't try other inserts if customers failed
        
        # Only proceed if we have customer IDs
        if not existing_customers or len(existing_customers) < 3:
            logger.warning("⚠️ Not enough customers found, skipping sample data insertion")
            return
        
        # Use the actual customer IDs from the database
        customer_ids = [cust[0] for cust in existing_customers[:3]]
        logger.info(f"📊 Using customer IDs: {customer_ids}")
        
        # Check for existing products
        check_products_query = "SELECT id, sku FROM products LIMIT 3;"
        existing_products = []
        
        try:
            result = await db_manager.execute_query(check_products_query)
            if result and isinstance(result, list):
                existing_products = [(row.get('id'), row.get('sku')) for row in result]
                logger.info(f"📊 Found {len(existing_products)} existing products")
        except Exception as e:
            logger.warning(f"⚠️ Could not check existing products: {e}")
        
        # Only insert products if none exist
        if not existing_products:
            # Insert sample products - FIXED: Use ON CONFLICT DO NOTHING
            insert_products_query = """
            INSERT INTO products (name, category, price, sku, stock_quantity) 
            VALUES 
            ('Laptop Pro', 'Electronics', 1299.99, 'LP-1001', 50),
            ('Wireless Mouse', 'Electronics', 49.99, 'WM-2001', 200),
            ('Office Chair', 'Furniture', 299.99, 'OC-3001', 30)
            ON CONFLICT (sku) DO NOTHING;
            """
            
            try:
                result = await db_manager.execute_query(insert_products_query)
                logger.info("✅ Attempted to insert sample products")
                
                # Get the actual product IDs that exist
                get_products_query = "SELECT id, sku FROM products WHERE sku IN ('LP-1001', 'WM-2001', 'OC-3001') ORDER BY id;"
                result = await db_manager.execute_query(get_products_query)
                if result and isinstance(result, list):
                    existing_products = [(row.get('id'), row.get('sku')) for row in result]
                    logger.info(f"📊 Found {len(existing_products)} products after insertion attempt")
                else:
                    logger.warning("⚠️ No products found after insertion attempt")
                    return  # Don't try other inserts if no products
            except Exception as e:
                logger.warning(f"⚠️ Could not insert products: {e}")
                return  # Don't try other inserts if products failed
        
        # Only proceed if we have product IDs
        if not existing_products or len(existing_products) < 3:
            logger.warning("⚠️ Not enough products found, skipping orders insertion")
            return
        
        # Use the actual product IDs from the database
        product_ids = [prod[0] for prod in existing_products[:3]]
        logger.info(f"📊 Using product IDs: {product_ids}")
        
        # Check for existing orders
        check_orders_query = "SELECT COUNT(*) as order_count FROM orders;"
        existing_order_count = 0
        
        try:
            result = await db_manager.execute_query(check_orders_query)
            if result and isinstance(result, list) and len(result) > 0:
                existing_order_count = result[0].get('order_count', 0)
                logger.info(f"📊 Found {existing_order_count} existing orders")
        except Exception as e:
            logger.warning(f"⚠️ Could not check existing orders: {e}")
        
        # Only insert orders if none exist
        if existing_order_count == 0:
            # Insert sample orders with actual customer IDs - FIXED: Use proper SQL formatting
            insert_orders_query = f"""
            INSERT INTO orders (customer_id, order_date, total_amount, final_amount, status, payment_status) 
            VALUES 
            ({customer_ids[0]}, '2024-01-15', 1349.98, 1349.98, 'completed', 'paid'),
            ({customer_ids[1]}, '2024-01-20', 89.98, 89.98, 'completed', 'paid'),
            ({customer_ids[2]}, '2024-02-05', 299.99, 299.99, 'processing', 'paid');
            """
            
            try:
                result = await db_manager.execute_query(insert_orders_query)
                logger.info("✅ Inserted sample orders")
                
                # Now get the order IDs we just inserted
                get_orders_query = "SELECT id FROM orders ORDER BY id DESC LIMIT 3;"
                result = await db_manager.execute_query(get_orders_query)
                if result and isinstance(result, list) and len(result) >= 3:
                    order_ids = [row.get('id') for row in result[:3]]
                    logger.info(f"📊 Using order IDs: {order_ids}")
                    
                    # Insert sample order items with actual order and product IDs
                    insert_order_items_query = f"""
                    INSERT INTO order_items (order_id, product_id, product_name, quantity, unit_price, total_price) 
                    VALUES 
                    ({order_ids[0]}, {product_ids[0]}, 'Laptop Pro', 1, 1299.99, 1299.99),
                    ({order_ids[0]}, {product_ids[1]}, 'Wireless Mouse', 1, 49.99, 49.99),
                    ({order_ids[1]}, {product_ids[1]}, 'Wireless Mouse', 1, 49.99, 49.99),
                    ({order_ids[2]}, {product_ids[2]}, 'Office Chair', 1, 299.99, 299.99);
                    """
                    
                    try:
                        await db_manager.execute_query(insert_order_items_query)
                        logger.info("✅ Inserted sample order items")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not insert order items: {e}")
            except Exception as e:
                logger.warning(f"⚠️ Could not insert orders: {e}")
        
        logger.info("✅ Sample data insertion process completed")
        
    except Exception as e:
        logger.error(f"❌ Failed to insert sample data: {e}")

# Create FastAPI app
app = FastAPI(
    title="Smart Data Analytics Agent",
    description="ChatGPT-powered database analytics with dynamic query generation",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
cors_origins = settings.CORS_ORIGINS
if isinstance(cors_origins, str):
    cors_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type", "message")
            
            if message_type == "message":
                query = data.get("query", "")
                session_id = data.get("session_id", "")
                
                if agent_manager:
                    # Process with agent
                    response = await agent_manager.process_query(
                        query=query,
                        session_id=session_id,
                        websocket=websocket
                    )
                    
                    # Send response
                    await websocket.send_json({
                        "type": "response",
                        "content": response,
                        "session_id": session_id
                    })
                    
            elif message_type == "heartbeat":
                await websocket.send_json({"type": "heartbeat", "status": "alive"})
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "agent": agent_manager is not None,
        "database": db_manager.connected if db_manager else False,
        "database_type": db_manager.db_type if db_manager else "unknown"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Smart Data Analytics Agent",
        "version": "2.0.0",
        "docs": "/docs",
        "features": [
            "ChatGPT-powered query analysis",
            "Dynamic SQL/MongoDB query generation",
            "Real-time WebSocket chat",
            "Multi-database support",
            "Intelligent data summarization"
        ]
    }