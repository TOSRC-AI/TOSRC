#!/usr/bin/env python3
"""测试核心实体提取逻辑（跳过API Key）"""
from src.bionic.neuron_core import synapse_core

text = "咨询的这套朝阳小区80平的房源，客服回复特别及时，清晰告知我租金2200元、押一付三，没有任何隐藏报价，讲解得很透明，特别靠谱！"
print(f"测试文本: {text}")
print("\n=== 实体提取结果 ===")
entities = synapse_core._extract_entities(text)
for e in entities:
    print(f"- {e['name']}: {e['text']}")

# 打印分类器判断结果
print("\n=== 语义分类器对80的判断 ===")
from src.utils.semantic_classifier import number_classifier
context = "80平的房源"
label, conf = number_classifier.predict(context)
print(f"上下文: {context}, 分类结果: {label}, 置信度: {conf:.2%}")
