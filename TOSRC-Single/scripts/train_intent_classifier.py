#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
租房行业意图分类模型训练工具
基于标注对话数据训练轻量意图分类器，结合关键词匹配+TF-IDF+朴素贝叶斯，轻量高效，适合离线场景
"""
import os
import sys
import json
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
from collections import defaultdict

# 添加上层目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import get_logger
from src.config.loader import get_global_config
from src.adapter.dal.sqlite_dal import SQLiteDAL

logger = get_logger()

class IntentClassifierTrainer:
    """意图分类器训练器"""
    
    def __init__(self, industry_code: str = "rental"):
        self.industry_code = industry_code
        self.db = SQLiteDAL(get_global_config()["database"]["sqlite_path"])
        
        # 模型数据
        self.intent_keywords = defaultdict(list)  # 意图关键词：{intent_code: [关键词列表]}
        self.intent_priority = {}  # 意图优先级
        self.stop_words = {"的", "了", "吗", "呢", "啊", "吧", "我", "你", "他", "的", "是", "有", "在", "要", "想"}
    
    def train_from_labeled_data(self, json_path: str, output_model_path: str = "data/models/intent_classifier") -> bool:
        """从标注JSON数据训练模型"""
        try:
            # 读取标注数据
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            conversations = data  # 数据本身就是列表格式
            logger.info(f"加载标注对话数据: {len(conversations)}条")
            
            # 从数据库加载所有意图信息
            intent_info = self._load_intent_info()
            
            # 提取关键词
            for conv in conversations:
                text = conv["user_text"]
                intents = [conv.get("top_intent", "")]  # 使用top_intent作为主意图
                
                if not intents:
                    continue
                    
                # 取第一个意图作为主意图，顶层意图没有行业前缀
                main_intent = intents[0]
                intent_code = main_intent
                if intent_code not in intent_info:
                    continue
                
                # 提取关键词（去掉停用词，长度>=2）
                words = self._extract_keywords(text)
                self.intent_keywords[intent_code].extend(words)
            
            # 去重，每个意图保留高频关键词
            for intent_code, keywords in self.intent_keywords.items():
                # 统计词频
                word_count = defaultdict(int)
                for kw in keywords:
                    word_count[kw] += 1
                # 保留出现>=2次的关键词
                unique_kw = list(set([kw for kw in keywords if word_count[kw] >= 2]))
                self.intent_keywords[intent_code] = unique_kw
                logger.debug(f"意图[{intent_code}]提取关键词: {len(unique_kw)}个")
            
            # 保存模型
            self._save_model(output_model_path)
            logger.info(f"✅ 意图分类模型训练完成，支持{len(self.intent_keywords)}个意图分类")
            return True
            
        except Exception as e:
            logger.error(f"训练意图分类模型失败: {str(e)}", exc_info=True)
            return False
    
    def _load_intent_info(self) -> Dict[str, Any]:
        """加载所有意图信息"""
        try:
            result = self.db.execute_query("""
                SELECT intent_code, intent_name, priority 
                FROM intents 
                WHERE level = 1
            """)
            
            intent_map = {}
            for item in result:
                intent_map[item["intent_code"]] = item
                self.intent_priority[item["intent_code"]] = item["priority"]
            return intent_map
            
        except Exception as e:
            logger.error(f"加载意图信息失败: {str(e)}")
            return {}
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 只保留中文、数字、字母
        cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
        words = []
        # 简单分词（按单字+2-3元组）
        n = len(cleaned)
        for i in range(n):
            if cleaned[i] in self.stop_words or cleaned[i].isspace():
                continue
            # 单字
            # words.append(cleaned[i])
            # 2元组
            if i + 1 < n and not cleaned[i+1].isspace() and cleaned[i+1] not in self.stop_words:
                words.append(cleaned[i:i+2])
            # 3元组
            if i + 2 < n and not cleaned[i+1].isspace() and not cleaned[i+2].isspace() and cleaned[i+1] not in self.stop_words and cleaned[i+2] not in self.stop_words:
                words.append(cleaned[i:i+3])
        
        return words
    
    def _save_model(self, output_path: str) -> None:
        """保存模型到文件"""
        os.makedirs(output_path, exist_ok=True)
        
        model_data = {
            "intent_keywords": dict(self.intent_keywords),
            "intent_priority": self.intent_priority,
            "stop_words": list(self.stop_words)
        }
        
        with open(os.path.join(output_path, "intent_classifier.json"), "w", encoding="utf-8") as f:
            json.dump(model_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"模型已保存到: {output_path}/intent_classifier.json")
    
    def predict(self, text: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """预测文本的意图，返回前N个最匹配的"""
        if not self.intent_keywords:
            # 加载模型
            model_path = "data/models/intent_classifier/intent_classifier.json"
            if os.path.exists(model_path):
                with open(model_path, "r", encoding="utf-8") as f:
                    model_data = json.load(f)
                self.intent_keywords = model_data.get("intent_keywords", {})
                self.intent_priority = model_data.get("intent_priority", {})
            else:
                return []
        
        text_kw = set(self._extract_keywords(text))
        intent_scores = {}
        
        for intent_code, keywords in self.intent_keywords.items():
            if not keywords:
                continue
            # 计算匹配得分：匹配关键词数 / 总关键词数 + 优先级加成
            match_count = len([kw for kw in keywords if kw in text_kw])
            score = match_count / len(keywords) * 100
            # 优先级加成：优先级越高加成越多
            score += self.intent_priority.get(intent_code, 0) / 10
            intent_scores[intent_code] = score
        
        # 按得分降序排序
        sorted_intents = sorted(intent_scores.items(), key=lambda x: (-x[1], -self.intent_priority.get(x[0], 0)))
        
        # 返回前N个
        result = []
        for intent_code, score in sorted_intents[:top_n]:
            if score <= 0:
                continue
            result.append({
                "intent_code": intent_code,
                "confidence": round(score / 100, 2) if score > 0 else 0,
                "priority": self.intent_priority.get(intent_code, 0)
            })
        
        return result

def main():
    trainer = IntentClassifierTrainer(industry_code="rental")
    # 用你提供的标注数据训练
    data_path = "/Volumes/1T/ai_project/ai-llm-router/TOSRC-Single/data/db/rent_test_labeled.json"
    trainer.train_from_labeled_data(data_path)
    
    # 测试效果
    test_texts = [
        "我想租朝阳区望京小区的两室一厅，月租3000左右",
        "这套房子还在出租吗，我想预约明天下午看房",
        "空调坏了，能派人来修吗",
        "我要提前退租，押金能退多少",
        "续租一年的话租金会涨吗"
    ]
    
    logger.info("\n=== 意图分类测试 ===")
    for text in test_texts:
        predictions = trainer.predict(text, top_n=1)
        if predictions:
            pred = predictions[0]
            logger.info(f"文本: {text}")
            logger.info(f"预测意图: {pred['intent_code']}, 置信度: {pred['confidence']}, 优先级: {pred['priority']}")
        else:
            logger.info(f"文本: {text} -> 未识别到意图")

if __name__ == "__main__":
    main()