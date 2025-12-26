from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, 
    Boolean, Text, ForeignKey, JSON, Numeric, Index, text
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import json

from .base import SQLBase, BaseSQLModel

# SQL Models for common entities
class Product(SQLBase, BaseSQLModel):
    """Product model for SQL databases"""
    __tablename__ = "products"
    
    name = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    original_price = Column(Numeric(10, 2))
    description = Column(Text)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    stock_quantity = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=10)
    brand = Column(String(100))
    attributes = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    active = Column(Boolean, default=True, index=True)
    
    # Relationships
    order_items = relationship("OrderItem", back_populates="product")
    reviews = relationship("Review", back_populates="product")
    inventory = relationship("Inventory", back_populates="product", uselist=False)
    
    __table_args__ = (
        Index('idx_product_category_price', 'category', 'price'),
        Index('idx_product_active_stock', 'active', 'stock_quantity'),
    )
    
    @validates('attributes', 'tags')
    def validate_json_fields(self, key, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError(f"{key} must be valid JSON")
        return value

class Customer(SQLBase, BaseSQLModel):
    """Customer model for SQL databases"""
    __tablename__ = "customers"
    
    name = Column(String(200), nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    customer_since = Column(Date, default=func.current_date())
    loyalty_tier = Column(String(50), default="standard")
    preferences = Column(JSON, default=dict)
    total_spent = Column(Numeric(12, 2), default=0)
    order_count = Column(Integer, default=0)
    active = Column(Boolean, default=True, index=True)
    
    # Relationships
    orders = relationship("Order", back_populates="customer")
    reviews = relationship("Review", back_populates="customer")
    
    __table_args__ = (
        Index('idx_customer_email_active', 'email', 'active'),
        Index('idx_customer_city_country', 'city', 'country'),
    )

class Order(SQLBase, BaseSQLModel):
    """Order model for SQL databases"""
    __tablename__ = "orders"
    
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    order_date = Column(Date, nullable=False, index=True)
    total_amount = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0)
    shipping_cost = Column(Numeric(10, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    final_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(50), default="pending", index=True)
    shipping_address = Column(Text)
    shipping_city = Column(String(100))
    shipping_state = Column(String(100))
    shipping_country = Column(String(100))
    shipping_postal_code = Column(String(20))
    payment_method = Column(String(50))
    payment_status = Column(String(50), default="pending", index=True)
    notes = Column(Text)
    
    # Relationships
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")
    
    __table_args__ = (
        Index('idx_order_date_status', 'order_date', 'status'),
        Index('idx_order_customer_date', 'customer_id', 'order_date'),
        Index('idx_order_status_payment', 'status', 'payment_status'),
    )

class OrderItem(SQLBase, BaseSQLModel):
    """Order item model for SQL databases"""
    __tablename__ = "order_items"
    
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    
    __table_args__ = (
        Index('idx_order_item_product', 'order_id', 'product_id'),
        Index('idx_order_item_price', 'unit_price'),
    )

class Category(SQLBase, BaseSQLModel):
    """Category model for SQL databases"""
    __tablename__ = "categories"
    
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey("categories.id"))
    products_count = Column(Integer, default=0)
    active = Column(Boolean, default=True, index=True)
    
    # Relationships
    parent = relationship("Category", remote_side="Category.id", backref="subcategories")
    
    __table_args__ = (
        Index('idx_category_parent_active', 'parent_id', 'active'),
    )

class Review(SQLBase, BaseSQLModel):
    """Review model for SQL databases"""
    __tablename__ = "reviews"
    
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5
    title = Column(String(200))
    comment = Column(Text)
    verified_purchase = Column(Boolean, default=False)
    helpful_votes = Column(Integer, default=0)
    
    # Relationships
    product = relationship("Product", back_populates="reviews")
    customer = relationship("Customer", back_populates="reviews")
    
    __table_args__ = (
        Index('idx_review_product_rating', 'product_id', 'rating'),
        Index('idx_review_customer_product', 'customer_id', 'product_id'),
        Index('idx_review_verified_rating', 'verified_purchase', 'rating'),
    )

class Inventory(SQLBase, BaseSQLModel):
    """Inventory model for SQL databases"""
    __tablename__ = "inventory"
    
    product_id = Column(Integer, ForeignKey("products.id"), unique=True, nullable=False, index=True)
    quantity = Column(Integer, default=0, nullable=False)
    low_stock_threshold = Column(Integer, default=10, nullable=False)
    warehouse_location = Column(String(100))
    last_restocked = Column(DateTime)
    reorder_point = Column(Integer, default=20, nullable=False)
    reorder_quantity = Column(Integer, default=50, nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="inventory")
    
    __table_args__ = (
        Index('idx_inventory_quantity', 'quantity'),
        Index('idx_inventory_warehouse', 'warehouse_location'),
        Index('idx_inventory_low_stock', 'quantity', 'low_stock_threshold'),
    )

# Additional utility models
class ProductCategory(SQLBase):
    """Many-to-many relationship between products and categories"""
    __tablename__ = "product_categories"
    
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_product_category', 'product_id', 'category_id'),
    )

# Pydantic schemas for SQL models
class ProductCreate(BaseSQLModel):
    name: str
    category: str
    price: float
    description: Optional[str] = None
    sku: str
    stock_quantity: int = 0
    brand: Optional[str] = None
    attributes: Dict[str, Any] = {}
    tags: List[str] = []
    active: bool = True

class CustomerCreate(BaseSQLModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    preferences: Dict[str, Any] = {}

class OrderCreate(BaseSQLModel):
    customer_id: int
    items: List[Dict[str, Any]]
    shipping_address: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None

# Database initialization functions
async def create_sql_tables(engine):
    """Create all SQL tables"""
    try:
        # First try to create tables using SQLAlchemy metadata
        async with engine.begin() as conn:
            await conn.run_sync(SQLBase.metadata.create_all)
        
        print("✅ SQL tables created successfully")
        
        # Also create indexes
        async with engine.connect() as conn:
            # Create additional indexes that aren't in the model definitions
            index_queries = [
                "CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);",
                "CREATE INDEX IF NOT EXISTS idx_customers_active ON customers(active);",
                "CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);",
                "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);",
                "CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);",
                "CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);",
                "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);",
                "CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);",
                "CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);",
                "CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id);",
                "CREATE INDEX IF NOT EXISTS idx_reviews_customer_id ON reviews(customer_id);",
                "CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);",
            ]
            
            for query in index_queries:
                try:
                    await conn.execute(text(query))
                    await conn.commit()
                except Exception as e:
                    print(f"⚠️ Could not create index: {e}")
                    await conn.rollback()
                    continue
            
        print("✅ Database indexes created")
        
    except Exception as e:
        print(f"❌ Error creating tables with metadata: {e}")
        
        # Fallback: create tables using raw SQL
        try:
            await _create_tables_with_raw_sql(engine)
        except Exception as sql_error:
            print(f"❌ Error creating tables with raw SQL: {sql_error}")
            raise

async def _create_tables_with_raw_sql(engine):
    """Create tables using raw SQL as fallback"""
    print("🔄 Creating tables using raw SQL...")
    
    async with engine.connect() as conn:
        # Create tables using raw SQL
        tables_sql = [
            # Drop tables if they exist first
            "DROP TABLE IF EXISTS inventory CASCADE;",
            "DROP TABLE IF EXISTS reviews CASCADE;",
            "DROP TABLE IF EXISTS order_items CASCADE;",
            "DROP TABLE IF EXISTS orders CASCADE;",
            "DROP TABLE IF EXISTS products CASCADE;",
            "DROP TABLE IF EXISTS customers CASCADE;",
            "DROP TABLE IF EXISTS categories CASCADE;",
            "DROP TABLE IF EXISTS product_categories CASCADE;",
            
            # Customers table
            """
            CREATE TABLE customers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                email VARCHAR(200) UNIQUE NOT NULL,
                phone VARCHAR(20),
                address TEXT,
                city VARCHAR(100),
                state VARCHAR(100),
                country VARCHAR(100),
                postal_code VARCHAR(20),
                customer_since DATE DEFAULT CURRENT_DATE,
                loyalty_tier VARCHAR(50) DEFAULT 'standard',
                preferences JSONB DEFAULT '{}',
                total_spent DECIMAL(12,2) DEFAULT 0,
                order_count INTEGER DEFAULT 0,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # Products table
            """
            CREATE TABLE products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                category VARCHAR(100) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                original_price DECIMAL(10,2),
                description TEXT,
                sku VARCHAR(50) UNIQUE NOT NULL,
                stock_quantity INTEGER DEFAULT 0,
                low_stock_threshold INTEGER DEFAULT 10,
                brand VARCHAR(100),
                attributes JSONB DEFAULT '{}',
                tags JSONB DEFAULT '[]',
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # Orders table
            """
            CREATE TABLE orders (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(id),
                order_date DATE NOT NULL,
                total_amount DECIMAL(12,2) NOT NULL,
                tax_amount DECIMAL(10,2) DEFAULT 0,
                shipping_cost DECIMAL(10,2) DEFAULT 0,
                discount_amount DECIMAL(10,2) DEFAULT 0,
                final_amount DECIMAL(12,2) NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                shipping_address TEXT,
                shipping_city VARCHAR(100),
                shipping_state VARCHAR(100),
                shipping_country VARCHAR(100),
                shipping_postal_code VARCHAR(20),
                payment_method VARCHAR(50),
                payment_status VARCHAR(50) DEFAULT 'pending',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # Order items table
            """
            CREATE TABLE order_items (
                id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(id),
                product_id INTEGER REFERENCES products(id),
                product_name VARCHAR(200) NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                total_price DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # Reviews table
            """
            CREATE TABLE reviews (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id),
                customer_id INTEGER REFERENCES customers(id),
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                title VARCHAR(200),
                comment TEXT,
                verified_purchase BOOLEAN DEFAULT FALSE,
                helpful_votes INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            
            # Inventory table
            """
            CREATE TABLE inventory (
                id SERIAL PRIMARY KEY,
                product_id INTEGER UNIQUE REFERENCES products(id),
                quantity INTEGER NOT NULL DEFAULT 0,
                low_stock_threshold INTEGER NOT NULL DEFAULT 10,
                warehouse_location VARCHAR(100),
                last_restocked TIMESTAMP,
                reorder_point INTEGER NOT NULL DEFAULT 20,
                reorder_quantity INTEGER NOT NULL DEFAULT 50,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        ]
        
        for sql in tables_sql:
            try:
                await conn.execute(text(sql))
                await conn.commit()
                print(f"✅ Executed SQL successfully")
            except Exception as e:
                print(f"⚠️ Could not execute SQL: {e}")
                await conn.rollback()
                continue
        
        print("✅ SQL tables created successfully with raw SQL")

async def drop_sql_tables(engine):
    """Drop all SQL tables"""
    SQLBase.metadata.drop_all(bind=engine)
    print("✅ SQL tables dropped")

async def reset_sql_database(engine):
    """Reset database by dropping and recreating tables"""
    await drop_sql_tables(engine)
    await create_sql_tables(engine)
    print("✅ SQL database reset complete")