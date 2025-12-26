import asyncio
import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.services.database_factory import DatabaseFactory
from app.models.sql_models import SQLBase, Product, Customer, Order, OrderItem, Category, Review, Inventory
from sqlalchemy import create_engine
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_sample_database():
    """Create sample tables and insert sample data"""
    
    # Get database URL
    db_type = settings.DATABASE_TYPE
    connection_url = settings.POSTGRES_URL
    
    if not connection_url:
        logger.error("❌ No database connection URL found in settings")
        return False
    
    try:
        # Create synchronous engine for table creation
        if db_type == "postgres":
            sync_url = connection_url.replace("postgresql+asyncpg://", "postgresql://")
            engine = create_engine(sync_url)
            
            # Create all tables
            SQLBase.metadata.create_all(engine)
            logger.info("✅ Created all database tables")
            
            # Insert sample data
            with engine.connect() as conn:
                # Insert sample categories
                conn.execute("""
                    INSERT INTO categories (name, description) VALUES 
                    ('Electronics', 'Electronic devices and accessories'),
                    ('Clothing', 'Apparel and fashion items'),
                    ('Books', 'Books and publications'),
                    ('Home & Garden', 'Home improvement and garden supplies')
                    ON CONFLICT (name) DO NOTHING;
                """)
                
                # Insert sample products
                conn.execute("""
                    INSERT INTO products (name, category, price, description, sku, stock_quantity, active) VALUES 
                    ('Laptop Pro', 'Electronics', 1299.99, 'High-performance laptop', 'LP-001', 50, true),
                    ('Wireless Mouse', 'Electronics', 29.99, 'Ergonomic wireless mouse', 'WM-002', 200, true),
                    ('T-Shirt', 'Clothing', 19.99, 'Cotton t-shirt', 'TS-003', 150, true),
                    ('Python Programming Book', 'Books', 49.99, 'Learn Python programming', 'BK-004', 75, true),
                    ('Coffee Maker', 'Home & Garden', 89.99, 'Automatic coffee maker', 'CM-005', 30, true)
                    ON CONFLICT (sku) DO NOTHING;
                """)
                
                # Insert sample customers
                conn.execute("""
                    INSERT INTO customers (name, email, phone, city, active) VALUES 
                    ('John Doe', 'john@example.com', '123-456-7890', 'New York', true),
                    ('Jane Smith', 'jane@example.com', '098-765-4321', 'Los Angeles', true),
                    ('Bob Johnson', 'bob@example.com', '555-123-4567', 'Chicago', true)
                    ON CONFLICT (email) DO NOTHING;
                """)
                
                # Get IDs for foreign keys
                result = conn.execute("SELECT id FROM customers LIMIT 3")
                customer_ids = [row[0] for row in result]
                
                result = conn.execute("SELECT id FROM products LIMIT 5")
                product_ids = [row[0] for row in result]
                
                # Insert sample orders
                for i, customer_id in enumerate(customer_ids):
                    conn.execute(f"""
                        INSERT INTO orders (customer_id, order_date, total_amount, final_amount, status, payment_status) 
                        VALUES ({customer_id}, CURRENT_DATE - INTERVAL '{i*10} days', 
                                {100.00 + i*50}, {100.00 + i*50}, 'completed', 'paid')
                    """)
                
                logger.info("✅ Inserted sample data")
                
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to create sample database: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(create_sample_database())