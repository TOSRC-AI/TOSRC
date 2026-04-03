#!/usr/bin/env python3
"""
测试BM25集成效果，验证语义容错能力
"""
import sys
sys.path.append('.')
from src.bionic.neuron_core import synapse_core
from src.bm25_utils import intent_bm25
import jieba
jieba.setLogLevel(jieba.logging.INFO)

def test_bm25_integration():
    print("=== BM25集成效果测试 ===")
    
    # 测试用例：包含错别字、同义词、口语化表达
    test_cases = [
        # 租房场景测试
        {"text": "组个两室一厅，预算3千", "expected_intent": "租房查询", "desc": "错别字+数字简写"},
        {"text": "找个两居室，价格适中就行", "expected_intent": "租房查询", "desc": "同义词+口语化"},
        {"text": "有没有地铁附近的房子，性价比高的", "expected_intent": "租房查询", "desc": "模糊语义"},
        {"text": "预算不高，想要个一室户，拎包入住", "expected_intent": "租房查询", "desc": "行业术语"},
        
        # 报修场景测试
        {"text": "我家热水器坏了，麻烦帮忙修下呗", "expected_intent": "房源报修", "desc": "口语化表达"},
        {"text": "卫生间漏水了，快来处理下", "expected_intent": "房源报修", "desc": "问题描述"},
        {"text": "空调不制冷，热死了", "expected_intent": "房源报修", "desc": "现象描述"},
        {"text": "灯不亮了，换个灯泡", "expected_intent": "房源报修", "desc": "需求描述"},
        
        # 天气场景测试
        {"text": "明天出门需要带伞不", "expected_intent": "天气查询", "desc": "间接询问"},
        {"text": "这两天热不热，穿啥衣服合适", "expected_intent": "天气查询", "desc": "关联询问"},
        {"text": "周末会不会下雨啊", "expected_intent": "天气查询", "desc": "口语化询问"},
        {"text": "下周降温吗，需要穿羽绒服不", "expected_intent": "天气查询", "desc": "生活关联"},
        
        # 缴费场景测试
        {"text": "这个月电费多少钱啊", "expected_intent": "缴费查询", "desc": "常规查询"},
        {"text": "水费在哪里交啊", "expected_intent": "缴费查询", "desc": "方式询问"},
        {"text": "我家燃气费是不是欠费了", "expected_intent": "缴费查询", "desc": "状态查询"},
        {"text": "物业费逾期了怎么办", "expected_intent": "缴费查询", "desc": "问题咨询"},
        
        # 投诉建议场景测试
        {"text": "你们物业卫生打扫的也太差了吧", "expected_intent": "投诉建议", "desc": "投诉场景"},
        {"text": "建议小区增加几个健身器材", "expected_intent": "投诉建议", "desc": "建议场景"},
        {"text": "保安态度太差了，能不能管管", "expected_intent": "投诉建议", "desc": "投诉场景"},
        {"text": "希望小区电梯能定期检修", "expected_intent": "投诉建议", "desc": "建议场景"}
    ]
    
    passed_count = 0
    total_count = len(test_cases)
    
    print("\n🚀 开始测试意图识别（融合BM25后）：")
    for i, test in enumerate(test_cases, 1):
        result = synapse_core.recognize_intent(test["text"])
        actual_intent = result["main_intent"] if result["main_intent"] else "未知意图"
        confidence = result["intent_confidence"]
        
        passed = actual_intent == test["expected_intent"]
        if passed:
            passed_count += 1
        
        print(f"\n用例{i}: {test['desc']}")
        print(f"输入: '{test['text']}'")
        print(f"预期: {test['expected_intent']}")
        print(f"实际: {actual_intent}")
        print(f"置信度: {confidence:.2f}")
        print(f"结果: {'✅ 通过' if passed else '❌ 失败'}")
        
        # 打印BM25单独得分作为参考
        if hasattr(intent_bm25, 'recognize_intent'):
            bm25_intent, bm25_score = intent_bm25.recognize_intent(test["text"], threshold=0)
            print(f"BM25单独识别: {bm25_intent}, 得分: {bm25_score:.2f}")
    
    print(f"\n🏆 测试结果：{passed_count}/{total_count} 通过")
    print(f"准确率: {passed_count/total_count*100:.2f}%")
    
    if passed_count == total_count:
        print("\n✅ BM25集成效果优秀！所有容错测试用例全部通过")
        print("✨ 核心提升：错别字、同义词、口语化表达全部正确识别")
    else:
        print(f"\n⚠️  有{total_count-passed_count}个用例失败，可通过补充语料优化")
    
    # 测试边界用例
    print("\n🔍 边界用例测试：")
    boundary_cases = [
        "我想租房子，同时看看明天天气",
        "我家灯坏了，顺便问问水费怎么交",
        "今天天气不错，适合看房"
    ]
    
    for text in boundary_cases:
        result = synapse_core.recognize_intent(text, enable_multi_intent=True)
        main_intent = result["main_intent"]
        sub_intent = result["sub_intent"]
        print(f"\n输入: '{text}'")
        print(f"主意图: {main_intent}, 次意图: {sub_intent if sub_intent else '无'}")
    
    return passed_count == total_count

if __name__ == "__main__":
    test_bm25_integration()