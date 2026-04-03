#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标注对话数据转BIO格式数据集工具
将JSON格式的标注对话转换为NER训练用的BIO格式
"""
import os
import sys
import json
import re
from typing import List, Dict, Any
from pathlib import Path

# 添加上层目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.logger import get_logger

logger = get_logger()

class BioDatasetConverter:
    """标注数据转BIO格式转换器"""
    
    def __init__(self):
        # BIO标签前缀
        self.B_PREFIX = "B-"
        self.I_PREFIX = "I-"
        self.O_TAG = "O"
    
    def convert_json_to_bio(self, json_path: str, output_dir: str = "data/ner_dataset") -> bool:
        """
        将JSON标注对话转换为BIO格式数据集
        :param json_path: 输入JSON标注文件路径
        :param output_dir: 输出目录
        :return: 转换是否成功
        """
        try:
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            
            # 读取标注数据
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            conversations = data.get("data", [])
            logger.info(f"开始转换标注数据，共{len(conversations)}条对话")
            
            bio_samples = []
            entity_type_set = set()
            
            for conv in conversations:
                text = conv["text"]
                entities = conv.get("entities", [])
                
                # 转换为BIO格式
                bio_tags, entity_types = self._text_to_bio(text, entities)
                bio_samples.append({
                    "text": text,
                    "bio_tags": bio_tags,
                    "entities": entities
                })
                entity_type_set.update(entity_types)
            
            # 保存训练集、验证集、测试集（按8:1:1划分）
            total = len(bio_samples)
            train_size = int(total * 0.8)
            val_size = int(total * 0.1)
            
            train_samples = bio_samples[:train_size]
            val_samples = bio_samples[train_size:train_size+val_size]
            test_samples = bio_samples[train_size+val_size:]
            
            # 保存为标准BIO格式文件
            self._save_bio_file(train_samples, os.path.join(output_dir, "train.txt"))
            self._save_bio_file(val_samples, os.path.join(output_dir, "dev.txt"))
            self._save_bio_file(test_samples, os.path.join(output_dir, "test.txt"))
            
            # 保存实体类型
            with open(os.path.join(output_dir, "entity_types.txt"), "w", encoding="utf-8") as f:
                for et in sorted(entity_type_set):
                    f.write(f"{et}\n")
            
            logger.info(f"✅ BIO数据集转换完成！")
            logger.info(f"训练集: {len(train_samples)}条，验证集: {len(val_samples)}条，测试集: {len(test_samples)}条")
            logger.info(f"支持实体类型: {len(entity_type_set)}类，已保存到entity_types.txt")
            logger.info(f"数据集目录: {output_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"转换BIO数据集失败: {str(e)}", exc_info=True)
            return False
    
    def _text_to_bio(self, text: str, entities: List[Dict[str, Any]]) -> tuple[List[str], List[str]]:
        """
        将单条文本和实体标注转换为BIO标签序列
        :param text: 原始文本
        :param entities: 标注实体列表，每个包含type和value字段
        :return: (BIO标签列表, 实体类型列表)
        """
        # 初始化标签为O
        tags = [self.O_TAG] * len(text)
        entity_types = []
        
        # 按实体长度降序排序，避免长实体被短实体覆盖
        sorted_entities = sorted(entities, key=lambda x: len(x["value"]), reverse=True)
        
        for entity in sorted_entities:
            entity_type = entity["type"]
            entity_value = entity["value"]
            entity_types.append(entity_type)
            
            # 查找实体在文本中的所有出现位置
            start_idx = 0
            while True:
                idx = text.find(entity_value, start_idx)
                if idx == -1:
                    break
                
                # 检查是否已经被标注过（避免冲突）
                if tags[idx] == self.O_TAG:
                    # 标注B-开头
                    tags[idx] = f"{self.B_PREFIX}{entity_type}"
                    # 标注I-开头
                    for i in range(idx + 1, idx + len(entity_value)):
                        if i < len(tags):
                            tags[i] = f"{self.I_PREFIX}{entity_type}"
                
                start_idx = idx + 1
        
        return tags, entity_types
    
    def _save_bio_file(self, samples: List[Dict[str, Any]], output_path: str) -> None:
        """保存BIO格式文件"""
        with open(output_path, "w", encoding="utf-8") as f:
            for sample in samples:
                text = sample["text"]
                tags = sample["bio_tags"]
                
                # 每个字和标签占一行，句子之间空行分隔
                for char, tag in zip(text, tags):
                    if char.strip():  # 跳过空字符
                        f.write(f"{char}\t{tag}\n")
                f.write("\n")  # 句子结束空行

def main():
    converter = BioDatasetConverter()
    input_path = "/Volumes/1T/ai_project/ai-llm-router/TOSRC-Single/data/db/rent_conversation_labeled.json"
    output_dir = "/Volumes/1T/ai_project/ai-llm-router/TOSRC-Single/data/ner_dataset"
    converter.convert_json_to_bio(input_path, output_dir)

if __name__ == "__main__":
    main()