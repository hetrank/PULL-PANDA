# OLD: Simple dictionary cache
cache = {}

def get_data(key):
    """Get data from cache or source"""
    if key in cache:
        return cache[key]
    
    # Fetch from source (expensive operation)
    data = fetch_from_source(key)
    cache[key] = data
    return data

def fetch_from_source(key):
    """Expensive data fetching operation"""
    # Simulate expensive operation
    time.sleep(1)
    return f"data_for_{key}"

# NEW: Advanced caching with TTL, LRU eviction, and persistence
import time
import pickle
from typing import Any, Optional, Callable
from collections import OrderedDict
import hashlib

class AdvancedCache:
    """Advanced caching system with TTL and size limits"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl  # seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired"""
        if key not in self.cache:
            return None
        
        item, expiry = self.cache[key]
        if time.time() > expiry:
            del self.cache[key]  # Expired
            return None
        
        # Move to end (recently used)
        self.cache.move_to_end(key)
        return item
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set item in cache with TTL"""
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)  # Remove oldest
        
        expiry = time.time() + (ttl or self.default_ttl)
        self.cache[key] = (value, expiry)
        self.cache.move_to_end(key)
    
    def cached(self, ttl: Optional[int] = None):
        """Decorator for caching function results"""
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                # Create cache key from function name and arguments
                key = self._generate_key(func.__name__, args, kwargs)
                cached_result = self.get(key)
                
                if cached_result is not None:
                    return cached_result
                
                result = func(*args, **kwargs)
                self.set(key, result, ttl)
                return result
            return wrapper
        return decorator
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate unique cache key"""
        key_parts = [func_name, str(args), str(sorted(kwargs.items()))]
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()

# Global cache instance
cache = AdvancedCache(max_size=500, default_ttl=60)

# Usage example
@cache.cached(ttl=30)
def get_user_data(user_id: int):
    """Expensive user data lookup with caching"""
    time.sleep(0.5)  # Simulate expensive operation
    return {"user_id": user_id, "data": f"user_data_{user_id}"}

@cache.cached(ttl=300)
def get_configuration(config_name: str):
    """Configuration lookup with longer TTL"""
    time.sleep(0.2)
    return {"config": config_name, "value": f"value_for_{config_name}"}