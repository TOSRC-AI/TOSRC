#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志归档管理器
支持自动压缩、清理过期日志
"""
import os
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import threading

from .jsonl_logger import JSONLLogger


class LogArchiver:
    """
    日志归档管理器

    功能：
    - 自动压缩N天前的日志
    - 清理过期的归档文件
    - 支持定时任务运行
    - 线程安全

    使用示例：
        archiver = LogArchiver("data/logs")
        archiver.archive_old_logs(days=7)  # 归档7天前的日志
        archiver.schedule_daily_archive()  # 每天自动归档
    """

    def __init__(self,
                 log_dir: str,
                 archive_dir: str = "archive",
                 compress_after_days: int = 7,
                 delete_after_days: int = 90):
        """
        初始化归档管理器

        Args:
            log_dir: 日志文件目录
            archive_dir: 归档目录名（相对于log_dir）
            compress_after_days: N天后压缩
            delete_after_days: N天后删除
        """
        self.log_dir = Path(log_dir)
        self.archive_dir = self.log_dir / archive_dir
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        self.compress_after_days = compress_after_days
        self.delete_after_days = delete_after_days

        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def archive_old_logs(self,
                         log_name: str = "routes",
                         days: Optional[int] = None,
                         compress: bool = True) -> Dict[str, Any]:
        """
        归档旧日志

        Args:
            log_name: 日志名称前缀
            days: 归档N天前的日志（默认使用 compress_after_days）
            compress: 是否压缩

        Returns:
            归档结果统计
        """
        days = days or self.compress_after_days
        cutoff = datetime.now() - timedelta(days=days)

        archived = []
        skipped = []
        errors = []

        with self._lock:
            # 查找需要归档的日志文件
            pattern = f"{log_name}_*.jsonl"

            for log_file in self.log_dir.glob(pattern):
                # 跳过已压缩和已在归档目录的文件
                if log_file.suffix == '.gz' or self.archive_dir in log_file.parents:
                    continue

                try:
                    # 解析文件名中的日期
                    date_str = log_file.stem.split("_")[1]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")

                    if file_date < cutoff:
                        # 需要归档
                        if compress:
                            archive_path = self.archive_dir / f"{log_file.stem}.jsonl.gz"

                            # 检查是否已存在
                            if archive_path.exists():
                                skipped.append({
                                    "file": str(log_file),
                                    "reason": "archive already exists"
                                })
                                continue

                            result = JSONLLogger.compress(
                                log_file,
                                archive_path,
                                remove_source=True
                            )
                            archived.append(result)
                        else:
                            # 仅移动，不压缩
                            archive_path = self.archive_dir / log_file.name
                            shutil.move(str(log_file), str(archive_path))
                            archived.append({
                                "source": str(log_file),
                                "dest": str(archive_path),
                                "compressed": False
                            })

                except Exception as e:
                    errors.append({
                        "file": str(log_file),
                        "error": str(e)
                    })

        return {
            "success": len(errors) == 0,
            "archived_count": len(archived),
            "skipped_count": len(skipped),
            "error_count": len(errors),
            "archived_files": archived,
            "skipped_files": skipped,
            "errors": errors,
            "cutoff_date": cutoff.strftime("%Y-%m-%d")
        }

    def cleanup_old_archives(self, days: Optional[int] = None) -> Dict[str, Any]:
        """
        清理过期的归档文件

        Args:
            days: 删除N天前的归档（默认使用 delete_after_days）

        Returns:
            清理结果统计
        """
        days = days or self.delete_after_days
        cutoff = datetime.now() - timedelta(days=days)

        deleted = []
        errors = []

        with self._lock:
            for archive_file in self.archive_dir.glob("*.jsonl*"):
                try:
                    # 解析文件名中的日期（兼容 .jsonl.gz：name 格式为 routes_YYYY-MM-DD.jsonl.gz）
                    date_str = archive_file.name.split("_")[1].split(".")[0]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")

                    if file_date < cutoff:
                        # 删除过期归档
                        file_size = archive_file.stat().st_size
                        archive_file.unlink()
                        deleted.append({
                            "file": str(archive_file),
                            "size": file_size,
                            "date": date_str
                        })

                except Exception as e:
                    errors.append({
                        "file": str(archive_file),
                        "error": str(e)
                    })

        return {
            "success": len(errors) == 0,
            "deleted_count": len(deleted),
            "error_count": len(errors),
            "deleted_files": deleted,
            "errors": errors,
            "cutoff_date": cutoff.strftime("%Y-%m-%d")
        }

    def get_archive_stats(self) -> Dict[str, Any]:
        """获取归档统计信息"""
        stats = {
            "log_dir": str(self.log_dir),
            "archive_dir": str(self.archive_dir),
            "active_files": [],
            "archived_files": [],
            "total_active_size": 0,
            "total_archive_size": 0,
            "compression_ratio": 0.0
        }

        # 活跃文件（未归档）
        for log_file in self.log_dir.glob("*.jsonl"):
            if self.archive_dir not in log_file.parents:
                file_stat = log_file.stat()
                stats["active_files"].append({
                    "name": log_file.name,
                    "size": file_stat.st_size,
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                })
                stats["total_active_size"] += file_stat.st_size

        # 归档文件
        original_size = 0
        for archive_file in self.archive_dir.glob("*.jsonl*"):
            file_stat = archive_file.stat()
            stats["archived_files"].append({
                "name": archive_file.name,
                "size": file_stat.st_size,
                "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                "compressed": archive_file.suffix == '.gz'
            })
            stats["total_archive_size"] += file_stat.st_size

        # 计算压缩比（估算）
        if stats["total_archive_size"] > 0:
            # 假设压缩后约为原大小的20%
            estimated_original = stats["total_archive_size"] * 5
            stats["compression_ratio"] = round(
                (1 - stats["total_archive_size"] / estimated_original) * 100, 1
            )

        # 转换为可读格式
        stats["total_active_size_human"] = self._human_readable_size(
            stats["total_active_size"]
        )
        stats["total_archive_size_human"] = self._human_readable_size(
            stats["total_archive_size"]
        )

        return stats

    def run_maintenance(self) -> Dict[str, Any]:
        """
        运行完整的维护任务
        1. 归档旧日志
        2. 清理过期归档

        Returns:
            维护结果
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "archive_result": None,
            "cleanup_result": None
        }

        # 归档
        archive_result = self.archive_old_logs()
        results["archive_result"] = archive_result

        # 清理
        cleanup_result = self.cleanup_old_archives()
        results["cleanup_result"] = cleanup_result

        results["success"] = (
            archive_result.get("success", False) and
            cleanup_result.get("success", False)
        )

        return results

    def schedule_daily_archive(self, hour: int = 2, minute: int = 0):
        """
        启动定时归档任务（每天指定时间运行）

        Args:
            hour: 小时（0-23）
            minute: 分钟（0-59）
        """
        if self._running:
            print("定时归档任务已在运行")
            return

        self._running = True

        def run_scheduled():
            while self._running:
                now = datetime.now()
                scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                if scheduled_time < now:
                    scheduled_time += timedelta(days=1)

                wait_seconds = (scheduled_time - now).total_seconds()
                print(f"下次归档时间: {scheduled_time}, 等待 {wait_seconds:.0f} 秒")

                # 等待到指定时间
                time.sleep(min(wait_seconds, 3600))  # 最多等1小时检查一次

                if datetime.now() >= scheduled_time:
                    print(f"开始执行定时归档任务...")
                    result = self.run_maintenance()
                    print(f"归档任务完成: {result}")

        self._thread = threading.Thread(target=run_scheduled, daemon=True)
        self._thread.start()
        print(f"定时归档任务已启动，每天 {hour:02d}:{minute:02d} 执行")

    def stop_scheduled(self):
        """停止定时归档任务"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("定时归档任务已停止")

    @staticmethod
    def _human_readable_size(size_bytes: int) -> str:
        """将字节大小转换为人类可读格式"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"


# 便捷函数
def create_default_archiver(log_type: str = "routes") -> LogArchiver:
    """
    创建默认配置的归档管理器

    Args:
        log_type: 日志类型（routes, feedback, training等）

    Returns:
        LogArchiver 实例
    """
    log_dir = f"data/logs/{log_type}"
    return LogArchiver(
        log_dir=log_dir,
        archive_dir="archive",
        compress_after_days=7,    # 7天后压缩
        delete_after_days=90      # 90天后删除
    )
