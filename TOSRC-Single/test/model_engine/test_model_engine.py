import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model_engine import intent_model, entity_model


def test_model_engine():
    print("=== 测试轻量模型引擎 ===")

    # 测试1：意图识别
    print("\n1. 测试意图识别：")
    test_cases = ["明天北京天气怎么样", "现在几点了", "给我讲个笑话吧", "今天的股票行情怎么样"]

    for text in test_cases:
        result = intent_model.predict_intent(text)
        assert "intent" in result
        assert "confidence" in result
        assert "route_to" in result
        assert result["response_time"] < 10000  # 第一次模型加载预热允许更长时间
        print(
            f"✅ '{text}' -> 意图：{result['intent']}，置信度：{result['confidence']:.2f}，响应时间：{result['response_time']}ms"
        )

    # 测试2：实体提取
    print("\n2. 测试实体提取：")
    test_cases = ["明天北京天气怎么样", "下周一上海有雨吗", "张三昨天去了广州"]

    for text in test_cases:
        result = entity_model.extract_entities(text)
        assert "entities" in result
        assert result["response_time"] < 5000
        print(f"✅ '{text}' -> 提取到 {len(result['entities'])} 个实体，响应时间：{result['response_time']}ms")
        for ent in result["entities"]:
            print(f"   - {ent['type']}: {ent['text']} (置信度 {ent['confidence']:.2f})")

    print("\n🎉 轻量模型引擎所有测试通过！")


if __name__ == "__main__":
    try:
        test_model_engine()
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        import traceback

        traceback.print_exc()
