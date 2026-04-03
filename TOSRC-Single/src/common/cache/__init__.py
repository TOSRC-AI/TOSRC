# -*- coding: utf-8 -*-
"""
缓存模块 - 提供多级缓存支持

支持：
- 内存缓存（线程安全，带TTL）
- 磁盘缓存（JSON文件）
- 缓存统计和监控
"""
from .memory_cache import MemoryCache, cached
from .disk_cache import DiskCache
from .cache_manager import CacheManager, get_cache_manager, cache_result

__all__ = [
    "MemoryCache",
    "cached",
    "DiskCache",
    "CacheManager",
    "get_cache_manager",
    "cache_result",
]
