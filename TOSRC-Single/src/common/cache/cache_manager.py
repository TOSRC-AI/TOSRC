# -*- coding: utf-8 -*-
"""
缓存管理器

统一管理多级缓存：
- L1: 内存缓存（最快）
- L2: 磁盘缓存（持久化）
- L3: 外部缓存（如Redis，预留）

实现缓存穿透、缓存击穿、缓存雪崩的防护
"""
import threading
import time
import hashlib
from typing import Any, Optional, Dict, Callable, List
from functools import wraps
from src.utils.logger import get_logger
from .memory_cache import MemoryCache
from .disk_cache import DiskCache

logger = get_logger()


class CacheManager:
    """
    缓存管理器

    管理多级缓存，提供统一接口

    特性：
    - 多级缓存（内存 -> 磁盘）
    - 缓存穿透防护（空值缓存）
    - 缓存击穿防护（互斥锁）
    - 缓存雪崩防护（随机TTL）

    使用示例：
        cache_mgr = CacheManager()

        # 基础使用
        value = cache_mgr.get("key")
        cache_mgr.set("key", value, ttl=300)

        # 多级缓存
        value = cache_mgr.get("key", tiers=["memory", "disk"])
    """

    def __init__(
        self,
        memory_cache: Optional[MemoryCache] = None,
        disk_cache: Optional[DiskCache] = None,
        enable_lock: bool = True
    ):
        """
        初始化缓存管理器

        Args:
            memory_cache: 内存缓存实例
            disk_cache: 磁盘缓存实例
            enable_lock: 是否启用互斥锁（防击穿）
        """
        self.memory = memory_cache or MemoryCache()
        self.disk = disk_cache or DiskCache()
        self.enable_lock = enable_lock

        # 互斥锁（防缓存击穿）
        self._locks: Dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()

        # 空值标记（防缓存穿透）
        self._NULL_VALUE = "__CACHE_NULL__"

        logger.info("CacheManager 初始化完成")

    def _get_lock(self, key: str) -> threading.Lock:
        """获取键的互斥锁"""
        with self._locks_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    def get(
        self,
        key: str,
        default: Any = None,
        tiers: List[str] = None
    ) -> Any:
        """
        获取缓存值（多级缓存）

        Args:
            key: 缓存键
            default: 默认值
            tiers: 缓存层级 ["memory", "disk"]，默认全部

        Returns:
            缓存值或默认值
        """
        tiers = tiers or ["memory", "disk"]

        # L1: 内存缓存
        if "memory" in tiers:
            value = self.memory.get(key)
            if value is not None:
                if value == self._NULL_VALUE:
                    return default
                return value

        # L2: 磁盘缓存
        if "disk" in tiers:
            value = self.disk.get(key)
            if value is not None:
                if value == self._NULL_VALUE:
                    return default

                # 回填内存缓存
                self.memory.set(key, value)
                return value

        return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        tiers: List[str] = None,
        jitter: bool = False
    ) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
            tiers: 缓存层级
            jitter: 是否添加随机抖动（防雪崩）
        """
        tiers = tiers or ["memory", "disk"]

        # 添加随机抖动（防止同时过期）
        if jitter and ttl:
            import random
            ttl = ttl * (0.9 + random.random() * 0.2)

        # 设置内存缓存
        if "memory" in tiers:
            self.memory.set(key, value, ttl=ttl)

        # 设置磁盘缓存
        if "disk" in tiers:
            self.disk.set(key, value, ttl=ttl)

    def get_or_set(
        self,
        key: str,
        default_factory: Callable[[], Any],
        ttl: Optional[float] = None,
        tiers: List[str] = None,
        cache_none: bool = False
    ) -> Any:
        """
        获取或设置缓存（带防击穿保护）

        Args:
            key: 缓存键
            default_factory: 默认值工厂函数
            ttl: 生存时间
            tiers: 缓存层级
            cache_none: 是否缓存None值（防穿透）

        Returns:
            缓存值
        """
        # 先尝试获取
        value = self.get(key, tiers=tiers)
        if value is not None:
            return value

        if not self.enable_lock:
            # 无锁模式
            value = default_factory()
            if value is not None or cache_none:
                self.set(key, value if value is not None else self._NULL_VALUE,
                        ttl=ttl, tiers=tiers)
            return value

        # 带锁模式（防击穿）
        lock = self._get_lock(key)

        if not lock.acquire(blocking=False):
            # 未获取到锁，等待后重试
            with lock:
                return self.get(key, default=default_factory(), tiers=tiers)

        try:
            # 双重检查
            value = self.get(key, tiers=tiers)
            if value is not None:
                return value

            # 执行工厂函数
            value = default_factory()

            # 设置缓存
            if value is not None or cache_none:
                self.set(
                    key,
                    value if value is not None else self._NULL_VALUE,
                    ttl=ttl,
                    tiers=tiers
                )

            return value

        finally:
            lock.release()

    def delete(self, key: str, tiers: List[str] = None) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键
            tiers: 缓存层级

        Returns:
            是否成功删除
        """
        tiers = tiers or ["memory", "disk"]
        success = False

        if "memory" in tiers:
            success = self.memory.delete(key) or success

        if "disk" in tiers:
            success = self.disk.delete(key) or success

        return success

    def clear(self, tiers: List[str] = None) -> None:
        """
        清空缓存

        Args:
            tiers: 缓存层级
        """
        tiers = tiers or ["memory", "disk"]

        if "memory" in tiers:
            self.memory.clear()

        if "disk" in tiers:
            self.disk.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "memory": self.memory.get_stats(),
            "disk": self.disk.get_stats()
        }

    def close(self) -> None:
        """关闭缓存管理器"""
        self.memory.close()
        self.disk.close()
        logger.info("CacheManager 已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None
_cache_manager_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    """
    获取全局缓存管理器实例（单例）

    Returns:
        CacheManager 实例
    """
    global _cache_manager

    if _cache_manager is None:
        with _cache_manager_lock:
            if _cache_manager is None:
                _cache_manager = CacheManager()

    return _cache_manager


def cache_result(
    ttl: float = 300,
    key_prefix: str = "",
    tiers: List[str] = None,
    cache_none: bool = False
):
    """
    缓存结果装饰器

    自动缓存函数返回值

    Args:
        ttl: 缓存生存时间
        key_prefix: 缓存键前缀
        tiers: 缓存层级
        cache_none: 是否缓存None值

    使用示例：
        @cache_result(ttl=60, key_prefix="user")
        def get_user(user_id: int):
            return db.query(User).get(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = _generate_cache_key(key_prefix, func, args, kwargs)

            # 使用缓存管理器获取或设置
            cache_mgr = get_cache_manager()
            return cache_mgr.get_or_set(
                cache_key,
                lambda: func(*args, **kwargs),
                ttl=ttl,
                tiers=tiers,
                cache_none=cache_none
            )

        # 附加清除缓存函数
        wrapper.invalidate = lambda *a, **kw: get_cache_manager().delete(
            _generate_cache_key(key_prefix, func, a, kw)
        )

        return wrapper

    return decorator


def _generate_cache_key(
    prefix: str,
    func: Callable,
    args: tuple,
    kwargs: dict
) -> str:
    """生成缓存键"""
    # 函数标识
    func_id = f"{func.__module__}.{func.__name__}"

    # 参数标识
    args_str = ":".join(str(arg) for arg in args)
    kwargs_str = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))

    # 组合键
    key_parts = [prefix, func_id, args_str, kwargs_str]
    key = "|".join(filter(None, key_parts))

    # MD5哈希（避免键过长）
    return hashlib.md5(key.encode()).hexdigest()


# 常用缓存快捷函数
def cache_entity(
    entity_type: str,
    entity_id: Any,
    value: Any,
    ttl: float = 300
) -> None:
    """缓存实体"""
    key = f"entity:{entity_type}:{entity_id}"
    get_cache_manager().set(key, value, ttl=ttl)


def get_cached_entity(
    entity_type: str,
    entity_id: Any,
    default: Any = None
) -> Any:
    """获取缓存实体"""
    key = f"entity:{entity_type}:{entity_id}"
    return get_cache_manager().get(key, default=default)


def invalidate_entity(entity_type: str, entity_id: Any) -> bool:
    """使实体缓存失效"""
    key = f"entity:{entity_type}:{entity_id}"
    return get_cache_manager().delete(key)


def cache_query(
    query_key: str,
    value: Any,
    ttl: float = 60
) -> None:
    """缓存查询结果"""
    key = f"query:{query_key}"
    get_cache_manager().set(key, value, ttl=ttl)


def get_cached_query(query_key: str, default: Any = None) -> Any:
    """获取缓存查询结果"""
    key = f"query:{query_key}"
    return get_cache_manager().get(key, default=default)
