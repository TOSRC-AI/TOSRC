import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

BASE_URL = "http://localhost:8765"


def test_api_interfaces():
    print("=== 测试API接口 ===")

    # 测试1：健康检查接口
    print("\n1. 测试健康检查接口：")
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    print(f"✅ 健康检查成功：当前加载规则数 {data['loaded_rules']}")

    # 测试2：路由接口
    print("\n2. 测试路由接口：")
    payload = {"input_text": "明天北京天气怎么样"}
    resp = requests.post(f"{BASE_URL}/api/v1/route", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    print(
        f"✅ 路由接口成功：路由到 {data['data']['route_to']}，来源 {data['data']['source']}，置信度 {data['data']['confidence']:.2f}"
    )

    # 测试3：意图识别接口
    print("\n3. 测试意图识别接口：")
    resp = requests.post(f"{BASE_URL}/api/v1/intent", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    print(f"✅ 意图接口成功：意图 {data['data']['intent']}，置信度 {data['data']['confidence']:.2f}")

    # 测试4：实体提取接口
    print("\n4. 测试实体提取接口：")
    resp = requests.post(f"{BASE_URL}/api/v1/entity", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    print(f"✅ 实体接口成功：提取到 {len(data['data']['entities'])} 个实体")

    # 测试5：异常输入处理
    print("\n5. 测试异常输入处理：")
    payload = {"input_text": ""}
    resp = requests.post(f"{BASE_URL}/api/v1/route", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    print("✅ 空输入处理成功")

    print("\n🎉 API接口所有测试通过！")


if __name__ == "__main__":
    try:
        test_api_interfaces()
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        import traceback

        traceback.print_exc()
