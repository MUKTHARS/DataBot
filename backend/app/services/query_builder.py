import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueryBuilder:
    """Builds optimized queries for different databases"""
    
    def __init__(self):
        self.query_templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """Load query templates for different intents"""
        return {
            "sales_analysis": {
                "postgres": """
                    SELECT 
                        DATE_TRUNC('{timeframe}', order_date) as period,
                        COUNT(*) as order_count,
                        SUM(total_amount) as total_revenue,
                        AVG(total_amount) as avg_order_value,
                        COUNT(DISTINCT customer_id) as unique_customers
                    FROM orders
                    WHERE order_date BETWEEN '{start_date}' AND '{end_date}'
                    AND status = 'completed'
                    GROUP BY DATE_TRUNC('{timeframe}', order_date)
                    ORDER BY period
                """,
                "mongodb": """
                    [
                        {{
                            "$match": {{
                                "order_date": {{
                                    "$gte": "{start_date}",
                                    "$lte": "{end_date}"
                                }},
                                "status": "completed"
                            }}
                        }},
                        {{
                            "$group": {{
                                "_id": {{
                                    "$dateTrunc": {{
                                        "date": {{ "$dateFromString": {{ "dateString": "$order_date" }} }},
                                        "unit": "{timeframe}"
                                    }}
                                }},
                                "order_count": {{ "$sum": 1 }},
                                "total_revenue": {{ "$sum": "$total_amount" }},
                                "avg_order_value": {{ "$avg": "$total_amount" }},
                                "unique_customers": {{ "$addToSet": "$customer_id" }}
                            }}
                        }},
                        {{
                            "$project": {{
                                "period": "$_id",
                                "order_count": 1,
                                "total_revenue": 1,
                                "avg_order_value": 1,
                                "unique_customers": {{ "$size": "$unique_customers" }}
                            }}
                        }},
                        {{ "$sort": {{ "period": 1 }} }}
                    ]
                """
            },
            "customer_analysis": {
                "postgres": """
                    SELECT 
                        c.id,
                        c.name,
                        c.email,
                        COUNT(o.id) as order_count,
                        SUM(o.total_amount) as total_spent,
                        MAX(o.order_date) as last_order_date,
                        AVG(o.total_amount) as avg_order_value
                    FROM customers c
                    LEFT JOIN orders o ON c.id = o.customer_id
                    WHERE o.status = 'completed' OR o.id IS NULL
                    GROUP BY c.id, c.name, c.email
                    ORDER BY total_spent DESC NULLS LAST
                    LIMIT {limit}
                """,
                "mongodb": """
                    [
                        {{
                            "$lookup": {{
                                "from": "orders",
                                "localField": "_id",
                                "foreignField": "customer_id",
                                "as": "orders",
                                "pipeline": [
                                    {{ "$match": {{ "status": "completed" }} }}
                                ]
                            }}
                        }},
                        {{
                            "$project": {{
                                "name": 1,
                                "email": 1,
                                "order_count": {{ "$size": "$orders" }},
                                "total_spent": {{ "$sum": "$orders.total_amount" }},
                                "last_order_date": {{ "$max": "$orders.order_date" }},
                                "avg_order_value": {{
                                    "$cond": {{
                                        "if": {{ "$gt": [{{ "$size": "$orders" }}, 0] }},
                                        "then": {{ "$avg": "$orders.total_amount" }},
                                        "else": 0
                                    }}
                                }}
                            }}
                        }},
                        {{ "$sort": {{ "total_spent": -1 }} }},
                        {{ "$limit": {limit} }}
                    ]
                """
            },
            "product_analysis": {
                "postgres": """
                    SELECT 
                        p.id,
                        p.name,
                        p.category,
                        p.price,
                        COUNT(oi.id) as times_ordered,
                        SUM(oi.quantity) as total_quantity,
                        SUM(oi.quantity * oi.unit_price) as total_revenue
                    FROM products p
                    LEFT JOIN order_items oi ON p.id = oi.product_id
                    LEFT JOIN orders o ON oi.order_id = o.id AND o.status = 'completed'
                    GROUP BY p.id, p.name, p.category, p.price
                    ORDER BY total_revenue DESC NULLS LAST
                    LIMIT {limit}
                """,
                "mongodb": """
                    [
                        {{
                            "$lookup": {{
                                "from": "order_items",
                                "localField": "_id",
                                "foreignField": "product_id",
                                "as": "order_items"
                            }}
                        }},
                        {{
                            "$lookup": {{
                                "from": "orders",
                                "localField": "order_items.order_id",
                                "foreignField": "_id",
                                "as": "orders",
                                "pipeline": [
                                    {{ "$match": {{ "status": "completed" }} }}
                                ]
                            }}
                        }},
                        {{
                            "$project": {{
                                "name": 1,
                                "category": 1,
                                "price": 1,
                                "times_ordered": {{ "$size": "$order_items" }},
                                "total_quantity": {{ "$sum": "$order_items.quantity" }},
                                "total_revenue": {{
                                    "$sum": {{
                                        "$map": {{
                                            "input": "$order_items",
                                            "as": "item",
                                            "in": {{ "$multiply": ["$$item.quantity", "$$item.unit_price"] }}
                                        }}
                                    }}
                                }}
                            }}
                        }},
                        {{ "$sort": {{ "total_revenue": -1 }} }},
                        {{ "$limit": {limit} }}
                    ]
                """
            }
        }
    
    def build_query(
        self, 
        intent: str, 
        database_type: str,
        parameters: Dict[str, Any]
    ) -> str:
        """Build query based on intent and database type"""
        try:
            if intent not in self.query_templates:
                raise ValueError(f"No template for intent: {intent}")
            
            if database_type not in self.query_templates[intent]:
                raise ValueError(f"No template for {database_type} with intent: {intent}")
            
            template = self.query_templates[intent][database_type]
            
            # Format template with parameters
            query = template.format(**parameters)
            
            logger.info(f"🔧 Built query for {intent} on {database_type}")
            return query
            
        except Exception as e:
            logger.error(f"❌ Query building failed: {e}")
            raise
    
    def build_custom_query(
        self,
        database_type: str,
        table: str,
        columns: List[str],
        filters: Dict[str, Any],
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """Build custom SELECT query"""
        try:
            if database_type in ["postgres", "mysql"]:
                return self._build_sql_query(table, columns, filters, order_by, limit)
            elif database_type == "mongodb":
                return self._build_mongo_query(table, columns, filters, order_by, limit)
            else:
                raise ValueError(f"Unsupported database type: {database_type}")
                
        except Exception as e:
            logger.error(f"❌ Custom query building failed: {e}")
            raise
    
    def _build_sql_query(
        self,
        table: str,
        columns: List[str],
        filters: Dict[str, Any],
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """Build SQL SELECT query"""
        # Build SELECT clause
        if columns == ["*"]:
            select_clause = "*"
        else:
            select_clause = ", ".join([f'"{col}"' for col in columns])
        
        # Build WHERE clause
        where_conditions = []
        params = {}
        param_index = 0
        
        for field, value in filters.items():
            if isinstance(value, dict) and "operator" in value:
                op = value["operator"]
                val = value["value"]
                
                if op in ["=", "!=", ">", "<", ">=", "<=", "LIKE", "IN"]:
                    where_conditions.append(f'"{field}" {op} :param_{param_index}')
                    params[f"param_{param_index}"] = val
                    param_index += 1
            else:
                where_conditions.append(f'"{field}" = :param_{param_index}')
                params[f"param_{param_index}"] = value
                param_index += 1
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
        
        # Build ORDER BY clause
        order_clause = f"ORDER BY {order_by}" if order_by else ""
        
        # Build LIMIT clause
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        # Build final query
        query = f'SELECT {select_clause} FROM "{table}" {where_clause} {order_clause} {limit_clause}'.strip()
        
        return query
    
    def _build_mongo_query(
        self,
        collection: str,
        fields: List[str],
        filters: Dict[str, Any],
        sort_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> str:
        """Build MongoDB find query as JSON string"""
        import json
        
        # Build projection
        projection = {}
        if fields != ["*"]:
            for field in fields:
                projection[field] = 1
        
        # Build filter
        mongo_filter = {}
        for field, value in filters.items():
            if isinstance(value, dict) and "operator" in value:
                op = value["operator"]
                val = value["value"]
                
                if op == "=":
                    mongo_filter[field] = val
                elif op == ">":
                    mongo_filter[field] = {"$gt": val}
                elif op == "<":
                    mongo_filter[field] = {"$lt": val}
                elif op == ">=":
                    mongo_filter[field] = {"$gte": val}
                elif op == "<=":
                    mongo_filter[field] = {"$lte": val}
                elif op == "!=":
                    mongo_filter[field] = {"$ne": val}
            else:
                mongo_filter[field] = value
        
        # Build find command
        find_command = {
            "find": collection,
            "filter": mongo_filter
        }
        
        if projection:
            find_command["projection"] = projection
        
        if sort_by:
            find_command["sort"] = {sort_by: 1}
        
        if limit:
            find_command["limit"] = limit
        
        return json.dumps(find_command)
    
    def optimize_query(self, query: str, database_type: str) -> str:
        """Optimize query for performance"""
        # This is a simplified optimization
        # In production, you'd want more sophisticated optimization
        
        if database_type in ["postgres", "mysql"]:
            # Add EXPLAIN to analyze (for debugging)
            return query
        
        elif database_type == "mongodb":
            # For MongoDB, ensure proper indexes are suggested
            return query
        
        return query
    
    def validate_query(self, query: str, database_type: str) -> bool:
        """Validate query for safety and syntax"""
        # Check for dangerous patterns
        dangerous_patterns = [
            r"\bDROP\b",
            r"\bDELETE\b.*\bFROM\b",
            r"\bTRUNCATE\b",
            r"\bALTER\b.*\bTABLE\b",
            r"\bCREATE\b.*\bTABLE\b",
            r"\bINSERT\b.*\bINTO\b",
            r"\bUPDATE\b.*\bSET\b",
            r"\bGRANT\b",
            r"\bREVOKE\b",
            r";\s*$"
        ]
        
        query_upper = query.upper()
        for pattern in dangerous_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                logger.warning(f"⚠️ Dangerous query detected: {pattern}")
                return False
        
        # Basic syntax check (simplified)
        if database_type in ["postgres", "mysql"]:
            if not query.strip().upper().startswith("SELECT"):
                logger.warning("⚠️ Only SELECT queries are allowed")
                return False
        
        return True