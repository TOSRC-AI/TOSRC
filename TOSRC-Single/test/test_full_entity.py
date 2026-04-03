#!/usr/bin/env python3
"""
全面测试业务实体和金额识别功能
"""
from src.bionic.neuron_core import synapse_core

test_cases = [
    # 基础测试
    ("请帮我查询下两三千北京的租房，物业费包含吗", [
        ("城市", "北京"),
        ("租金", "两三千"),
        ("物业费", "物业费")
    ]),
    ("帮我找个预算3500元左右的两室一厅，朝南", [
        ("租金", "预算"),
        ("租金", "3500元"),
        ("户型", "两室一厅"),
        ("朝向", "朝南")
    ]),
    ("不超过2500的整租房，最好是精装修", [
        ("租金", "2500"),
        ("户型", "整租"),
        ("装修", "精装修")
    ]),
    ("1500到2000的合租房，在朝阳区", [
        ("租金", "1500到2000"),
        ("户型", "合租"),
        ("区域", "朝阳区")
    ]),
    ("三四千的三室一厅，中楼层就行", [
        ("租金", "三四千"),
        ("户型", "三室一厅"),
        ("楼层", "中楼层")
    ]),
    ("房租大概三千，水电费自付，押金一个月", [
        ("租金", "房租"),
        ("租金", "三千"),
        ("水电费", "水电费"),
        ("押金", "押金")
    ]),
    ("上海的两室一厅，价格2w左右", [
        ("城市", "上海"),
        ("户型", "两室一厅"),
        ("租金", "2w")
    ]),
    ("广州的租房，最低两千以上，最高不超过三千五", [
        ("城市", "广州"),
        ("租金", "两千以上"),
        ("租金", "三千五")
    ])
]

print("="*60)
print("业务实体和金额识别全面测试")
print("="*60)

passed = 0
failed = 0

for text, expect_entities in test_cases:
    print(f"\n测试文本: {text}")
    entities = synapse_core._extract_entities(text)
    
    # 转换为字典方便对比
    actual_map = {}
    for e in entities:
        if e["name"] not in actual_map:
            actual_map[e["name"]] = []
        actual_map[e["name"]].append(e["text"])
    
    ok = True
    for expect_name, expect_text in expect_entities:
        if expect_name not in actual_map:
            print(f"❌  缺失实体: {expect_name}")
            ok = False
        else:
            found = False
            for actual_text in actual_map[expect_name]:
                if expect_text in actual_text:
                    found = True
                    break
            if not found:
                print(f"❌  实体[{expect_name}]不匹配，预期包含[{expect_text}]，实际: {actual_map[expect_name]}")
                ok = False
    
    # 检查是否有多余实体
    for actual_name in actual_map:
        found = False
        for expect_name, _ in expect_entities:
            if expect_name == actual_name:
                found = True
                break
        if not found:
            print(f"⚠️  多余实体: {actual_name}: {actual_map[actual_name]}")
    
    if ok:
        passed +=1
        print("✅  PASS")
        for e in entities:
            print(f"  - {e['name']}: {e['text']}")
    else:
        failed +=1

print("\n" + "="*60)
print(f"测试结果: 共{len(test_cases)}条用例, 成功{passed}条, 失败{failed}条")
print("="*60)
