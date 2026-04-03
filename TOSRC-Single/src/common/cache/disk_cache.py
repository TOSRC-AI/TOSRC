# -*- coding: utf-8 -*-
"""
磁盘缓存实现

特性：
- 基于JSON文件的持久化缓存
- 支持TTL
- 自动过期清理
- 线程安全
"""
import json
import os
import time
import threading
from pathlib import Path
from typing import Any, Optional, Dict
from dataclasses import dataclass, asdict
from src.utils.logger import get_logger

logger = get_logger()


@dataclass
class DiskCacheEntry:
    """磁盘缓存项"""
    value: Any
    created_at: float
    ttl: Optional[float] = None

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "value": self.value,
            "created_at": self.created_at,
            "ttl": self.ttl
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DiskCacheEntry":
        """从字典创建"""
        return cls(
            value=data["value"],
            created_at=data["created_at"],
            ttl=data.get("ttl")
        )


class DiskCache:
    """
    磁盘缓存

    使用JSON文件存储缓存数据，适用于：
    - 大对象缓存（避免占用内存）
    - 持久化缓存（重启后保留）
    - 跨进程共享缓存

    使用示例：
        cache = DiskCache(cache_dir="data/cache")
        cache.set("key", {"data": "value"}, ttl=3600)
        data = cache.get("key")
    """

    def __init__(
        self,
        cache_dir: str = "data/cache",
        default_ttl: Optional[float] = None,
        max_size: int = 1000
    ):
        """
        初始化磁盘缓存

        Args:
            cache_dir: 缓存目录
            default_ttl: 默认TTL
            max_size: 最大缓存条目数
        """
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self.max_size = max_size

        # 确保目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 线程锁
        self._lock = threading.RLock()

        # 索引文件（记录所有缓存项）
        self._index_file = self.cache_dir / ".index.json"
        self._index: Dict[str, float] = {}  # key -> modified_time

        # 加载索引
        self._load_index()

        logger.debug(f"DiskCache 初始化完成: {cache_dir}")

    def _load_index(self):
        """加载索引"""
        if self._index_file.exists():
            try:
                with open(self._index_file, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
            except Exception as e:
                logger.warning(f"加载缓存索引失败: {e}")
                self._index = {}

    def _save_index(self):
        """保存索引"""
        try:
            with open(self._index_file, "w", encoding="utf-8") as f:
                json.dump(self._index, f)
        except Exception as e:
            logger.warning(f"保存缓存索引失败: {e}")

    def _get_cache_file(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用hash避免文件名过长
        import hashlib
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

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
            cache_file = self._get_cache_file(key)

            if not cache_file.exists():
                return default

            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                entry = DiskCacheEntry.from_dict(data)

                if entry.is_expired():
                    # 过期，删除
                    cache_file.unlink(missing_ok=True)
                    self._index.pop(key, None)
                    self._save_index()
                    return default

                return entry.value

            except Exception as e:
                logger.warning(f"读取缓存文件失败: {e}")
                return default

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
            ttl: 生存时间（秒）
        """
        with self._lock:
            # 检查容量
            if len(self._index) >= self.max_size and key not in self._index:
                self._cleanup_oldest()

            # 创建缓存项
            entry = DiskCacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl if ttl is not None else self.default_ttl
            )

            # 保存到文件
            cache_file = self._get_cache_file(key)
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(entry.to_dict(), f, ensure_ascii=False)

                # 更新索引
                self._index[key] = time.time()
                self._save_index()

            except Exception as e:
                logger.warning(f"写入缓存文件失败: {e}")

    def _cleanup_oldest(self, count: int = 10):
        """清理最旧的缓存项"""
        if not self._index:
            return

        # 按修改时间排序
        sorted_items = sorted(self._index.items(), key=lambda x: x[1])

        for key, _ in sorted_items[:count]:
            cache_file = self._get_cache_file(key)
            cache_file.unlink(missing_ok=True)
            del self._index[key]

        self._save_index()
        logger.debug(f"清理 {count} 个旧缓存项")

    def delete(self, key: str) -> bool:
        """
        删除缓存项

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key not in self._index:
                return False

            cache_file = self._get_cache_file(key)
            cache_file.unlink(missing_ok=True)

            del self._index[key]
            self._save_index()

            return True

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            if key not in self._index:
                return False

            cache_file = self._get_cache_file(key)
            if not cache_file.exists():
                self._index.pop(key, None)
                return False

            # 检查过期
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                entry = DiskCacheEntry.from_dict(data)

                if entry.is_expired():
                    cache_file.unlink(missing_ok=True)
                    self._index.pop(key, None)
                    return False

                return True
            except:
                return False

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            # 删除所有缓存文件
            for cache_file in self.cache_dir.glob("*.json"):
                if cache_file.name != ".index.json":
                    cache_file.unlink(missing_ok=True)

            self._index.clear()
            self._save_index()

            logger.info("磁盘缓存已清空")

    def cleanup_expired(self) -> int:
        """
        清理过期缓存项

        Returns:
            清理的数量
        """
        with self._lock:
            expired_count = 0

            for key in list(self._index.keys()):
                cache_file = self._get_cache_file(key)

                if not cache_file.exists():
                    self._index.pop(key, None)
                    continue

                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    entry = DiskCacheEntry.from_dict(data)

                    if entry.is_expired():
                        cache_file.unlink(missing_ok=True)
                        self._index.pop(key, None)
                        expired_count += 1
                except:
                    cache_file.unlink(missing_ok=True)
                    self._index.pop(key, None)

            if expired_count > 0:
                self._save_index()
                logger.debug(f"清理 {expired_count} 个过期缓存项")

            return expired_count

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "size": len(self._index),
                "max_size": self.max_size,
                "cache_dir": str(self.cache_dir)
            }

    def keys(self) -> list:
        """获取所有键"""
        with self._lock:
            return list(self._index.keys())

    def close(self):
        """关闭缓存"""
        self._save_index()
        logger.info("DiskCache 已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
