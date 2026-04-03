#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新标注格式转BIO数据集工具
支持rent_test_labeled.json格式：包含user_text、entities字典、irony反讽标注
"""
import os
import json
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path

class NewFormatBioConverter:
    """新标注格式转换器"""
    
    def __init__(self):
        self.B_PREFIX = "B-"
        self.I_PREFIX = "I-"
        self.O_TAG = "O"
    
    def convert(self, input_json: str, output_dir: str = "data/ner_dataset_v2") -> bool:
        """转换新格式标注数据为BIO"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # 读取新格式数据
            with open(input_json, "r", encoding="utf-8") as f:
                samples = json.load(f)
            
            logger.info(f"加载新格式标注数据: {len(samples)}条")
            
            bio_samples = []
            entity_type_set = set()
            
            for sample in samples:
                text = sample["user_text"]
                entities_dict = sample.get("entities", {})
                
                # 将字典格式的entities转换为列表格式
                entities = []
                for et, val in entities_dict.items():
                    # 处理多个值的情况（用顿号、逗号分隔）
                    vals = re.split(r'[、，,]', val)
                    for v in vals:
                        v = v.strip()
                        if v:
                            entities.append({
                                "type": et,
                                "value": v
                            })
                
                # 转换为BIO
                bio_tags, entity_types = self._text_to_bio(text, entities)
                bio_samples.append({
                    "text": text,
                    "bio_tags": bio_tags,
                    "entities": entities,
                    "irony": sample.get("irony", False)
                })
                entity_type_set.update(entity_types)
            
            # 按9:1划分训练集和测试集
            total = len(bio_samples)
            train_size = int(total * 0.9)
            train_samples = bio_samples[:train_size]
            test_samples = bio_samples[train_size:]
            
            # 保存
            self._save_bio_file(train_samples, os.path.join(output_dir, "train.txt"))
            self._save_bio_file(test_samples, os.path.join(output_dir, "test.txt"))
            
            # 保存实体类型
            with open(os.path.join(output_dir, "entity_types.txt"), "w", encoding="utf-8") as f:
                for et in sorted(entity_type_set):
                    f.write(f"{et}\n")
            
            logger.info(f"✅ 新数据集转换完成！")
            logger.info(f"训练集: {len(train_samples)}条，测试集: {len(test_samples)}条")
            logger.info(f"实体类型: {len(entity_type_set)}类")
            logger.info(f"输出目录: {output_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"转换失败: {str(e)}", exc_info=True)
            return False
    
    def _text_to_bio(self, text: str, entities: List[Dict[str, Any]]) -> tuple[List[str], List[str]]:
        """文本转BIO标签"""
        tags = [self.O_TAG] * len(text)
        entity_types = []
        
        # 按实体长度降序排序
        sorted_entities = sorted(entities, key=lambda x: len(x["value"]), reverse=True)
        
        for entity in sorted_entities:
            entity_type = entity["type"]
            entity_value = entity["value"]
            entity_types.append(entity_type)
            
            start_idx = 0
            while True:
                idx = text.find(entity_value, start_idx)
                if idx == -1:
                    break
                
                if tags[idx] == self.O_TAG:
                    tags[idx] = f"{self.B_PREFIX}{entity_type}"
                    for i in range(idx + 1, idx + len(entity_value)):
                        if i < len(tags):
                            tags[i] = f"{self.I_PREFIX}{entity_type}"
                
                start_idx = idx + 1
        
        return tags, entity_types
    
    def _save_bio_file(self, samples: List[Dict[str, Any]], output_path: str) -> None:
        """保存BIO文件"""
        with open(output_path, "w", encoding="utf-8") as f:
            for sample in samples:
                text = sample["text"]
                tags = sample["bio_tags"]
                for char, tag in zip(text, tags):
                    if char.strip():
                        f.write(f"{char}\t{tag}\n")
                f.write("\n")

def main():
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from src.utils.logger import get_logger
    global logger
    logger = get_logger()
    
    converter = NewFormatBioConverter()
    input_path = "/Volumes/1T/ai_project/ai-llm-router/TOSRC-Single/data/db/rent_test_labeled.json"
    output_dir = "/Volumes/1T/ai_project/ai-llm-router/TOSRC-Single/data/ner_dataset_v2"
    converter.convert(input_path, output_dir)

if __name__ == "__main__":
    main()