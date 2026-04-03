import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import yaml
from src.rule_engine import RuleEngine


def test_rule_engine():
    print("=== 测试规则引擎 ===")
    rule_engine = RuleEngine(rule_config_path="config/rules.yaml")

    # 测试1：关键词匹配
    print("\n1. 测试关键词匹配：")
    result = rule_engine.match("明天北京天气怎么样")
    assert result is not None
    assert result["rule_id"] == "rule_001"
    assert result["action"]["route_to"] == "weather_service"
    print(f"✅ 关键词匹配成功：路由到 {result['action']['route_to']}，置信度 {result['confidence']}")

    # 测试2：正则匹配
    print("\n2. 测试正则匹配：")
    result = rule_engine.match("现在几点了")
    assert result is not None
    assert result["rule_id"] == "rule_002"
    assert result["action"]["route_to"] == "time_service"
    print(f"✅ 正则匹配成功：路由到 {result['action']['route_to']}，置信度 {result['confidence']}")

    # 测试3：多规则优先级
    print("\n3. 测试多规则优先级：")
    result = rule_engine.match("今天天气怎么样，现在几点了")
    assert result is not None
    assert result["rule_id"] == "rule_001"  # 天气规则优先级更高(3>2)
    print(f"✅ 优先级测试成功：优先匹配高优先级规则 {result['rule_id']}")

    # 测试4：规则热更新
    print("\n4. 测试规则热更新：")
    test_rule = {
        "id": "test_001",
        "name": "测试规则",
        "priority": 10,
        "match_type": "keyword",
        "pattern": "测试热更新",
        "confidence": 1.0,
        "action": {"route_to": "test_service"},
        "enabled": True,
    }

    with open("config/rules.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config["rules"].append(test_rule)
    with open("config/rules.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True)

    time.sleep(0.5)
    result = rule_engine.match("测试热更新")
    assert result is not None
    assert result["rule_id"] == "test_001"
    print("✅ 规则热更新成功")

    # 恢复原配置
    config["rules"].pop()
    with open("config/rules.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True)
    rule_engine.load_rules()
    print("✅ 恢复原规则配置成功")

    print("\n🎉 规则引擎所有测试通过！")


if __name__ == "__main__":
    try:
        test_rule_engine()
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        import traceback

        traceback.print_exc()
