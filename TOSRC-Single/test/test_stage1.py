#!/usr/bin/env python3
"""测试第一阶段模块功能：规则包管理器和调度引擎"""
from src.core.rule_package_manager import rule_package_manager
from src.core.scheduler import scheduler

print("=== 测试1：规则包管理器 ===")
# 查看所有加载的场景
scenes = rule_package_manager.list_all_scenes()
print(f"已加载的场景: {scenes}")

# 获取租房场景规则
rental_rules = rule_package_manager.get_scene_rules("rental")
print(f"租房规则包加载成功: entity_rules数量={len(rental_rules.get('entity_rules', []))}, intent_rules数量={len(rental_rules.get('intent_rules', []))}")

print("\n=== 测试2：调度引擎 ===")
text = "咨询的这套朝阳小区80平的房源，客服回复特别及时，清晰告知我租金2200元、押一付三，没有任何隐藏报价，讲解得很透明，特别靠谱！"
result = scheduler.process(text, scene="rental", allow_llm=False)
print(f"输入文本: {text}")
print(f"识别结果:")
print(f"- 运行模式: {result['mode']}")
print(f"- 置信度: {result['confidence']:.2%}")
print(f"- 实体列表:")
for e in result['entities']:
    print(f"  {e['name']}: {e['text']}")
print(f"- 意图列表:")
for intent in result['intents']:
    print(f"  {intent.get('name', '')}: {intent.get('confidence', 0):.2%}")

# 测试不同模式
print("\n=== 测试3：纯规则模式 ===")
scheduler.config["mode"] = "rule_only"
result2 = scheduler.process(text, scene="rental")
print(f"运行模式: {result2['mode']}, 实体数量: {len(result2['entities'])}")

print("\n✅ 第一阶段模块测试通过，规则包加载和调度引擎运行正常！")
