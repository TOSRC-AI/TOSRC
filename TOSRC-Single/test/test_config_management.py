import pytest
import yaml
import os

# 直接加载测试用例
test_case_path = os.path.join(os.path.dirname(__file__), "test_cases/core_test_cases.yaml")
with open(test_case_path, "r", encoding="utf-8") as f:
    all_test_cases = yaml.safe_load(f)
config_test_cases = all_test_cases["config_test_cases"]

@pytest.mark.parametrize("config_test_case", config_test_cases)
def test_config_api(test_client, api_headers, config_test_case):
    """测试配置管理接口"""
    response = test_client.get(
        config_test_case["endpoint"],
        headers=api_headers
    )
    
    assert response.status_code == config_test_case["expected_status"], f"用例[{config_test_case['name']}]请求失败: {response.text}"
    
    if "expected_count" in config_test_case:
        data = response.json()
        assert len(data) >= config_test_case["expected_count"], f"用例[{config_test_case['name']}]返回数量错误，预期至少:{config_test_case['expected_count']}，实际:{len(data)}"
    
    if "expected_scene_ids" in config_test_case:
        data = response.json()
        actual_ids = [scene["scene_id"] for scene in data]
        for expected_id in config_test_case["expected_scene_ids"]:
            assert expected_id in actual_ids, f"用例[{config_test_case['name']}]缺失场景ID:{expected_id}"
    
    if "expected_fields" in config_test_case:
        data = response.json()
        for field in config_test_case["expected_fields"]:
            assert field in data, f"用例[{config_test_case['name']}]缺失字段:{field}"
