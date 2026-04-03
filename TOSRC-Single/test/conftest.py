import pytest
import yaml
from fastapi.testclient import TestClient
import sys
import os

# 添加上级目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

@pytest.fixture(scope="session")
def test_client():
    """测试客户端fixture"""
    return TestClient(app)

@pytest.fixture(scope="session")
def test_cases():
    """加载所有测试用例"""
    test_case_path = os.path.join(os.path.dirname(__file__), "test_cases/core_test_cases.yaml")
    with open(test_case_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="session")
def api_headers():
    """API请求头fixture"""
    return {
        "X-API-Key": "admin-llm-router-2026",
        "Content-Type": "application/json"
    }
