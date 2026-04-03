#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON Lines (JSONL) 日志记录器
支持按日分片、自动压缩归档、流式读取
适用于高并发日志写入场景
"""
import json
import gzip
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator, Union


class JSONLLogger:
    """
    JSON Lines 日志记录器

    特点：
    - 按日期自动分片存储
    - 支持 gzip 压缩归档
    - 线程安全（使用锁）
    - 流式读取大文件

    使用示例：
        logger = JSONLLogger("data/logs", "routes")
        logger.write({"text": "你好", "intent": "greeting"})
    """

    def __init__(self,
                 log_dir: str,
                 name: str,
                 rotate_daily: bool = True,
                 buffer_size: int = 100):
        """
        初始化 JSONL 日志记录器

        Args:
            log_dir: 日志文件存放目录
            name: 日志名称（用于文件名前缀）
            rotate_daily: 是否按天切分文件
            buffer_size: 缓冲写入的条数（0表示立即写入）
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.name = name
        self.rotate_daily = rotate_daily
        self.buffer_size = buffer_size

        # 线程锁，确保线程安全
        self._lock = threading.Lock()

        # 文件句柄缓存
        self._current_file: Optional[Path] = None
        self._current_date: Optional[str] = None
        self._file_handle = None

        # 写入缓冲
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_count = 0

    def _get_file_path(self, date_str: Optional[str] = None) -> Path:
        """获取指定日期的日志文件路径"""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"{self.name}_{date_str}.jsonl"

    def _open_file(self, file_path: Path):
        """打开日志文件（追加模式）"""
        if self._file_handle is not None:
            if self._current_file == file_path:
                return
            # 关闭旧文件
            self._file_handle.close()

        self._file_handle = open(file_path, "a", encoding="utf-8", buffering=1)
        self._current_file = file_path

    def _flush_buffer(self):
        """刷新缓冲区到文件"""
        if not self._buffer:
            return

        # 确保文件已打开
        today = datetime.now().strftime("%Y-%m-%d")
        if self._current_date != today:
            self._current_date = today
            file_path = self._get_file_path(today)
            self._open_file(file_path)

        # 批量写入
        lines = []
        for record in self._buffer:
            line = json.dumps(record, ensure_ascii=False, default=str)
            lines.append(line + "\n")

        self._file_handle.writelines(lines)
        self._file_handle.flush()

        # 清空缓冲区
        self._buffer.clear()
        self._buffer_count = 0

    def write(self, record: Dict[str, Any], immediate: bool = False, timestamp: Optional[Union[str, datetime]] = None):
        """
        写入单条记录

        Args:
            record: 要记录的数据字典
            immediate: 是否立即写入（跳过缓冲）
            timestamp: 自定义时间戳
        """
        # 添加时间戳（如果没有）
        if "timestamp" not in record:
            if timestamp is not None:
                record["timestamp"] = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
            else:
                record["timestamp"] = datetime.now().isoformat()

        with self._lock:
            if immediate or self.buffer_size <= 0:
                # 立即写入
                today = datetime.now().strftime("%Y-%m-%d")
                if self._current_date != today:
                    self._current_date = today
                    file_path = self._get_file_path(today)
                    self._open_file(file_path)

                line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
                self._file_handle.write(line)
                self._file_handle.flush()
            else:
                # 加入缓冲区
                self._buffer.append(record)
                self._buffer_count += 1

                # 缓冲区满时刷新
                if self._buffer_count >= self.buffer_size:
                    self._flush_buffer()

    def flush(self):
        """手动刷新缓冲区"""
        with self._lock:
            self._flush_buffer()

    def close(self):
        """关闭日志记录器，刷新缓冲区并关闭文件"""
        with self._lock:
            self._flush_buffer()
            if self._file_handle:
                self._file_handle.close()
                self._file_handle = None
                self._current_file = None

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
        return False

    @staticmethod
    def read(file_path: Union[str, Path],
             start_time: Optional[datetime] = None,
             end_time: Optional[datetime] = None,
             filter_func: Optional[callable] = None) -> Iterator[Dict[str, Any]]:
        """
        流式读取 JSONL 文件

        Args:
            file_path: JSONL 文件路径（支持 .gz 压缩文件）
            start_time: 起始时间过滤
            end_time: 结束时间过滤
            filter_func: 自定义过滤函数

        Yields:
            字典格式的日志记录
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return

        # 自动检测压缩文件
        is_gz = file_path.suffix == '.gz' or str(file_path).endswith('.jsonl.gz')
        opener = gzip.open if is_gz else open
        mode = "rt" if is_gz else "r"

        try:
            with opener(file_path, mode, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        record = json.loads(line)

                        # 时间过滤
                        if start_time or end_time:
                            ts = record.get("timestamp")
                            if ts:
                                record_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                if start_time and record_time < start_time:
                                    continue
                                if end_time and record_time > end_time:
                                    continue

                        # 自定义过滤
                        if filter_func and not filter_func(record):
                            continue

                        yield record

                    except json.JSONDecodeError as e:
                        # 跳过格式错误的行，记录警告
                        print(f"Warning: Invalid JSON at {file_path}:{line_num} - {e}")
                        continue

        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            raise

    @staticmethod
    def read_all(file_path: Union[str, Path],
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None,
                 filter_func: Optional[callable] = None,
                 limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        读取所有记录到列表（注意大文件可能导致内存问题）

        Args:
            file_path: JSONL 文件路径
            start_time: 起始时间过滤
            end_time: 结束时间过滤
            filter_func: 自定义过滤函数
            limit: 最大返回条数

        Returns:
            记录列表
        """
        records = []
        for i, record in enumerate(JSONLLogger.read(file_path, start_time, end_time, filter_func)):
            if limit and i >= limit:
                break
            records.append(record)
        return records

    @classmethod
    def compress(cls, source: Union[str, Path], dest: Optional[Union[str, Path]] = None, remove_source: bool = True):
        """
        压缩 JSONL 文件为 gzip 格式

        Args:
            source: 源文件路径
            dest: 目标文件路径（默认添加 .gz 后缀）
            remove_source: 是否删除源文件
        """
        source = Path(source)

        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        if dest is None:
            dest = source.with_suffix(".jsonl.gz")
        else:
            dest = Path(dest)

        # 确保目标目录存在
        dest.parent.mkdir(parents=True, exist_ok=True)

        # 记录原始文件大小（必须在删除前获取）
        original_size = source.stat().st_size

        with open(source, "rb") as f_in:
            with gzip.open(dest, "wb", compresslevel=9) as f_out:
                f_out.writelines(f_in)

        if remove_source:
            source.unlink()

        # 返回压缩比
        compressed_size = dest.stat().st_size
        ratio = (1 - compressed_size / original_size) * 100

        return {
            "source": str(source),
            "dest": str(dest),
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": f"{ratio:.1f}%"
        }

    @classmethod
    def decompress(cls, source: Union[str, Path], dest: Optional[Union[str, Path]] = None):
        """
        解压 gzip 格式的 JSONL 文件

        Args:
            source: 压缩文件路径
            dest: 目标文件路径（默认移除 .gz 后缀）
        """
        source = Path(source)

        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        if dest is None:
            dest = source.with_suffix('') if source.suffix == '.gz' else Path(str(source).replace('.gz', ''))
        else:
            dest = Path(dest)

        with gzip.open(source, "rt", encoding="utf-8") as f_in:
            with open(dest, "w", encoding="utf-8") as f_out:
                f_out.write(f_in.read())

        return str(dest)

    def get_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        stats = {
            "log_dir": str(self.log_dir),
            "name": self.name,
            "total_files": 0,
            "total_size_bytes": 0,
            "date_range": {"earliest": None, "latest": None},
            "files": []
        }

        # 查找所有日志文件
        pattern = f"{self.name}_*.jsonl*"
        files = sorted(self.log_dir.glob(pattern))

        for f in files:
            file_stat = f.stat()
            file_info = {
                "name": f.name,
                "size": file_stat.st_size,
                "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                "compressed": f.suffix == '.gz'
            }
            stats["files"].append(file_info)
            stats["total_files"] += 1
            stats["total_size_bytes"] += file_stat.st_size

            # 解析日期（兼容 .jsonl.gz）
            try:
                date_str = f.name.split("_")[1].split(".")[0]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if stats["date_range"]["earliest"] is None or file_date < stats["date_range"]["earliest"]:
                    stats["date_range"]["earliest"] = file_date
                if stats["date_range"]["latest"] is None or file_date > stats["date_range"]["latest"]:
                    stats["date_range"]["latest"] = file_date
            except (IndexError, ValueError):
                pass

        # 转换日期为字符串
        if stats["date_range"]["earliest"]:
            stats["date_range"]["earliest"] = stats["date_range"]["earliest"].strftime("%Y-%m-%d")
        if stats["date_range"]["latest"]:
            stats["date_range"]["latest"] = stats["date_range"]["latest"].strftime("%Y-%m-%d")

        # 转换大小为可读格式
        stats["total_size_human"] = self._human_readable_size(stats["total_size_bytes"])

        return stats

    @staticmethod
    def _human_readable_size(size_bytes: int) -> str:
        """将字节大小转换为人类可读格式"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
