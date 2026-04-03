#!/usr/bin/env python3
"""测试正向匹配方案效果"""
from src.bionic.neuron_core import synapse_core

print("=== 测试场景1：面积数字误识别问题 ===")
text1 = "咨询的这套朝阳小区80平的房源，客服回复特别及时，清晰告知我租金2200元、押一付三，没有任何隐藏报价，讲解得很透明，特别靠谱！"
print(f"文本: {text1}")
entities1 = synapse_core._extract_entities(text1)
for e in entities1:
    print(f"- {e['name']}: {e['text']}")

print("\n=== 测试场景2：正常金额识别（带单位） ===")
text2 = "我要租两室一厅，月租3k5左右，不超4000"
print(f"文本: {text2}")
entities2 = synapse_core._extract_entities(text2)
for e in entities2:
    print(f"- {e['name']}: {e['text']}")

print("\n=== 测试场景3：无单位但有金额上下文 ===")
text3 = "这套房子租金多少？3500，押一付三"
print(f"文本: {text3}")
entities3 = synapse_core._extract_entities(text3)
for e in entities3:
    print(f"- {e['name']}: {e['text']}")

print("\n=== 测试场景4：纯数字无上下文（不识别） ===")
text4 = "这套房子80平，3室2厅，25楼，楼龄10年"
print(f"文本: {text4}")
entities4 = synapse_core._extract_entities(text4)
for e in entities4:
    print(f"- {e['name']}: {e['text']}")
