#!/usr/bin/env python3
"""
简单测试BM25功能
"""
import sys
sys.path.append('.')
import jieba
jieba.setLogLevel(jieba.logging.INFO)  # 关闭jieba日志

from src.bm25_utils import IntentBM25
from src.db.sqlite_manager import sqlite_manager

print("测试BM25模块...")

# 测试分词
text = "我想租个两室一厅，预算3000左右"
words = jieba.lcut(text)
print(f"分词结果: {words}")

# 测试插入语料
print("\n插入测试语料...")
sqlite_manager.insert_corpus("租房查询", "租房子", weight=2)
sqlite_manager.insert_corpus("租房查询", "预算多少钱", weight=2)
sqlite_manager.insert_corpus("天气查询", "明天天气怎么样", weight=2)

# 初始化BM25
bm25 = IntentBM25()
print("\nBM25初始化完成")

# 测试识别
test_texts = [
    "租个两室一厅",
    "明天上海天气",
    "热水器坏了"
]

for text in test_texts:
    intent, score = bm25.recognize_intent(text, threshold=0.1)
    print(f"\n输入: {text}")
    print(f"识别: {intent}, 得分: {score:.2f}")

print("\n✅ 基础功能正常")
