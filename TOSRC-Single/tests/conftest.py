#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest 全局配置和 Fixtures
"""
import os
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

import pytest

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="function")
def temp_dir():
    """创建临时目录，测试结束后自动清理"""
    tmp = tempfile.mkdtemp(prefix="tosrc_test_")
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="function")
def temp_db(temp_dir):
    """创建临时数据库"""
    db_path = temp_dir / "test.db"
    return str(db_path)


@pytest.fixture(scope="function")
def temp_log_dir(temp_dir):
    """创建临时日志目录"""
    log_dir = temp_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    return str(log_dir)


@pytest.fixture(scope="function")
def sample_intent_data():
    """示例意图数据"""
    return {
        "intent_id": 1,
        "intent_code": "budget_query",
        "intent_name": "预算查询",
        "level": 2,
        "priority": 100,
        "is_enabled": True
    }


@pytest.fixture(scope="function")
def sample_route_record():
    """示例路由记录"""
    return {
        "text": "我想租个3000块的房子",
        "intent": {
            "intent_code": "budget_query",
            "intent_name": "预算查询"
        },
        "entities": [
            {"type": "amount", "text": "3000块", "value": 3000}
        ],
        "confidence": 0.95,
        "mode": "rule",
        "latency_ms": 45,
        "user_id": "test_user",
        "scene": "rental"
    }


@pytest.fixture(scope="function")
def mock_datetime():
    """Mock  datetime"""
    return datetime(2026, 4, 3, 12, 0, 0)


# 标记过滤器
def pytest_configure(config):
    """配置 pytest"""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """修改测试项"""
    for item in items:
        # 自动添加标记
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
