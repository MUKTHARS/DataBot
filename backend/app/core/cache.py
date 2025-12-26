import asyncio
import logging
import pickle
from typing import Any, Optional
from datetime import datetime, timedelta
import redis.asyncio as redis
from typing import Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching for query results and responses"""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = bool(settings.REDIS_URL)
        self.default_ttl = settings.CACHE_TTL
        self.size = 0
    
    async def initialize(self) -> bool:
        """Initialize cache connection"""
        try:
            if not self.enabled:
                logger.info("ℹ️ Cache disabled (no Redis URL configured)")
                return True
            
            logger.info("🔄 Initializing cache...")
            
            # Create Redis client
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False
            )
            
            # Test connection
            await self.redis_client.ping()
            
            # Get cache info
            info = await self.redis_client.info()
            self.size = info.get('used_memory', 0)
            
            logger.info(f"✅ Cache initialized: {self.size} bytes used")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache initialization failed: {e}")
            self.enabled = False
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                logger.debug(f"💾 Cache hit: {key}")
                return pickle.loads(value)
            return None
        except Exception as e:
            logger.error(f"❌ Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized = pickle.dumps(value)
            
            await self.redis_client.setex(key, ttl, serialized)
            
            # Update size estimate
            self.size += len(serialized)
            
            logger.debug(f"💾 Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"❌ Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"❌ Cache delete error: {e}")
            return False
    
    async def clear(self, pattern: str = "*") -> int:
        """Clear cache entries matching pattern"""
        if not self.enabled or not self.redis_client:
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"🧹 Cache cleared: {len(keys)} keys")
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"❌ Cache clear error: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled or not self.redis_client:
            return {"enabled": False}
        
        try:
            info = await self.redis_client.info()
            
            return {
                "enabled": True,
                "used_memory": info.get('used_memory', 0),
                "connected_clients": info.get('connected_clients', 0),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0),
                "hit_rate": (
                    info.get('keyspace_hits', 0) / 
                    max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0))
                ),
                "size": self.size
            }
        except Exception as e:
            logger.error(f"❌ Cache stats error: {e}")
            return {"enabled": False, "error": str(e)}
    
    async def cleanup(self):
        """Cleanup cache connection"""
        try:
            if self.redis_client:
                await self.redis_client.close()
                logger.info("✅ Cache connection closed")
        except Exception as e:
            logger.error(f"❌ Cache cleanup error: {e}")
        finally:
            self.redis_client = None
            self.enabled = False