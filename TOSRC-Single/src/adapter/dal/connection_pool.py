#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite 数据库连接池

解决高并发场景下的连接复用问题，提升数据库访问性能
"""
import sqlite3
import threading
import queue
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """连接池配置"""
    max_connections: int = 10
    min_connections: int = 2
    connection_timeout: float = 30.0
    max_idle_time: float = 300.0  # 5分钟
    check_interval: float = 60.0   # 检查间隔


class PooledConnection:
    """包装的数据库连接，支持连接池管理"""

    def __init__(self, connection: sqlite3.Connection, pool: 'ConnectionPool'):
        self._connection = connection
        self._pool = pool
        self._in_use = False
        self._last_used = threading.current_thread().ident
        self._created_at = sqlite3.datetime.datetime.now()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    @property
    def in_use(self) -> bool:
        return self._in_use

    @in_use.setter
    def in_use(self, value: bool):
        self._in_use = value
        if value:
            self._last_used = sqlite3.datetime.datetime.now()

    def is_expired(self, max_idle_time: float) -> bool:
        """检查连接是否过期"""
        if self._in_use:
            return False
        idle_time = (sqlite3.datetime.datetime.now() - self._last_used).total_seconds()
        return idle_time > max_idle_time

    def close(self):
        """关闭底层连接"""
        try:
            self._connection.close()
        except Exception as e:
            logger.warning(f"关闭连接时出错: {e}")


class ConnectionPool:
    """
    SQLite 数据库连接池

    特性：
    - 连接复用，减少创建开销
    - 线程安全，支持多线程并发
    - 自动回收过期连接
    - 上下文管理器支持

    使用示例：
        pool = ConnectionPool("data.db", max_connections=10)

        with pool.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM users")
            results = cursor.fetchall()
    """

    def __init__(self, db_path: str, config: Optional[PoolConfig] = None):
        """
        初始化连接池

        Args:
            db_path: 数据库文件路径
            config: 连接池配置
        """
        self.db_path = db_path
        self.config = config or PoolConfig()

        # 连接池状态
        self._pool: queue.Queue[PooledConnection] = queue.Queue()
        self._in_use: Dict[int, PooledConnection] = {}
        self._lock = threading.RLock()
        self._closed = False

        # 统计信息
        self._stats = {
            "total_created": 0,
            "total_reused": 0,
            "total_closed": 0,
            "max_concurrent": 0
        }

        # 初始化最小连接数
        self._init_connections()

        logger.info(f"连接池初始化完成: {db_path}, 最大连接数: {self.config.max_connections}")

    def _init_connections(self):
        """初始化最小连接数"""
        for _ in range(self.config.min_connections):
            try:
                conn = self._create_connection()
                self._pool.put(conn)
            except Exception as e:
                logger.error(f"初始化连接失败: {e}")

    def _create_connection(self) -> PooledConnection:
        """创建新连接"""
        if self._closed:
            raise RuntimeError("连接池已关闭")

        conn = sqlite3.connect(
            self.db_path,
            timeout=self.config.connection_timeout,
            check_same_thread=False  # 允许跨线程使用
        )
        conn.row_factory = sqlite3.Row

        # 启用 WAL 模式提升并发性能
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        pooled_conn = PooledConnection(conn, self)

        with self._lock:
            self._stats["total_created"] += 1

        logger.debug("创建新连接")
        return pooled_conn

    @contextmanager
    def get_connection(self, timeout: Optional[float] = None):
        """
        获取连接（上下文管理器）

        Args:
            timeout: 等待超时时间（秒）

        Yields:
            sqlite3.Connection: 数据库连接
        """
        if self._closed:
            raise RuntimeError("连接池已关闭")

        timeout = timeout or self.config.connection_timeout
        pooled_conn = None

        try:
            # 尝试从池中获取连接
            try:
                pooled_conn = self._pool.get(timeout=timeout)
                self._stats["total_reused"] += 1
                logger.debug("复用连接")
            except queue.Empty:
                # 池已满，检查是否可创建新连接
                with self._lock:
                    current_count = len(self._in_use) + self._pool.qsize()
                    if current_count < self.config.max_connections:
                        pooled_conn = self._create_connection()
                    else:
                        raise RuntimeError(f"连接池已满，无法获取连接（当前: {current_count}）")

            # 标记为使用中
            pooled_conn.in_use = True
            thread_id = threading.current_thread().ident

            with self._lock:
                self._in_use[thread_id] = pooled_conn
                current_concurrent = len(self._in_use)
                if current_concurrent > self._stats["max_concurrent"]:
                    self._stats["max_concurrent"] = current_concurrent

            yield pooled_conn.connection

        finally:
            if pooled_conn:
                # 归还连接到池中
                pooled_conn.in_use = False
                thread_id = threading.current_thread().ident

                with self._lock:
                    self._in_use.pop(thread_id, None)

                try:
                    self._pool.put(pooled_conn, timeout=1.0)
                except queue.Full:
                    # 池已满，关闭连接
                    pooled_conn.close()
                    self._stats["total_closed"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        with self._lock:
            return {
                **self._stats,
                "available": self._pool.qsize(),
                "in_use": len(self._in_use),
                "total": self._pool.qsize() + len(self._in_use),
                "max": self.config.max_connections
            }

    def close(self):
        """关闭连接池"""
        if self._closed:
            return

        self._closed = True
        logger.info("正在关闭连接池...")

        # 关闭所有连接
        closed_count = 0
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
                closed_count += 1
            except queue.Empty:
                break

        # 关闭正在使用的连接
        with self._lock:
            for conn in self._in_use.values():
                conn.close()
                closed_count += 1
            self._in_use.clear()

        logger.info(f"连接池已关闭，共关闭 {closed_count} 个连接")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 全局连接池缓存
_pools: Dict[str, ConnectionPool] = {}
_pools_lock = threading.Lock()


def get_connection_pool(db_path: str, config: Optional[PoolConfig] = None) -> ConnectionPool:
    """
    获取或创建连接池（单例模式）

    Args:
        db_path: 数据库路径
        config: 连接池配置

    Returns:
        ConnectionPool: 连接池实例
    """
    with _pools_lock:
        if db_path not in _pools:
            _pools[db_path] = ConnectionPool(db_path, config)
        return _pools[db_path]


def close_all_pools():
    """关闭所有连接池"""
    global _pools
    with _pools_lock:
        for pool in _pools.values():
            pool.close()
        _pools.clear()
        logger.info("所有连接池已关闭")
