#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RouteLogger 单元测试
"""
import json
from datetime import datetime, timedelta

import pytest

from src.utils.route_logger import RouteLogger


@pytest.mark.unit
class TestRouteLogger:
    """测试 RouteLogger 类"""

    def test_save_basic(self, temp_log_dir):
        """测试基本保存功能"""
        logger = RouteLogger(temp_log_dir)

        logger.save(
            text="测试文本",
            intent={"intent_code": "test", "intent_name": "测试意图"},
            confidence=0.95
        )

        logger.flush()

        # 查询验证
        records = logger.query(limit=10)
        assert len(records) == 1
        assert records[0]["text"] == "测试文本"
        assert records[0]["intent_code"] == "test"
        assert records[0]["confidence"] == 0.95

        logger.close()

    def test_save_with_all_fields(self, temp_log_dir):
        """测试保存完整字段"""
        logger = RouteLogger(temp_log_dir)

        logger.save(
            text="我想租个3000块的房子",
            intent={
                "intent_code": "budget_query",
                "intent_name": "预算查询",
                "intent_level": 2
            },
            entities=[
                {"type": "amount", "text": "3000块", "value": 3000},
                {"type": "room", "text": "两室一厅", "value": "2室1厅"}
            ],
            confidence=0.92,
            mode="rule",
            latency_ms=45,
            user_id="user_123",
            scene="rental",
            emotion={"type": "neutral", "score": 0.5},
            request_id="req_abc123"
        )

        logger.flush()

        records = logger.query(limit=10)
        assert len(records) == 1

        record = records[0]
        assert record["text"] == "我想租个3000块的房子"
        assert record["intent_code"] == "budget_query"
        assert record["intent_name"] == "预算查询"
        assert len(record["entities"]) == 2
        assert record["mode"] == "rule"
        assert record["latency_ms"] == 45
        assert record["user_id"] == "user_123"
        assert record["scene"] == "rental"
        assert record["request_id"] == "req_abc123"

        logger.close()

    def test_query_with_filters(self, temp_log_dir):
        """测试带过滤的查询"""
        logger = RouteLogger(temp_log_dir)

        # 写入多条记录
        logger.save(text="文本1", intent={"intent_code": "A"}, confidence=0.9)
        logger.save(text="文本2", intent={"intent_code": "B"}, confidence=0.8)
        logger.save(text="文本3", intent={"intent_code": "A"}, confidence=0.95)

        logger.flush()

        # 按意图过滤
        records = logger.query(intent_code="A", limit=10)
        assert len(records) == 2
        assert all(r["intent_code"] == "A" for r in records)

        logger.close()

    def test_query_with_time_range(self, temp_log_dir):
        """测试按时间范围查询"""
        logger = RouteLogger(temp_log_dir)

        # 写入记录
        logger.save(text="近期记录", intent={"intent_code": "test"})
        logger.flush()

        # 查询最近1天
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)

        records = logger.query(start_time=start_time, end_time=end_time, limit=10)
        assert len(records) >= 1

        # 查询1小时前（应该查不到）
        start_time = end_time - timedelta(hours=1)
        end_time = end_time - timedelta(minutes=30)

        records = logger.query(start_time=start_time, end_time=end_time, limit=10)
        # 由于是刚刚写入的，可能查不到

        logger.close()

    def test_get_stats(self, temp_log_dir):
        """测试统计功能"""
        logger = RouteLogger(temp_log_dir)

        # 写入多种类型的记录
        logger.save(text="预算查询1", intent={"intent_code": "budget_query"}, confidence=0.95)
        logger.save(text="预算查询2", intent={"intent_code": "budget_query"}, confidence=0.88)
        logger.save(text="交通查询", intent={"intent_code": "transport_query"}, confidence=0.92)
        logger.save(text="宠物政策", intent={"intent_code": "pet_policy"}, confidence=0.85)

        logger.flush()

        stats = logger.get_stats(days=1)

        assert stats["total_requests"] == 4
        assert stats["average_confidence"] > 0
        assert len(stats["top_intents"]) > 0
        assert "budget_query" in stats["top_intents"]
        assert "mode_distribution" in stats
        assert "hourly_distribution" in stats

        logger.close()

    def test_get_intent_accuracy(self, temp_log_dir):
        """测试意图准确率统计"""
        logger = RouteLogger(temp_log_dir)

        # 写入不同置信度的记录
        logger.save(text="高置信度1", confidence=0.95)
        logger.save(text="高置信度2", confidence=0.92)
        logger.save(text="中置信度", confidence=0.80)
        logger.save(text="低置信度", confidence=0.50)

        logger.flush()

        accuracy = logger.get_intent_accuracy(days=1)

        assert accuracy["total"] == 4
        assert accuracy["high_confidence"]["count"] == 2
        assert accuracy["medium_confidence"]["count"] == 1
        assert accuracy["low_confidence"]["count"] == 1

        # 验证百分比
        assert accuracy["high_confidence"]["percentage"] == 50.0
        assert accuracy["medium_confidence"]["percentage"] == 25.0
        assert accuracy["low_confidence"]["percentage"] == 25.0

        logger.close()

    def test_query_stream(self, temp_log_dir):
        """测试流式查询"""
        logger = RouteLogger(temp_log_dir)

        # 写入多条记录
        for i in range(100):
            logger.save(text=f"文本{i}", intent={"intent_code": "test"})

        logger.flush()

        # 流式读取
        count = 0
        for record in logger.query_stream():
            assert "text" in record
            count += 1

        assert count == 100

        logger.close()

    def test_export_to_json(self, temp_log_dir, temp_dir):
        """测试导出为 JSON"""
        logger = RouteLogger(temp_log_dir)

        # 写入记录
        for i in range(10):
            logger.save(text=f"文本{i}", intent={"intent_code": "test"})

        logger.flush()

        # 导出
        output_path = temp_dir / "exported.json"
        count = logger.export_to_json(str(output_path))

        assert count == 10
        assert output_path.exists()

        # 验证导出内容
        import json
        with open(output_path, 'r') as f:
            data = json.load(f)
            assert len(data) == 10
            assert isinstance(data, list)

        logger.close()

    def test_empty_query(self, temp_log_dir):
        """测试空查询结果"""
        logger = RouteLogger(temp_log_dir)

        # 查询空目录
        records = logger.query(limit=10)
        assert len(records) == 0

        stats = logger.get_stats(days=1)
        assert stats["total_requests"] == 0

        logger.close()

    def test_multiple_scenes(self, temp_log_dir):
        """测试多场景数据"""
        logger = RouteLogger(temp_log_dir)

        # 不同场景的数据
        logger.save(text="租房1", intent={"intent_code": "rent"}, scene="rental")
        logger.save(text="租房2", intent={"intent_code": "rent"}, scene="rental")
        logger.save(text="酒店1", intent={"intent_code": "book"}, scene="hotel")

        logger.flush()

        # 按场景过滤
        rental_records = logger.query(scene="rental", limit=10)
        assert len(rental_records) == 2

        hotel_records = logger.query(scene="hotel", limit=10)
        assert len(hotel_records) == 1

        # 统计
        stats = logger.get_stats(days=1)
        assert stats["scene_distribution"]["rental"] == 2
        assert stats["scene_distribution"]["hotel"] == 1

        logger.close()

    def test_mode_distribution(self, temp_log_dir):
        """测试模式分布统计"""
        logger = RouteLogger(temp_log_dir)

        logger.save(text="规则1", mode="rule")
        logger.save(text="规则2", mode="rule")
        logger.save(text="规则3", mode="rule")
        logger.save(text="LLM1", mode="llm")
        logger.save(text="混合1", mode="hybrid")

        logger.flush()

        stats = logger.get_stats(days=1)

        assert stats["mode_distribution"]["rule"] == 3
        assert stats["mode_distribution"]["llm"] == 1
        assert stats["mode_distribution"]["hybrid"] == 1

        logger.close()
