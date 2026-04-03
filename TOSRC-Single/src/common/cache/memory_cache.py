# -*- coding: utf-8 -*-
"""
线程安全的内存缓存实现

特性：
- 带TTL（生存时间）的缓存项
- 线程安全操作
- 自动过期清理
- LRU淘汰策略
- 命中率统计
"""
import threading
import time
import functools
from typing import Any, Optional, Dict, Callable, Tuple
from collections import OrderedDict
from dataclasses import dataclass
from src.utils.logger import get_logger

logger = get_logger()


@dataclass
class CacheEntry:
    """缓存项"""
    value: Any
    created_at: float
    ttl: Optional[float] = None
    access_count: int = 0
    last_accessed: float = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl


class MemoryCache:
    """
    线程安全的内存缓存

    特性：
    - 支持TTL（生存时间）
    - 支持最大容量限制（LRU淘汰）
    - 线程安全
    - 自动过期清理
    - 命中率统计

    使用示例：
        cache = MemoryCache(max_size=1000, default_ttl=300)
        cache.set("key", "value", ttl=60)
        value = cache.get("key")
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        cleanup_interval: float = 60.0,
        enable_stats: bool = True
    ):
        """
        初始化内存缓存

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒）
            cleanup_interval: 自动清理间隔（秒）
            enable_stats: 是否启用统计
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.enable_stats = enable_stats

        # 使用OrderedDict实现LRU
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # 统计信息
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }

        # 自动清理定时器
        self._cleanup_timer: Optional[threading.Timer] = None
        self._cleanup_interval = cleanup_interval
        self._start_cleanup_timer()

        logger.debug(f"MemoryCache 初始化完成，max_size={max_size}")

    def _start_cleanup_timer(self):
        """启动自动清理定时器"""
        def cleanup():
            try:
                self.cleanup_expired()
            finally:
                self._start_cleanup_timer()

        self._cleanup_timer = threading.Timer(self._cleanup_interval, cleanup)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            缓存值或默认值
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                if self.enable_stats:
                    self._stats["misses"] += 1
                return default

            if entry.is_expired():
                # 过期，删除并返回默认值
                del self._cache[key]
                if self.enable_stats:
                    self._stats["misses"] += 1
                    self._stats["expirations"] += 1
                return default

            # 更新访问信息
            entry.access_count += 1
            entry.last_accessed = time.time()

            # 移动到OrderedDict末尾（最近使用）
            self._cache.move_to_end(key)

            if self.enable_stats:
                self._stats["hits"] += 1

            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None
    ) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None表示永不过期
        """
        with self._lock:
            # 如果key已存在，先删除（确保顺序正确）
            if key in self._cache:
                del self._cache[key]

            # 检查容量，执行LRU淘汰
            while len(self._cache) >= self.max_size:
                self._evict_lru()

            # 计算实际TTL
            actual_ttl = ttl if ttl is not None else self.default_ttl

            # 创建缓存项
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=actual_ttl,
                last_accessed=time.time()
            )

            self._cache[key] = entry

    def _evict_lru(self):
        """淘汰最少使用的缓存项"""
        if not self._cache:
            return

        # OrderedDict的第一个元素是最久未使用的
        oldest_key = next(iter(self._cache))
        del self._cache[oldest_key]

        if self.enable_stats:
            self._stats["evictions"] += 1

        logger.debug(f"LRU淘汰: {oldest_key}")

    def delete(self, key: str) -> bool:
        """
        删除缓存项

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在（未过期）"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                del self._cache[key]
                return False
            return True

    def cleanup_expired(self) -> int:
        """
        清理过期缓存项

        Returns:
            清理的数量
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys and self.enable_stats:
                self._stats["expirations"] += len(expired_keys)

            if expired_keys:
                logger.debug(f"清理 {len(expired_keys)} 个过期缓存项")

            return len(expired_keys)

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            logger.info("内存缓存已清空")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests * 100
                if total_requests > 0 else 0
            )

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": round(hit_rate, 2),
                "evictions": self._stats["evictions"],
                "expirations": self._stats["expirations"]
            }

    def keys(self) -> list:
        """获取所有键（不过滤过期）"""
        with self._lock:
            return list(self._cache.keys())

    def values(self) -> list:
        """获取所有值（不过滤过期）"""
        with self._lock:
            return [entry.value for entry in self._cache.values()]

    def items(self) -> list:
        """获取所有键值对（过滤过期）"""
        with self._lock:
            result = []
            expired_keys = []

            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
                else:
                    result.append((key, entry.value))

            # 删除过期项
            for key in expired_keys:
                del self._cache[key]

            return result

    def close(self):
        """关闭缓存，清理资源"""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
        self.clear()
        logger.info("MemoryCache 已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 装饰器函数
def cached(
    cache_instance: Optional[MemoryCache] = None,
    ttl: Optional[float] = None,
    key_func: Optional[Callable] = None
):
    """
    缓存装饰器

    自动缓存函数返回值

    Args:
        cache_instance: 缓存实例，默认创建新的
        ttl: 缓存生存时间
        key_func: 自定义缓存键生成函数

    使用示例：
        cache = MemoryCache()

        @cached(cache_instance=cache, ttl=60)
        def expensive_function(arg1, arg2):
            return expensive_computation(arg1, arg2)
    """
    def decorator(func: Callable) -> Callable:
        _cache = cache_instance or MemoryCache()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认：函数名+参数
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

            # 尝试从缓存获取
            cached_value = _cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数
            result = func(*args, **kwargs)

            # 缓存结果
            _cache.set(cache_key, result, ttl=ttl)

            return result

        # 附加缓存操作函数
        wrapper.cache = _cache
        wrapper.cache_key = lambda *a, **kw: (
            key_func(*a, **kw) if key_func
            else f"{func.__name__}:{':'.join(str(x) for x in a)}"
        )

        return wrapper

    return decorator
