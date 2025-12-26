import asyncio
import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent))

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_mongodb():
    """Setup MongoDB with sample data"""
    
    connection_url = "mongodb://localhost:27017/analytics_db"
    
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(connection_url)
        db = client["analytics_db"]
        
        # Test connection
        await client.admin.command('ping')
        logger.info("✅ Connected to MongoDB")
        
        # Drop existing collections (optional - remove if you want to keep data)
        collections = await db.list_collection_names()
        if collections:
            logger.info(f"📊 Existing collections: {collections}")
            # Uncomment to reset:
            # for collection in collections:
            #     await db.drop_collection(collection)
            # logger.info("🧹 Dropped existing collections")
        
        # Create sample data
        from datetime import datetime, timedelta
        
        # Sample customers
        customers = [
            {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+1234567890",
                "city": "New York",
                "country": "USA",
                "loyalty_points": 150,
                "total_spent": 2500.00,
                "order_count": 5,
                "active": True,
                "created_at": datetime.now() - timedelta(days=365),
                "updated_at": datetime.now()
            },
            {
                "name": "Jane Smith",
                "email": "jane@example.com",
                "phone": "+1987654321",
                "city": "London",
                "country": "UK",
                "loyalty_points": 250,
                "total_spent": 1800.00,
                "order_count": 3,
                "active": True,
                "created_at": datetime.now() - timedelta(days=200),
                "updated_at": datetime.now()
            },
            {
                "name": "Bob Johnson",
                "email": "bob@example.com",
                "phone": "+1122334455",
                "city": "Sydney",
                "country": "Australia",
                "loyalty_points": 75,
                "total_spent": 1200.00,
                "order_count": 2,
                "active": True,
                "created_at": datetime.now() - timedelta(days=100),
                "updated_at": datetime.now()
            },
            {
                "name": "Alice Brown",
                "email": "alice@example.com",
                "phone": "+1555666777",
                "city": "Toronto",
                "country": "Canada",
                "loyalty_points": 300,
                "total_spent": 3200.00,
                "order_count": 7,
                "active": True,
                "created_at": datetime.now() - timedelta(days=150),
                "updated_at": datetime.now()
            },
            {
                "name": "Charlie Wilson",
                "email": "charlie@example.com",
                "phone": "+1444333222",
                "city": "Berlin",
                "country": "Germany",
                "loyalty_points": 180,
                "total_spent": 2100.00,
                "order_count": 4,
                "active": True,
                "created_at": datetime.now() - timedelta(days=80),
                "updated_at": datetime.now()
            }
        ]
        
        # Insert customers
        result = await db.customers.insert_many(customers)
        customer_ids = result.inserted_ids
        logger.info(f"✅ Inserted {len(customer_ids)} customers")
        
        # Sample products
        products = [
            {
                "name": "Laptop Pro",
                "category": "Electronics",
                "price": 1299.99,
                "sku": "LP-1001",
                "stock_quantity": 50,
                "description": "High-performance laptop with 16GB RAM, 512GB SSD",
                "attributes": {"brand": "TechCorp", "ram": "16GB", "storage": "512GB SSD", "screen": "15.6 inch"},
                "tags": ["laptop", "electronics", "computer", "gaming"],
                "active": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "name": "Wireless Mouse",
                "category": "Electronics",
                "price": 49.99,
                "sku": "WM-2001",
                "stock_quantity": 200,
                "description": "Ergonomic wireless mouse with long battery life",
                "attributes": {"brand": "PeriTech", "color": "Black", "wireless": True, "battery": "12 months"},
                "tags": ["mouse", "electronics", "accessories", "wireless"],
                "active": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "name": "Office Chair",
                "category": "Furniture",
                "price": 299.99,
                "sku": "OC-3001",
                "stock_quantity": 30,
                "description": "Comfortable office chair with lumbar support",
                "attributes": {"brand": "ComfySeat", "material": "Leather", "adjustable": True, "weight": "25kg"},
                "tags": ["chair", "furniture", "office", "ergonomic"],
                "active": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "name": "Coffee Maker",
                "category": "Home Appliances",
                "price": 89.99,
                "sku": "CM-4001",
                "stock_quantity": 75,
                "description": "Automatic coffee maker with timer",
                "attributes": {"brand": "BrewMaster", "capacity": "12 cups", "auto_off": True},
                "tags": ["coffee", "appliance", "kitchen", "home"],
                "active": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            },
            {
                "name": "Desk Lamp",
                "category": "Home & Office",
                "price": 39.99,
                "sku": "DL-5001",
                "stock_quantity": 120,
                "description": "LED desk lamp with adjustable brightness",
                "attributes": {"brand": "LightPro", "led": True, "adjustable": True, "color_temp": "3000K-6000K"},
                "tags": ["lamp", "lighting", "desk", "led"],
                "active": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        ]
        
        # Insert products
        result = await db.products.insert_many(products)
        product_ids = result.inserted_ids
        product_docs = await db.products.find({}, {"_id": 1, "name": 1, "price": 1}).to_list(length=5)
        logger.info(f"✅ Inserted {len(product_ids)} products")
        
        # Sample orders (spread across last 3 months)
        orders = []
        today = datetime.now()
        
        # Create orders for each customer
        for i, customer_id in enumerate(customer_ids):
            customer_name = customers[i]["name"]
            
            # 1-3 orders per customer
            for j in range(1, 4):
                order_date = today - timedelta(days=30 * j + i*5)
                
                # Select 1-3 random products
                import random
                selected_products = random.sample(product_docs, random.randint(1, 3))
                
                items = []
                total_amount = 0
                
                for product in selected_products:
                    quantity = random.randint(1, 3)
                    unit_price = product["price"]
                    item_total = unit_price * quantity
                    
                    items.append({
                        "product_id": product["_id"],
                        "product_name": product["name"],
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "total_price": item_total
                    })
                    
                    total_amount += item_total
                
                # Add some variation to order dates
                order_date = order_date - timedelta(days=random.randint(0, 10))
                
                order = {
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                    "order_date": order_date,
                    "total_amount": round(total_amount, 2),
                    "tax_amount": round(total_amount * 0.08, 2),
                    "shipping_cost": 9.99 if total_amount < 100 else 0,
                    "final_amount": round(total_amount + (total_amount * 0.08) + (9.99 if total_amount < 100 else 0), 2),
                    "status": "completed",
                    "payment_status": "paid",
                    "payment_method": random.choice(["credit_card", "paypal", "bank_transfer"]),
                    "items": items,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                
                orders.append(order)
        
        # Insert orders
        await db.orders.insert_many(orders)
        logger.info(f"✅ Inserted {len(orders)} orders")
        
        # Create indexes
        await db.customers.create_index("email", unique=True)
        await db.products.create_index("sku", unique=True)
        await db.orders.create_index("customer_id")
        await db.orders.create_index("order_date")
        await db.orders.create_index([("order_date", -1)])
        
        logger.info("✅ Created database indexes")
        
        # Verify data
        customer_count = await db.customers.count_documents({})
        product_count = await db.products.count_documents({})
        order_count = await db.orders.count_documents({})
        
        logger.info(f"📊 Database Stats:")
        logger.info(f"  - Customers: {customer_count}")
        logger.info(f"  - Products: {product_count}")
        logger.info(f"  - Orders: {order_count}")
        
        # Sample query test
        pipeline = [
            {"$match": {
                "order_date": {
                    "$gte": today - timedelta(days=30),
                    "$lt": today
                }
            }},
            {"$group": {
                "_id": None,
                "total_revenue": {"$sum": "$total_amount"},
                "order_count": {"$sum": 1}
            }}
        ]
        
        result = await db.orders.aggregate(pipeline).to_list(length=1)
        if result:
            logger.info(f"💰 Last month's revenue: ${result[0].get('total_revenue', 0):.2f}")
        
        logger.info("✅ MongoDB setup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ MongoDB setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(setup_mongodb())