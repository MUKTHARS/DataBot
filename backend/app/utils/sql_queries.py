"""Common SQL queries for the application"""

CREATE_TABLES_QUERIES = {
    "postgres": [
        """
        CREATE TABLE IF NOT EXISTS customers (
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
        """
        CREATE TABLE IF NOT EXISTS products (
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
        """
        CREATE TABLE IF NOT EXISTS orders (
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
        """
        CREATE TABLE IF NOT EXISTS order_items (
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
        """
        CREATE TABLE IF NOT EXISTS reviews (
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
        """
        CREATE TABLE IF NOT EXISTS inventory (
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
    ],
    "mysql": [
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            email VARCHAR(200) UNIQUE NOT NULL,
            phone VARCHAR(20),
            address TEXT,
            city VARCHAR(100),
            state VARCHAR(100),
            country VARCHAR(100),
            postal_code VARCHAR(20),
            customer_since DATE DEFAULT (CURRENT_DATE),
            loyalty_tier VARCHAR(50) DEFAULT 'standard',
            preferences JSON,
            total_spent DECIMAL(12,2) DEFAULT 0,
            order_count INT DEFAULT 0,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );
        """,
        # Similar CREATE TABLE statements for MySQL...
    ]
}

SAMPLE_DATA_QUERIES = {
    "postgres": [
        # Customers
        """
        INSERT INTO customers (name, email, phone, city, country) 
        VALUES 
        ('John Doe', 'john@example.com', '+1234567890', 'New York', 'USA'),
        ('Jane Smith', 'jane@example.com', '+1987654321', 'London', 'UK'),
        ('Bob Johnson', 'bob@example.com', '+1122334455', 'Sydney', 'Australia')
        ON CONFLICT (email) DO NOTHING;
        """,
        # Products
        """
        INSERT INTO products (name, category, price, sku, stock_quantity, description) 
        VALUES 
        ('Laptop Pro', 'Electronics', 1299.99, 'LP-1001', 50, 'High-performance laptop'),
        ('Wireless Mouse', 'Electronics', 49.99, 'WM-2001', 200, 'Ergonomic wireless mouse'),
        ('Office Chair', 'Furniture', 299.99, 'OC-3001', 30, 'Comfortable office chair')
        ON CONFLICT (sku) DO NOTHING;
        """,
        # Orders
        """
        INSERT INTO orders (customer_id, order_date, total_amount, status, payment_status) 
        VALUES 
        (1, '2024-01-15', 1349.98, 'completed', 'paid'),
        (2, '2024-01-20', 89.98, 'completed', 'paid'),
        (3, '2024-02-05', 299.99, 'processing', 'paid')
        ON CONFLICT DO NOTHING;
        """,
        # Order Items
        """
        INSERT INTO order_items (order_id, product_id, product_name, quantity, unit_price, total_price) 
        VALUES 
        (1, 1, 'Laptop Pro', 1, 1299.99, 1299.99),
        (1, 2, 'Wireless Mouse', 1, 49.99, 49.99),
        (2, 2, 'Wireless Mouse', 1, 49.99, 49.99),
        (3, 3, 'Office Chair', 1, 299.99, 299.99)
        ON CONFLICT DO NOTHING;
        """
    ]
}

COMMON_ANALYTICS_QUERIES = {
    "top_customers": """
        SELECT 
            c.id,
            c.name,
            c.email,
            COUNT(o.id) as order_count,
            SUM(o.total_amount) as total_spent,
            MAX(o.order_date) as last_order_date
        FROM customers c
        LEFT JOIN orders o ON c.id = o.customer_id
        GROUP BY c.id, c.name, c.email
        ORDER BY total_spent DESC NULLS LAST
        LIMIT 10;
    """,
    "top_products": """
        SELECT 
            p.id,
            p.name,
            p.category,
            p.price,
            SUM(oi.quantity) as total_quantity,
            SUM(oi.total_price) as total_revenue
        FROM products p
        LEFT JOIN order_items oi ON p.id = oi.product_id
        LEFT JOIN orders o ON oi.order_id = o.id
        GROUP BY p.id, p.name, p.category, p.price
        ORDER BY total_revenue DESC NULLS LAST
        LIMIT 10;
    """,
    "sales_by_month": """
        SELECT 
            DATE_TRUNC('month', order_date) as month,
            COUNT(*) as order_count,
            SUM(total_amount) as total_revenue,
            AVG(total_amount) as avg_order_value
        FROM orders
        WHERE status = 'completed'
        GROUP BY DATE_TRUNC('month', order_date)
        ORDER BY month DESC
        LIMIT 12;
    """,
    "customer_geography": """
        SELECT 
            country,
            city,
            COUNT(*) as customer_count,
            SUM(total_spent) as total_spent
        FROM customers
        WHERE active = TRUE
        GROUP BY country, city
        ORDER BY total_spent DESC;
    """,
    "product_categories": """
        SELECT 
            category,
            COUNT(*) as product_count,
            AVG(price) as avg_price,
            SUM(stock_quantity) as total_stock
        FROM products
        WHERE active = TRUE
        GROUP BY category
        ORDER BY product_count DESC;
    """
}

async def create_database_tables(db_manager):
    """Create all necessary database tables"""
    try:
        db_type = db_manager.db_type
        if db_type in CREATE_TABLES_QUERIES:
            queries = CREATE_TABLES_QUERIES[db_type]
            for query in queries:
                try:
                    await db_manager.execute_query(query)
                except Exception as e:
                    print(f"⚠️ Could not execute query: {e}")
            print(f"✅ Created tables for {db_type}")
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")

async def insert_sample_data(db_manager):
    """Insert sample data into the database"""
    try:
        db_type = db_manager.db_type
        if db_type in SAMPLE_DATA_QUERIES:
            queries = SAMPLE_DATA_QUERIES[db_type]
            for query in queries:
                try:
                    await db_manager.execute_query(query)
                except Exception as e:
                    print(f"⚠️ Could not insert sample data: {e}")
            print(f"✅ Inserted sample data for {db_type}")
    except Exception as e:
        print(f"❌ Failed to insert sample data: {e}")