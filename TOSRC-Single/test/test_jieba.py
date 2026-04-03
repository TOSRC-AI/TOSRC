#!/usr/bin/env python3
import jieba
jieba.setLogLevel(jieba.logging.INFO)
print("测试jieba分词...")
text = "我想租个两室一厅"
words = jieba.lcut(text)
print(f"分词结果: {words}")
print("✅ jieba正常")
