"""
数据缓存模块
提供内存缓存和数据库缓存的双重缓存机制
"""

import time
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime


class MemoryCache:
    """内存缓存类"""
    
    def __init__(self, default_ttl: int = 300):
        """
        初始化内存缓存
        
        Args:
            default_ttl: 默认缓存时间（秒）
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，不存在或已过期返回None
        """
        if key not in self._cache:
            return None
        
        item = self._cache[key]
        if item['expires_at'] and time.time() > item['expires_at']:
            del self._cache[key]
            return None
        
        return item['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
        """
        ttl = ttl if ttl is not None else self.default_ttl
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl if ttl else None
        }
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的缓存数量
        """
        now = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if v['expires_at'] and now > v['expires_at']
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)


class DualCache:
    """双重缓存（内存 + 数据库）"""
    
    def __init__(self, memory_ttl: int = 300, db_ttl: int = 3600):
        """
        初始化双重缓存
        
        Args:
            memory_ttl: 内存缓存时间（秒）
            db_ttl: 数据库缓存时间（秒）
        """
        self.memory_cache = MemoryCache(default_ttl=memory_ttl)
        self.db_ttl = db_ttl
        self._db = None
    
    @property
    def db(self):
        """懒加载数据库"""
        if self._db is None:
            from database import get_db
            self._db = get_db()
        return self._db
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存（先查内存，再查数据库）
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值
        """
        # 先查内存缓存
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # 再查数据库缓存
        value = self.db.get_cache(key)
        if value is not None:
            # 回填内存缓存
            self.memory_cache.set(key, value)
            return value
        
        return None
    
    def set(self, key: str, value: Any, 
            memory_ttl: Optional[int] = None,
            db_ttl: Optional[int] = None) -> None:
        """
        设置缓存（同时写入内存和数据库）
        
        Args:
            key: 缓存键
            value: 缓存值
            memory_ttl: 内存缓存时间
            db_ttl: 数据库缓存时间
        """
        self.memory_cache.set(key, value, memory_ttl)
        self.db.set_cache(key, value, db_ttl or self.db_ttl)
    
    def delete(self, key: str) -> None:
        """删除缓存"""
        self.memory_cache.delete(key)
        # 数据库缓存让它自然过期
    
    def clear_memory(self) -> None:
        """清空内存缓存"""
        self.memory_cache.clear()


def cached(key_prefix: str, ttl: int = 300):
    """
    缓存装饰器
    
    Args:
        key_prefix: 缓存键前缀
        ttl: 缓存时间（秒）
    
    Usage:
        @cached('token_data', ttl=600)
        def get_token_data(coin_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        cache = MemoryCache(default_ttl=ttl)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{':'.join(str(a) for a in args)}"
            if kwargs:
                cache_key += f":{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
            
            # 尝试获取缓存
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        
        return wrapper
    return decorator


# 全局缓存实例
_cache_instance: Optional[DualCache] = None


def get_cache() -> DualCache:
    """获取全局缓存实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DualCache()
    return _cache_instance
