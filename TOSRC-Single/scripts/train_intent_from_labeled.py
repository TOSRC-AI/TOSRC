#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于标注数据训练意图分类模型
"""
import os
import sys
import json
from collections import defaultdict
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import get_logger
from src.config.loader import get_global_config

logger = get_logger()

def train_intent_model(json_path: str, output_path: str = "data/models/intent_keywords.json"):
    """从标注数据训练意图关键词模型"""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 统计每个意图的关键词
        intent_keywords = defaultdict(lambda: defaultdict(int))
        intent_name_map = {}
        
        for item in data:
            top_intent = item["top_intent"]
            second_intent = item["second_intent"]
            text = item["user_text"]
            
            # 提取关键词（2-3元组）
            keywords = []
            n = len(text)
            for i in range(n):
                if i + 1 < n and text[i].isspace() == False and text[i+1].isspace() == False:
                    keywords.append(text[i:i+2])
                if i + 2 < n and text[i].isspace() == False and text[i+1].isspace() == False and text[i+2].isspace() == False:
                    keywords.append(text[i:i+3])
            
            # 统计关键词频率
            for kw in keywords:
                intent_keywords[top_intent][kw] += 1
                intent_keywords[second_intent][kw] += 1
            
            # 保存意图名称映射
            intent_name_map[top_intent] = top_intent
            intent_name_map[second_intent] = second_intent
        
        # 过滤低频关键词，只保留出现>=2次的
        result = {}
        for intent, kw_counts in intent_keywords.items():
            result[intent] = {
                "keywords": [kw for kw, count in kw_counts.items() if count >= 2],
                "name": intent_name_map.get(intent, intent)
            }
        
        # 保存模型
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 意图分类模型训练完成，支持{len(result)}个意图，保存到: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"训练意图模型失败: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    json_path = "/Volumes/1T/ai_project/ai-llm-router/data/租房行业/租房数据标注99.json"
    train_intent_model(json_path)