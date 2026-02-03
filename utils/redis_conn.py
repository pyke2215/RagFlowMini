# utils/redis_cache.py
import redis
import json
import os
from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class RedisConnection:
    """
    Thin wrapper around a Redis client with some helper methods for
    caching conversation context, embeddings, and rate limiting.
    """

    def __init__(self):
        # Load từ .env
        redis_uri = os.getenv("REDIS_URI")
        if redis_uri:
            self.client = redis.from_url(redis_uri, decode_responses=True)
        else:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port_raw = os.getenv("REDIS_PORT", "6379")
            redis_db_raw = os.getenv("REDIS_DB", "0")

            try:
                redis_port = int(redis_port_raw)
            except ValueError:
                redis_port = 6379

            try:
                redis_db = int(redis_db_raw) if redis_db_raw.strip() != "" else 0
            except ValueError:
                redis_db = 0

            redis_password = os.getenv("REDIS_PASSWORD", None)
            
            self.client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password if redis_password else None,
                socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", 5)),
                decode_responses=True,
            )
            self.check_connection()

    # Cache conversation messages (ưu tiên cho chat)
    def cache_conversation_messages(self, conversation_id: str, messages: list, ttl=None):
        """
        Cache danh sách messages của conversation vào Redis.
        Messages được lưu dưới dạng list, giữ nguyên thứ tự.
        """
        if ttl is None:
            ttl = int(os.getenv("CACHE_CONTEXT_TTL", 3600))
        key = f"conv:{conversation_id}:messages"
        self.client.setex(key, ttl, json.dumps(messages, default=str))
    
    def get_conversation_messages(self, conversation_id: str, limit: int = None) -> Optional[list]:
        """
        Lấy messages từ Redis cache.
        Nếu có limit, trả về N messages gần nhất.
        """
        key = f"conv:{conversation_id}:messages"
        data = self.client.get(key)
        if data:
            messages = json.loads(data)
            if limit and len(messages) > limit:
                # Trả về N messages gần nhất (cuối list)
                return messages[-limit:]
            return messages
        return None
    
    def add_message_to_conversation_cache(self, conversation_id: str, message: dict, max_messages: int = 50):
        """
        Thêm message mới vào cache conversation.
        Tự động giới hạn số lượng messages (giữ N messages gần nhất).
        """
        key = f"conv:{conversation_id}:messages"
        existing = self.client.get(key)
        
        if existing:
            messages = json.loads(existing)
        else:
            messages = []
        
        # Thêm message mới vào cuối
        messages.append(message)
        
        # Giới hạn số lượng (giữ N messages gần nhất)
        if len(messages) > max_messages:
            messages = messages[-max_messages:]
        
        ttl = int(os.getenv("CACHE_CONTEXT_TTL", 3600))
        self.client.setex(key, ttl, json.dumps(messages, default=str))
    
    # Legacy methods (backward compatibility)
    def cache_conversation_context(self, conversation_id: str, messages: list, ttl=None):
        """Alias cho cache_conversation_messages"""
        self.cache_conversation_messages(conversation_id, messages, ttl)
    
    def get_conversation_context(self, conversation_id: str) -> Optional[list]:
        """Alias cho get_conversation_messages"""
        return self.get_conversation_messages(conversation_id)
    
    # Cache embeddings (query → embedding)
    def cache_query_embedding(self, query: str, embedding: list, ttl=None):
        if ttl is None:
            ttl = int(os.getenv("CACHE_EMBEDDING_TTL", 1800))
        key = f"embed:query:{hash(query)}"
        self.client.setex(key, ttl, json.dumps(embedding))
    
    # Rate limiting
    def check_rate_limit(self, user_id: str, limit=None, window=None) -> bool:
        if limit is None:
            limit = int(os.getenv("RATE_LIMIT_REQUESTS", 10))
        if window is None:
            window = int(os.getenv("RATE_LIMIT_WINDOW", 60))
        
        key = f"ratelimit:{user_id}"
        current = self.client.incr(key)
        if current == 1:
            self.client.expire(key, window)
        return current <= limit
    
    # ===== Basic Redis Operations (wrapped from self.client) =====
    
    def ping(self):
        """Check if Redis connection is alive"""
        return self.client.ping()
    
    def set(self, key: str, value: str, ex: int = None, px: int = None, nx: bool = False, xx: bool = False):
        """Set key to value with optional expiration"""
        return self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
    
    def get(self, key: str):
        """Get value by key"""
        return self.client.get(key)
    
    def delete(self, *keys: str):
        """Delete one or more keys"""
        return self.client.delete(*keys)
    
    def exists(self, *keys: str):
        """Check if one or more keys exist"""
        return self.client.exists(*keys)
    
    def setex(self, key: str, time: int, value: str):
        """Set key to value with expiration time in seconds"""
        return self.client.setex(key, time, value)
    
    def expire(self, key: str, time: int):
        """Set expiration time for a key"""
        return self.client.expire(key, time)
    
    def ttl(self, key: str):
        """Get time to live for a key"""
        return self.client.ttl(key)
    
    def incr(self, key: str, amount: int = 1):
        """Increment key by amount (default 1)"""
        return self.client.incr(key, amount)
    
    def decr(self, key: str, amount: int = 1):
        """Decrement key by amount (default 1)"""
        return self.client.decr(key, amount)
    
    def keys(self, pattern: str = "*"):
        """Get all keys matching pattern"""
        return self.client.keys(pattern)
    
    def flushdb(self):
        """Delete all keys in current database"""
        return self.client.flushdb()
    
    # ===== High-level helper methods =====
    
    def check_connection(self):
        """Check if Redis connection is alive (alias for ping with error handling)"""
        try:
            if self.client and self.ping():
                print("Kết nối Redis thành công!")
                return True
        except redis.ConnectionError as e:
            print(f"Lỗi kết nối Redis: {e}")
            return False


@lru_cache(maxsize=1)
def get_redis_connection() -> RedisConnection:
    """
    FastAPI dependency factory that returns a singleton RedisConnection instance.
    """
    return RedisConnection()

# Alias để backward compatibility
get_redis_cache = get_redis_connection