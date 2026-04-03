#!/usr/bin/env python3
"""
简化版BM25集成测试，优先验证核心功能
"""
import sys
sys.path.append('.')
import jieba
jieba.setLogLevel(jieba.logging.INFO)

# 第一步：测试BM25独立功能
print("=== 🚀 测试BM25独立功能 ===")
from src.bm25_utils import intent_bm25, IntentBM25
from src.db.sqlite_manager import sqlite_manager

# 先清理测试语料
sqlite_manager.execute_custom_sql("DELETE FROM intent_corpus", write=True)

# 插入测试语料
test_corpus = [
    {"intent_name": "租房查询", "corpus_text": "租房子", "weight": 2},
    {"intent_name": "租房查询", "corpus_text": "两室一厅", "weight": 2},
    {"intent_name": "租房查询", "corpus_text": "预算多少钱", "weight": 2},
    {"intent_name": "租房查询", "corpus_text": "找房子", "weight": 2},
    {"intent_name": "房源报修", "corpus_text": "坏了", "weight": 2},
    {"intent_name": "房源报修", "corpus_text": "修一下", "weight": 2},
    {"intent_name": "房源报修", "corpus_text": "热水器坏了", "weight": 2},
    {"intent_name": "天气查询", "corpus_text": "天气怎么样", "weight": 2},
    {"intent_name": "天气查询", "corpus_text": "下雨吗", "weight": 2},
    {"intent_name": "缴费查询", "corpus_text": "交电费", "weight": 2},
    {"intent_name": "缴费查询", "corpus_text": "多少钱", "weight": 2},
    {"intent_name": "投诉建议", "corpus_text": "投诉", "weight": 2},
    {"intent_name": "投诉建议", "corpus_text": "建议", "weight": 2},
]

for corpus in test_corpus:
    sqlite_manager.insert_corpus(**corpus)

# 重新初始化BM25模型
intent_bm25._init_model()
print("✅ 语料初始化完成，共加载", len(test_corpus), "条语料")

# 测试BM25单独识别
print("\n=== 🧪 测试BM25单独识别 ===")
test_texts = [
    ("组个两室一厅，预算3千", "租房查询"),
    ("我家热水器坏了，帮忙修下", "房源报修"),
    ("明天会下雨吗", "天气查询"),
    ("这个月电费多少钱", "缴费查询"),
    ("投诉你们服务太差", "投诉建议")
]

passed = 0
for text, expected in test_texts:
    intent, score = intent_bm25.recognize_intent(text, threshold=0.1)
    ok = intent == expected
    if ok:
        passed +=1
    print(f"输入: '{text}'")
    print(f"预期: {expected}, 实际: {intent}, 得分: {score:.2f}, 结果: {'✅' if ok else '❌'}")

print(f"\n🏆 BM25独立测试结果: {passed}/{len(test_texts)} 通过, 准确率: {passed/len(test_texts)*100:.2f}%")

# 第二步：测试集成到仿生核心
print("\n=== 🤖 测试BM25仿生核心集成 ===")
from src.bionic.neuron_core import synapse_core

# 插入测试意图神经元
from src.bionic.db import bionic_db
bionic_db.add_intent_neuron("default", "租房查询", "租房查询", base_priority=5)
bionic_db.add_intent_neuron("default", "房源报修", "房源报修", base_priority=5)
bionic_db.add_intent_neuron("default", "天气查询", "天气查询", base_priority=5)
bionic_db.add_intent_neuron("default", "缴费查询", "缴费查询", base_priority=5)
bionic_db.add_intent_neuron("default", "投诉建议", "投诉建议", base_priority=5)

# 重新加载神经元
synapse_core.load_intent_neurons()

passed_integrated = 0
for text, expected in test_texts:
    result = synapse_core.recognize_intent(text)
    actual_intent = result["main_intent"]
    confidence = result["intent_confidence"]
    ok = actual_intent == expected
    if ok:
        passed_integrated +=1
    print(f"输入: '{text}'")
    print(f"预期: {expected}, 实际: {actual_intent}, 置信度: {confidence:.2f}, 结果: {'✅' if ok else '❌'}")

print(f"\n🏆 集成测试结果: {passed_integrated}/{len(test_texts)} 通过, 准确率: {passed_integrated/len(test_texts)*100:.2f}%")

if passed == len(test_texts) and passed_integrated == len(test_texts):
    print("\n✅ 所有测试通过！BM25功能正常，集成成功！")
else:
    print("\n⚠️  部分测试失败，可补充更多语料优化")

# 清理测试数据
sqlite_manager.execute_custom_sql("DELETE FROM intent_corpus", write=True)
print("\n🧹 测试数据清理完成")
