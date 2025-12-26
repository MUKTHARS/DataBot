from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from pydantic import Field, BaseModel, ConfigDict
import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase

from .base import BaseMongoModel, TimeStampedModel

# Custom ObjectId type for Pydantic
class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string", format="objectid")

# MongoDB Models for common entities
class ProductDocument(BaseMongoModel):
    """Product document for MongoDB"""
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    sku: str = Field(..., min_length=1, max_length=50)
    stock_quantity: int = Field(default=0, ge=0)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    active: bool = Field(default=True)

class CustomerDocument(BaseMongoModel):
    """Customer document for MongoDB"""
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=1, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    loyalty_points: int = Field(default=0, ge=0)
    active: bool = Field(default=True)

class OrderItemDocument(BaseMongoModel):
    """Order item document for MongoDB"""
    product_id: PyObjectId
    product_name: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    total_price: float = Field(..., gt=0)

class OrderDocument(BaseMongoModel):
    """Order document for MongoDB"""
    customer_id: PyObjectId
    order_date: datetime = Field(default_factory=datetime.utcnow)
    total_amount: float = Field(..., gt=0)
    status: str = Field(default="pending", pattern="^(pending|processing|shipped|delivered|cancelled)$")
    shipping_address: Optional[str] = None
    payment_method: Optional[str] = None
    payment_status: str = Field(default="pending", pattern="^(pending|paid|failed|refunded)$")
    items: List[OrderItemDocument] = Field(default_factory=list)
    notes: Optional[str] = None

class CategoryDocument(BaseMongoModel):
    """Category document for MongoDB"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    parent_category: Optional[PyObjectId] = None
    products_count: int = Field(default=0, ge=0)
    active: bool = Field(default=True)

class ReviewDocument(BaseMongoModel):
    """Review document for MongoDB"""
    product_id: PyObjectId
    customer_id: PyObjectId
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None
    verified_purchase: bool = Field(default=False)

class InventoryDocument(BaseMongoModel):
    """Inventory document for MongoDB"""
    product_id: PyObjectId
    quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)
    warehouse_location: Optional[str] = None
    last_restocked: Optional[datetime] = None
    reorder_point: int = Field(default=20, ge=0)

# Index definitions for MongoDB collections
MONGO_INDEXES = {
    "products": [
        pymongo.IndexModel([("name", pymongo.TEXT)], name="name_text"),
        pymongo.IndexModel([("category", 1)], name="category_idx"),
        pymongo.IndexModel([("price", 1)], name="price_idx"),
        pymongo.IndexModel([("sku", 1)], name="sku_idx", unique=True),
        pymongo.IndexModel([("active", 1)], name="active_idx"),
    ],
    "customers": [
        pymongo.IndexModel([("email", 1)], name="email_idx", unique=True),
        pymongo.IndexModel([("name", 1)], name="name_idx"),
        pymongo.IndexModel([("city", 1)], name="city_idx"),
        pymongo.IndexModel([("active", 1)], name="active_idx"),
    ],
    "orders": [
        pymongo.IndexModel([("customer_id", 1)], name="customer_idx"),
        pymongo.IndexModel([("order_date", -1)], name="order_date_idx"),
        pymongo.IndexModel([("status", 1)], name="status_idx"),
        pymongo.IndexModel([("total_amount", -1)], name="total_amount_idx"),
    ],
    "categories": [
        pymongo.IndexModel([("name", 1)], name="name_idx", unique=True),
        pymongo.IndexModel([("parent_category", 1)], name="parent_idx"),
        pymongo.IndexModel([("active", 1)], name="active_idx"),
    ],
    "reviews": [
        pymongo.IndexModel([("product_id", 1)], name="product_idx"),
        pymongo.IndexModel([("customer_id", 1)], name="customer_idx"),
        pymongo.IndexModel([("rating", -1)], name="rating_idx"),
    ],
    "inventory": [
        pymongo.IndexModel([("product_id", 1)], name="product_idx", unique=True),
        pymongo.IndexModel([("quantity", 1)], name="quantity_idx"),
        pymongo.IndexModel([("warehouse_location", 1)], name="warehouse_idx"),
    ]
}

async def create_mongo_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for MongoDB collections"""
    for collection_name, indexes in MONGO_INDEXES.items():
        try:
            await db[collection_name].create_indexes(indexes)
            print(f"✅ Created indexes for collection: {collection_name}")
        except Exception as e:
            print(f"⚠️ Failed to create indexes for {collection_name}: {e}")

# Helper functions for MongoDB
def convert_objectid(data: Any):
    """Convert ObjectId to string in nested data structures"""
    if isinstance(data, list):
        return [convert_objectid(item) for item in data]
    elif isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if key == "_id" and isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, (dict, list)):
                result[key] = convert_objectid(value)
            else:
                result[key] = value
        return result
    else:
        return data

def prepare_mongo_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare document for MongoDB insertion"""
    # Remove None values
    document = {k: v for k, v in document.items() if v is not None}
    
    # Convert datetime to ISO format
    for key, value in document.items():
        if isinstance(value, datetime):
            document[key] = value.isoformat()
    
    return document