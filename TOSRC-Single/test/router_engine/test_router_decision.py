import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.router_decision import RouterDecisionEngine


def test_router_decision():
    print("=== 测试路由决策引擎 ===")
    router = RouterDecisionEngine()

    # 测试1：规则优先
    print("\n1. 测试规则优先策略：")
    rule_match = {"confidence": 0.8, "action": {"route_to": "weather_service"}}
    decision = router.decide_route(rule_match_result=rule_match)
    assert decision["source"] == "rule_engine"
    assert decision["route_to"] == "weather_service"
    print(f"✅ 规则优先成功：来源 {decision['source']}，路由到 {decision['route_to']}")

    # 测试2：模型兜底
    print("\n2. 测试模型兜底策略：")
    model_match = {"confidence": 0.7, "action": {"route_to": "chat_llm_service"}}
    decision = router.decide_route(rule_match_result=None, model_match_result=model_match)
    assert decision["source"] == "model_engine"
    assert decision["route_to"] == "chat_llm_service"
    print(f"✅ 模型兜底成功：来源 {decision['source']}，路由到 {decision['route_to']}")

    # 测试3：默认路由
    print("\n3. 测试默认路由策略：")
    decision = router.decide_route(rule_match_result=None, model_match_result=None)
    assert decision["source"] == "default"
    assert decision["route_to"] == "default_llm_service"
    print(f"✅ 默认路由成功：来源 {decision['source']}，路由到 {decision['route_to']}")

    # 测试4：规则置信度不足时使用模型
    print("\n4. 测试规则置信度不足场景：")
    rule_match = {"confidence": 0.6, "action": {"route_to": "weather_service"}}
    model_match = {"confidence": 0.8, "action": {"route_to": "other_service"}}
    decision = router.decide_route(rule_match_result=rule_match, model_match_result=model_match)
    assert decision["source"] == "model_engine"
    assert decision["route_to"] == "other_service"
    print(f"✅ 规则置信度不足时使用模型成功：来源 {decision['source']}")

    print("\n🎉 路由决策引擎所有测试通过！")


if __name__ == "__main__":
    try:
        test_router_decision()
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        import traceback

        traceback.print_exc()
