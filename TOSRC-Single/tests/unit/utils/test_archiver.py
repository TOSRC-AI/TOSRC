#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LogArchiver 单元测试
"""
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.utils.archiver import LogArchiver, create_default_archiver
from src.utils.jsonl_logger import JSONLLogger


@pytest.mark.unit
class TestLogArchiver:
    """测试 LogArchiver 类"""

    def test_init_creates_directories(self, temp_dir):
        """测试初始化创建目录"""
        log_dir = temp_dir / "logs"
        assert not log_dir.exists()

        archiver = LogArchiver(str(log_dir))
        assert log_dir.exists()
        assert (log_dir / "archive").exists()

    def test_archive_old_logs(self, temp_dir):
        """测试归档旧日志"""
        log_dir = temp_dir / "logs"
        log_dir.mkdir()

        # 创建今天的日志
        today = datetime.now().strftime("%Y-%m-%d")
        today_file = log_dir / f"routes_{today}.jsonl"
        today_file.write_text('{"test": "today"}\n')

        # 创建10天前的日志
        old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        old_file = log_dir / f"routes_{old_date}.jsonl"
        old_file.write_text('{"test": "old"}\n')

        # 归档7天前的日志
        archiver = LogArchiver(str(log_dir), compress_after_days=7)
        result = archiver.archive_old_logs()

        assert result["archived_count"] == 1
        assert result["error_count"] == 0

        # 验证旧文件已归档
        assert not old_file.exists()
        archive_file = log_dir / "archive" / f"routes_{old_date}.jsonl.gz"
        assert archive_file.exists()

        # 今天的文件应该还在
        assert today_file.exists()

    def test_cleanup_old_archives(self, temp_dir):
        """测试清理过期归档"""
        log_dir = temp_dir / "logs"
        archive_dir = log_dir / "archive"
        archive_dir.mkdir(parents=True)

        # 创建近期归档
        recent_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        recent_file = archive_dir / f"routes_{recent_date}.jsonl.gz"
        recent_file.write_text("recent")

        # 创建过期归档
        old_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        old_file = archive_dir / f"routes_{old_date}.jsonl.gz"
        old_file.write_text("old")

        # 清理90天前的归档
        archiver = LogArchiver(str(log_dir), delete_after_days=90)
        result = archiver.cleanup_old_archives()

        assert result["deleted_count"] == 1
        assert not old_file.exists()
        assert recent_file.exists()

    def test_get_archive_stats(self, temp_dir):
        """测试归档统计"""
        log_dir = temp_dir / "logs"
        log_dir.mkdir()

        # 创建活跃文件
        today = datetime.now().strftime("%Y-%m-%d")
        active_file = log_dir / f"routes_{today}.jsonl"
        active_file.write_text('{"test": "active"}\n')

        # 创建归档文件
        archive_dir = log_dir / "archive"
        archive_dir.mkdir()
        old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        archive_file = archive_dir / f"routes_{old_date}.jsonl.gz"
        archive_file.write_text("archived")

        archiver = LogArchiver(str(log_dir))
        stats = archiver.get_archive_stats()

        assert stats["total_active_size"] > 0
        assert len(stats["active_files"]) == 1
        assert len(stats["archived_files"]) == 1
        assert "total_active_size_human" in stats
        assert "total_archive_size_human" in stats

    def test_run_maintenance(self, temp_dir):
        """测试运行完整维护"""
        log_dir = temp_dir / "logs"
        log_dir.mkdir()

        # 创建需要归档的文件
        old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        old_file = log_dir / f"routes_{old_date}.jsonl"
        old_file.write_text('{"test": "old"}\n')

        archiver = LogArchiver(str(log_dir), compress_after_days=7, delete_after_days=90)
        result = archiver.run_maintenance()

        assert result["success"]
        assert "archive_result" in result
        assert "cleanup_result" in result
        assert result["archive_result"]["archived_count"] == 1

    def test_create_default_archiver(self):
        """测试创建默认归档器"""
        archiver = create_default_archiver("routes")
        assert isinstance(archiver, LogArchiver)
        assert "routes" in archiver.log_dir.name

    def test_no_files_to_archive(self, temp_dir):
        """测试无可归档文件的情况"""
        log_dir = temp_dir / "logs"
        log_dir.mkdir()

        archiver = LogArchiver(str(log_dir), compress_after_days=7)
        result = archiver.archive_old_logs()

        assert result["archived_count"] == 0
        assert result["skipped_count"] == 0
        assert result["error_count"] == 0

    def test_archive_already_exists(self, temp_dir):
        """测试归档文件已存在的情况"""
        log_dir = temp_dir / "logs"
        log_dir.mkdir()
        archive_dir = log_dir / "archive"
        archive_dir.mkdir()

        # 创建旧日志
        old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        old_file = log_dir / f"routes_{old_date}.jsonl"
        old_file.write_text('{"test": "old"}\n')

        # 创建已存在的归档
        existing_archive = archive_dir / f"routes_{old_date}.jsonl.gz"
        existing_archive.write_text("existing")

        archiver = LogArchiver(str(log_dir), compress_after_days=7)
        result = archiver.archive_old_logs()

        # 应该跳过已存在的归档
        assert result["archived_count"] == 0
        assert result["skipped_count"] == 1
