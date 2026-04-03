#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSONLLogger 单元测试
"""
import json
import os
import gzip
from datetime import datetime
from pathlib import Path

import pytest

from src.utils.jsonl_logger import JSONLLogger


@pytest.mark.unit
class TestJSONLLogger:
    """测试 JSONLLogger 类"""

    def test_init_creates_directory(self, temp_dir):
        """测试初始化时创建目录"""
        log_dir = temp_dir / "new_logs"
        assert not log_dir.exists()

        logger = JSONLLogger(str(log_dir), "test")
        assert log_dir.exists()
        logger.close()

    def test_write_single_record(self, temp_dir):
        """测试写入单条记录"""
        logger = JSONLLogger(str(temp_dir), "test", buffer_size=1)

        record = {"key": "value", "number": 123}
        logger.write(record)

        # 检查文件
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_dir / f"test_{today}.jsonl"
        assert log_file.exists()

        # 读取验证
        with open(log_file, 'r') as f:
            line = f.readline().strip()
            saved = json.loads(line)
            assert saved["key"] == "value"
            assert saved["number"] == 123
            assert "timestamp" in saved

        logger.close()

    def test_write_multiple_records(self, temp_dir):
        """测试写入多条记录"""
        logger = JSONLLogger(str(temp_dir), "test", buffer_size=10)

        for i in range(5):
            logger.write({"id": i, "data": f"item_{i}"})

        logger.flush()

        # 验证所有记录
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_dir / f"test_{today}.jsonl"

        with open(log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 5

            for i, line in enumerate(lines):
                record = json.loads(line)
                assert record["id"] == i
                assert record["data"] == f"item_{i}"

        logger.close()

    def test_buffer_flush(self, temp_dir):
        """测试缓冲区刷新"""
        logger = JSONLLogger(str(temp_dir), "test", buffer_size=3)

        # 写入2条（不触发自动刷新）
        logger.write({"id": 1})
        logger.write({"id": 2})

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_dir / f"test_{today}.jsonl"

        # 手动刷新前文件可能不存在或为空
        logger.flush()

        # 刷新后应该写入文件
        assert log_file.exists()
        with open(log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 2

        logger.close()

    def test_immediate_write(self, temp_dir):
        """测试立即写入模式"""
        logger = JSONLLogger(str(temp_dir), "test", buffer_size=10)

        # 使用 immediate=True 立即写入
        logger.write({"urgent": True}, immediate=True)

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_dir / f"test_{today}.jsonl"

        # 不需要 flush 就应该写入
        with open(log_file, 'r') as f:
            content = f.read()
            assert "urgent" in content

        logger.close()

    def test_context_manager(self, temp_dir):
        """测试上下文管理器"""
        with JSONLLogger(str(temp_dir), "test") as logger:
            logger.write({"test": "data"})

        # 退出后文件应该存在
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_dir / f"test_{today}.jsonl"
        assert log_file.exists()

    def test_read_all(self, temp_dir):
        """测试读取所有记录"""
        logger = JSONLLogger(str(temp_dir), "test", buffer_size=1)

        records = [
            {"id": 1, "name": "alice"},
            {"id": 2, "name": "bob"},
            {"id": 3, "name": "charlie"}
        ]

        for record in records:
            logger.write(record)

        logger.close()

        # 读取
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_dir / f"test_{today}.jsonl"
        read_records = JSONLLogger.read_all(str(log_file))

        assert len(read_records) == 3
        assert read_records[0]["name"] == "alice"
        assert read_records[1]["name"] == "bob"
        assert read_records[2]["name"] == "charlie"

    def test_read_stream(self, temp_dir):
        """测试流式读取"""
        logger = JSONLLogger(str(temp_dir), "test", buffer_size=1)

        for i in range(5):
            logger.write({"id": i})

        logger.close()

        # 流式读取
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_dir / f"test_{today}.jsonl"

        count = 0
        for record in JSONLLogger.read(str(log_file)):
            assert "id" in record
            count += 1

        assert count == 5

    def test_read_with_filter(self, temp_dir):
        """测试带过滤的读取"""
        logger = JSONLLogger(str(temp_dir), "test", buffer_size=1)

        logger.write({"type": "A", "value": 1})
        logger.write({"type": "B", "value": 2})
        logger.write({"type": "A", "value": 3})

        logger.close()

        # 过滤函数
        def filter_type_a(record):
            return record.get("type") == "A"

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_dir / f"test_{today}.jsonl"

        filtered = JSONLLogger.read_all(str(log_file), filter_func=filter_type_a)

        assert len(filtered) == 2
        assert all(r["type"] == "A" for r in filtered)

    def test_compress_decompress(self, temp_dir):
        """测试压缩和解压"""
        # 创建测试文件
        test_file = temp_dir / "test.jsonl"
        with open(test_file, 'w') as f:
            for i in range(100):
                f.write(json.dumps({"id": i, "data": "x" * 100}) + "\n")

        original_size = test_file.stat().st_size

        # 压缩
        compressed = temp_dir / "test.jsonl.gz"
        result = JSONLLogger.compress(str(test_file), str(compressed))

        assert compressed.exists()
        assert result["original_size"] == original_size
        assert result["compressed_size"] < original_size

        # 解压
        decompressed = temp_dir / "test_decompressed.jsonl"
        JSONLLogger.decompress(str(compressed), str(decompressed))

        # 验证内容
        with open(decompressed, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 100

    def test_get_stats(self, temp_dir):
        """测试获取统计信息"""
        logger = JSONLLogger(str(temp_dir), "test", buffer_size=1)

        # 写入一些数据
        for i in range(10):
            logger.write({"id": i})

        logger.close()

        stats = logger.get_stats()

        assert stats["log_dir"] == str(temp_dir)
        assert stats["name"] == "test"
        assert stats["total_files"] == 1
        assert stats["total_size_bytes"] > 0
        assert "total_size_human" in stats

    def test_invalid_json_handling(self, temp_dir):
        """测试处理无效的 JSON 行"""
        # 手动创建一个包含无效 JSON 的文件
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_dir / f"test_{today}.jsonl"

        with open(log_file, 'w') as f:
            f.write('{"valid": true}\n')
            f.write('invalid json line\n')
            f.write('{"valid": true}\n')

        # 应该跳过无效行，读取有效行
        records = JSONLLogger.read_all(str(log_file))
        assert len(records) == 2

    def test_thread_safety(self, temp_dir):
        """测试线程安全"""
        import threading

        logger = JSONLLogger(str(temp_dir), "test", buffer_size=100)
        errors = []

        def write_records(start_id):
            try:
                for i in range(50):
                    logger.write({"thread_id": start_id, "seq": i})
            except Exception as e:
                errors.append(e)

        # 创建多个线程写入
        threads = []
        for i in range(4):
            t = threading.Thread(target=write_records, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        logger.flush()

        # 检查是否有错误
        assert len(errors) == 0, f"线程安全错误: {errors}"

        # 验证记录数
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_dir / f"test_{today}.jsonl"

        with open(log_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 200  # 4线程 * 50条

        logger.close()

    def test_custom_timestamp(self, temp_dir):
        """测试自定义时间戳"""
        logger = JSONLLogger(str(temp_dir), "test", buffer_size=1)

        custom_time = "2026-01-01T00:00:00"
        logger.write({"data": "test"}, timestamp=custom_time)

        logger.close()

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = temp_dir / f"test_{today}.jsonl"

        with open(log_file, 'r') as f:
            record = json.loads(f.readline())
            assert record["timestamp"] == custom_time
