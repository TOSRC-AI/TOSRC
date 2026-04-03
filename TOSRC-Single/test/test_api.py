#!/usr/bin/env python3
"""测试后端API接口"""
import requests
import json

url = "http://localhost:8080/api/v1/chat"
headers = {"Content-Type": "application/json"}
data = {
    "text": "咨询的这套朝阳小区80平的房源，客服回复特别及时，清晰告知我租金2200元、押一付三，没有任何隐藏报价，讲解得很透明，特别靠谱！",
    "stream": False
}

response = requests.post(url, headers=headers, data=json.dumps(data))
result = response.json()
print("API返回结果:")
print(json.dumps(result, indent=2, ensure_ascii=False))

print("\n=== 实体提取结果 ===")
for e in result.get("entities", []):
    print(f"- {e['name']}: {e['text']}")
