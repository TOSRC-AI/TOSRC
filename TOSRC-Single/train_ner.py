#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量小样本NER训练器（独立版本）
适配租房小数据集，基于规则+词典+正则实现，无需大模型，训练速度快，适合离线场景
"""
import os
import json
import re
from typing import List, Dict, Any, Tuple
from collections import defaultdict

class LightNERTrainer:
    """轻量NER训练器，小样本快速训练"""
    
    def __init__(self):
        self.entity_dict = defaultdict(list)  # 实体词典：{实体类型: [实体值列表]}
        self.pattern_dict = {}  # 正则模式：{实体类型: 正则表达式}
        self.entity_weights = {}  # 实体权重
        self.is_trained = False
    
    def train_from_bio(self, dataset_dir: str, output_model_path: str = "data/models/ner_light") -> bool:
        """
        从BIO数据集训练
        :param dataset_dir: BIO数据集目录
        :param output_model_path: 模型输出路径
        :return: 训练是否成功
        """
        try:
            os.makedirs(output_model_path, exist_ok=True)
            
            # 1. 加载所有BIO数据
            train_file = os.path.join(dataset_dir, "train.txt")
            dev_file = os.path.join(dataset_dir, "dev.txt")
            test_file = os.path.join(dataset_dir, "test.txt")
            
            train_samples = self._load_bio_file(train_file)
            # 没有验证集的话用测试集代替
            if os.path.exists(dev_file):
                dev_samples = self._load_bio_file(dev_file)
            else:
                dev_samples = self._load_bio_file(test_file)
            
            print(f"加载训练样本: {len(train_samples)}条，验证样本: {len(dev_samples)}条")
            
            # 2. 构建实体词典
            self._build_entity_dictionary(train_samples + dev_samples)
            
            # 3. 构建正则匹配模式
            self._build_patterns()
            
            # 4. 保存模型
            self._save_model(output_model_path)
            
            # 5. 评估效果
            accuracy = self._evaluate(dev_samples)
            print(f"✅ 模型训练完成，验证集准确率: {accuracy:.2f}%")
            
            self.is_trained = True
            return True
            
        except Exception as e:
            print(f"训练NER模型失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_bio_file(self, file_path: str) -> List[Tuple[List[str], List[str]]]:
        """加载BIO格式文件"""
        samples = []
        chars = []
        tags = []
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    if chars and tags:
                        samples.append((chars, tags))
                        chars = []
                        tags = []
                    continue
                
                parts = line.split("\t")
                if len(parts) == 2:
                    chars.append(parts[0])
                    tags.append(parts[1])
        
        if chars and tags:
            samples.append((chars, tags))
        
        return samples
    
    def _build_entity_dictionary(self, samples: List[Tuple[List[str], List[str]]]) -> None:
        """从标注数据构建实体词典"""
        entity_map = defaultdict(set)
        
        for chars, tags in samples:
            current_entity = []
            current_type = None
            
            for char, tag in zip(chars, tags):
                if tag.startswith("B-"):
                    if current_entity and current_type:
                        entity_value = "".join(current_entity)
                        entity_map[current_type].add(entity_value)
                    current_entity = [char]
                    current_type = tag[2:]
                elif tag.startswith("I-") and current_type == tag[2:]:
                    current_entity.append(char)
                else:
                    if current_entity and current_type:
                        entity_value = "".join(current_entity)
                        entity_map[current_type].add(entity_value)
                    current_entity = []
                    current_type = None
            
            # 处理句子末尾的实体
            if current_entity and current_type:
                entity_value = "".join(current_entity)
                entity_map[current_type].add(entity_value)
        
        # 转换为列表
        for et, values in entity_map.items():
            self.entity_dict[et] = list(values)
            print(f"实体类型[{et}]：{len(values)}个实体值")
    
    def _build_patterns(self) -> None:
        """构建正则匹配模式"""
        # 价格模式
        self.pattern_dict["price"] = re.compile(r'([0-9]+[kK万wW元块钱]|([0-9]+[-~至到][0-9]+[kK万wW元块]?))')
        # 时间模式（支持完整时间短语，优先匹配长的）
        self.pattern_dict["time"] = re.compile(r'((今天|明天|后天|本周|下周|本月|下月|这[周月天])[早晚上下]?[午晚]?\s*([0-9]+[:点][0-9]+分?)?|[0-9]+[号日]|[0-9一二三四五六七八九十]+个?月|上午|下午|晚上|早上)')
        # 手机号模式
        self.pattern_dict["phone"] = re.compile(r'1[3-9]\d{9}')
        # 数字模式
        self.pattern_dict["number"] = re.compile(r'\d+')
    
    def _save_model(self, output_path: str) -> None:
        """保存模型到文件"""
        model_data = {
            "entity_dict": dict(self.entity_dict),
            "pattern_dict": {k: v.pattern for k, v in self.pattern_dict.items()},
            "entity_weights": self.entity_weights
        }
        
        with open(os.path.join(output_path, "ner_model.json"), "w", encoding="utf-8") as f:
            json.dump(model_data, f, ensure_ascii=False, indent=2)
        
        print(f"模型已保存到: {output_path}/ner_model.json")
    
    def load_model(self, model_path: str) -> bool:
        """加载模型"""
        try:
            model_file = os.path.join(model_path, "ner_model.json")
            if not os.path.exists(model_file):
                print(f"模型文件不存在: {model_file}")
                return False
            
            with open(model_file, "r", encoding="utf-8") as f:
                model_data = json.load(f)
            
            self.entity_dict = model_data.get("entity_dict", {})
            self.pattern_dict = {k: re.compile(v) for k, v in model_data.get("pattern_dict", {}).items()}
            self.entity_weights = model_data.get("entity_weights", {})
            
            self.is_trained = True
            print(f"NER模型加载成功，包含{len(self.entity_dict)}类实体")
            return True
            
        except Exception as e:
            print(f"加载NER模型失败: {str(e)}")
            return False
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """提取实体"""
        if not self.is_trained:
            return []
        
        entities = []
        seen_spans = set()  # 避免重叠实体
        
        # 1. 词典匹配
        for entity_type, values in self.entity_dict.items():
            for val in values:
                start_idx = 0
                while True:
                    idx = text.find(val, start_idx)
                    if idx == -1:
                        break
                    end_idx = idx + len(val)
                    # 检查是否重叠
                    overlap = False
                    for (s, e) in seen_spans:
                        if not (end_idx <= s or idx >= e):
                            overlap = True
                            break
                    if not overlap:
                        entities.append({
                            "type": entity_type,
                            "value": val,
                            "start": idx,
                            "end": end_idx,
                            "confidence": 0.95,
                            "source": "dict"
                        })
                        seen_spans.add((idx, end_idx))
                    start_idx = idx + 1
        
        # 2. 正则匹配
        for entity_type, pattern in self.pattern_dict.items():
            for match in pattern.finditer(text):
                idx = match.start()
                end_idx = match.end()
                val = match.group()
                # 检查是否重叠
                overlap = False
                for (s, e) in seen_spans:
                    if not (end_idx <= s or idx >= e):
                        overlap = True
                        break
                if not overlap:
                    entities.append({
                        "type": entity_type,
                        "value": val,
                        "start": idx,
                        "end": end_idx,
                        "confidence": 0.85,
                        "source": "pattern"
                    })
                    seen_spans.add((idx, end_idx))
        
        # 按起始位置排序
        entities.sort(key=lambda x: x["start"])
        return entities
    
    def _evaluate(self, dev_samples: List[Tuple[List[str], List[str]]]) -> float:
        """评估模型准确率"""
        total = 0
        correct = 0
        
        for chars, tags in dev_samples:
            text = "".join(chars)
            pred_entities = self.extract_entities(text)
            
            # 构建真实实体集合
            true_entities = set()
            current_entity = []
            current_type = None
            for char, tag in zip(chars, tags):
                if tag.startswith("B-"):
                    if current_entity and current_type:
                        entity_value = "".join(current_entity)
                        true_entities.add((current_type, entity_value))
                    current_entity = [char]
                    current_type = tag[2:]
                elif tag.startswith("I-") and current_type == tag[2:]:
                    current_entity.append(char)
                else:
                    if current_entity and current_type:
                        entity_value = "".join(current_entity)
                        true_entities.add((current_type, entity_value))
                    current_entity = []
                    current_type = None
            if current_entity and current_type:
                entity_value = "".join(current_entity)
                true_entities.add((current_type, entity_value))
            
            # 构建预测实体集合
            pred_entities_set = set()
            for e in pred_entities:
                pred_entities_set.add((e["type"], e["value"]))
            
            # 统计
            total += len(true_entities)
            for te in true_entities:
                if te in pred_entities_set:
                    correct += 1
        
        accuracy = (correct / total * 100) if total > 0 else 0
        return accuracy

def main():
    trainer = LightNERTrainer()
    dataset_dir = "./data/ner_dataset_v2"
    model_path = "./data/models/ner_light_v2"
    
    # 训练
    trainer.train_from_bio(dataset_dir, model_path)
    
    # 测试
    test_texts = [
        "我想在北京租个两室一厅，月租3k左右，不超4000，明天下午看房",
        "有没有朝南主卧带独立卫浴，可以短租三个月吗",
        "这套房子还在出租吗，我想约明天下午看房"
    ]
    
    print("\n=== 测试识别效果 ===")
    for text in test_texts:
        entities = trainer.extract_entities(text)
        print(f"\n文本: {text}")
        print(f"识别实体: {len(entities)}个")
        for e in entities:
            print(f"  [{e['type']}] {e['value']} (置信度: {e['confidence']}, 来源: {e['source']})")

if __name__ == "__main__":
    main()