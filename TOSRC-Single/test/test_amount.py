#!/usr/bin/env python3
"""
金额识别功能测试脚本
"""
from src.bionic.neuron_core import synapse_core

# 测试用例
test_cases = [
    # 纯数字
    ("预算2000的两室一厅", ["2000"]),
    ("预算3500.50的房子", ["3500.50"]),
    ("1500-2000的一居室", ["1500-2000"]),
    
    # 中文数字
    ("预算两千的房子", ["两千（2000元）"]),
    ("三千五左右的两室", ["三千五（3500元）"]),
    ("一万二的整租房源", ["一万二（12000元）"]),
    
    # 带单位
    ("2000元的单间", ["2000元"]),
    ("3500块的一居室", ["3500块"]),
    ("预算2k的短租房", ["2k"]),
    ("2w左右的两室一厅", ["2w"]),
    ("2万的整租房", ["2万"]),
    
    # 带区间
    ("1500~2000的合租房", ["1500~2000"]),
    ("1500-2000的房子", ["1500-2000"]),
    ("一千五到两千的房源", ["一千五到两千（1500-2000元）"]),
    
    # 口语化
    ("两千左右的房子", ["两千左右（2000元）"]),
    ("大概三千的一居室", ["大概三千（3000元）"]),
    ("不超过2500的单间", ["不超过2500"]),
]

print("="*60)
print("金额识别功能测试")
print("="*60)

passed = 0
failed = 0

for text, expect_amounts in test_cases:
    result = synapse_core._extract_entities(text)
    actual_amounts = [e["text"] for e in result if e["name"] == "租金"]
    
    # 检查是否包含所有预期金额
    ok = True
    for expect in expect_amounts:
        if expect not in actual_amounts:
            ok = False
            break
    
    if ok:
        passed +=1
        status = "✅  PASS"
    else:
        failed +=1
        status = "❌  FAIL"
    
    print(f"\n{status} 测试文本: {text}")
    print(f"   预期: {expect_amounts}")
    print(f"   实际: {actual_amounts}")

print("\n" + "="*60)
print(f"测试结果: 共{len(test_cases)}条用例, 成功{passed}条, 失败{failed}条")
print("="*60)
