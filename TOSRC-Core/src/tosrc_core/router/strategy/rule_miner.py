#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则挖掘模块：从LLM标注库中自动挖掘可复用规则，生成JSON规则包
完全兼容《外接LLM调教系统方案》中的规则包格式，支持实体规则、意图规则、情绪规则、否定规则自动挖掘
"""
import os
import json
import re
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict, Counter
from ...common.utils.logger import get_logger
from ...common.interface.dal import BaseDAL

logger = get_logger()

class RuleMiner:
    """规则挖掘核心类"""
    def __init__(self, dal: BaseDAL, annotation_dir: str = None):
        """
        初始化规则挖掘模块
        :param dal: 数据访问层实例，用于存储挖掘得到的规则
        :param annotation_dir: 标注数据目录，由适配层传入
        """
        self.dal = dal
        self.annotation_dir = annotation_dir
        # 规则输出目录由适配层配置
        self.rule_output_dir = os.path.join(annotation_dir, "..", "rules", "pending") if annotation_dir else "./data/rules/pending"
        os.makedirs(self.rule_output_dir, exist_ok=True)
    
    def _load_scene_annotations(self, scene: str) -> List[Dict[str, Any]]:
        """加载指定场景的所有标注数据"""
        scene_dir = os.path.join(self.annotation_dir, scene)
        if not os.path.exists(scene_dir):
            logger.warning(f"场景{scene}没有标注数据")
            return []
        
        annotations = []
        for file_name in os.listdir(scene_dir):
            if file_name.endswith(".json"):
                file_path = os.path.join(scene_dir, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        annotation = json.load(f)
                        annotations.append(annotation)
                except Exception as e:
                    logger.error(f"标注文件加载失败: {file_path}, 错误: {str(e)}")
        
        logger.info(f"加载场景{scene}标注数据: {len(annotations)}条")
        return annotations
    
    def _mine_entity_rules(self, annotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """挖掘实体规则（正则模板）"""
        entity_patterns = defaultdict(Counter)
        
        for ann in annotations:
            text = ann["text"]
            for entity in ann.get("entities", []):
                entity_type = entity.get("entity", "")
                value = entity.get("value", "")
                unit = entity.get("unit", "")
                start = entity.get("start", 0)
                end = entity.get("end", 0)
                
                if not entity_type or start >= end:
                    continue
                
                # 提取实体前后的特征词
                prefix = text[max(0, start - 5):start].strip()
                suffix = text[end:min(len(text), end + 3)].strip()
                
                # 生成正则模板
                pattern_parts = []
                if prefix:
                    # 前缀保留关键字，替换特殊字符
                    prefix_re = re.escape(prefix)
                    pattern_parts.append(f"({prefix_re})")
                
                # 数值部分根据实体类型生成匹配规则
                if entity.get("type") == "range":
                    pattern_parts.append(r"(\\d+(?:\\.\\d+)?)\\s*[-~～到至]\\s*(\\d+(?:\\.\\d+)?)")
                elif entity.get("type") == "approx":
                    pattern_parts.append(r"约?\\s*(\\d+(?:\\.\\d+)?)\\s*[左右大概约]?")
                else:
                    pattern_parts.append(r"(\\d+(?:\\.\\d+)?)")
                
                if unit:
                    pattern_parts.append(f"({re.escape(unit)})")
                
                pattern = "".join(pattern_parts)
                
                # 去重，相同模式只保留一个
                entity_patterns[entity_type][pattern] += 1
        
        # 转换为规则格式
        entity_rules = []
        for entity_type, patterns in entity_patterns.items():
            # 按出现频率排序，取频率最高的前10个模式
            for pattern, count in patterns.most_common(10):
                entity_rules.append({
                    "name": f"{entity_type}_{len(entity_rules)}",
                    "pattern": pattern,
                    "groups": ["prefix", "value", "unit"],
                    "entity_type": entity_type,
                    "type": "normal",
                    "priority": 2,
                    "count": count
                })
        
        logger.info(f"挖掘实体规则: {len(entity_rules)}条")
        return entity_rules
    
    def _mine_intent_rules(self, annotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """挖掘意图规则（关键词+句式模板）"""
        intent_keywords = defaultdict(Counter)
        intent_patterns = defaultdict(Counter)
        
        for ann in annotations:
            text = ann["text"]
            intent_name = ann.get("intent", {}).get("name", "")
            if not intent_name:
                continue
            
            # 提取关键词：将文本拆分为词语，统计高频词
            words = list(text)  # 简单按字符拆分，后续可集成分词
            for word in words:
                if len(word) >= 1 and '\u4e00' <= word <= '\u9fff':
                    intent_keywords[intent_name][word] += 1
            
            # 生成句式模板：将实体替换为占位符
            entities = sorted(ann.get("entities", []), key=lambda x: -x.get("start", 0))
            template = text
            for entity in entities:
                start = entity.get("start", 0)
                end = entity.get("end", 0)
                if start < end:
                    template = template[:start] + "[ENTITY]" + template[end:]
            intent_patterns[intent_name][template] += 1
        
        # 转换为规则格式
        intent_rules = []
        for intent_name, keywords in intent_keywords.items():
            # 取高频关键词Top10
            top_keywords = [k for k, v in keywords.most_common(10) if v >= 2]
            if not top_keywords:
                continue
            
            # 生成正则模式
            pattern = ".*(" + "|".join(re.escape(k) for k in top_keywords) + ").*"
            
            intent_rules.append({
                "intent": intent_name,
                "keywords": top_keywords,
                "pattern": pattern,
                "confidence": 0.9,
                "priority": 3
            })
        
        logger.info(f"挖掘意图规则: {len(intent_rules)}条")
        return intent_rules
    
    def _mine_emotion_rules(self, annotations: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """挖掘情绪规则（情绪词典）"""
        emotion_words = {
            "positive_words": set(),
            "negative_words": set(),
            "urgent_words": set(),
            "calm_words": set()
        }
        
        for ann in annotations:
            text = ann["text"]
            emotion_type = ann.get("emotion", {}).get("type", "")
            sentiment = ann.get("emotion", {}).get("sentiment", "")
            
            # 简单提取情绪关键词（后续可优化为TF-IDF）
            if sentiment == "positive":
                for word in text:
                    if len(word) >= 1 and '\u4e00' <= word <= '\u9fff':
                        emotion_words["positive_words"].add(word)
            elif sentiment == "negative":
                for word in text:
                    if len(word) >= 1 and '\u4e00' <= word <= '\u9fff':
                        emotion_words["negative_words"].add(word)
            
            if emotion_type == "urgent":
                for word in text:
                    if len(word) >= 1 and '\u4e00' <= word <= '\u9fff':
                        emotion_words["urgent_words"].add(word)
            elif emotion_type == "calm":
                for word in text:
                    if len(word) >= 1 and '\u4e00' <= word <= '\u9fff':
                        emotion_words["calm_words"].add(word)
        
        # 转换为列表，取高频词
        for key in emotion_words:
            emotion_words[key] = list(emotion_words[key])[:20]  # 保留前20个高频词
        
        logger.info(f"挖掘情绪规则: 正向{len(emotion_words['positive_words'])}个, 负向{len(emotion_words['negative_words'])}个")
        return emotion_words
    
    def _mine_negative_rules(self, annotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """挖掘否定规则"""
        negative_patterns = Counter()
        
        for ann in annotations:
            if ann.get("intent", {}).get("is_negated", False):
                text = ann["text"]
                # 匹配否定句式
                neg_match = re.search(r"(不|没|无|非|不要|不是|没有)[^\uff0c\u3002\uff01\uff1f]{1,5}", text)
                if neg_match:
                    pattern = re.escape(neg_match.group()) + ".*"
                    negative_patterns[pattern] += 1
        
        # 转换为规则格式
        negative_rules = []
        for pattern, count in negative_patterns.most_common(10):
            negative_rules.append({
                "pattern": pattern,
                "is_negated": True,
                "priority": 1,
                "count": count
            })
        
        logger.info(f"挖掘否定规则: {len(negative_rules)}条")
        return negative_rules
    
    def generate_rule_package(self, scene: str, scene_name: str = "") -> Optional[Dict[str, Any]]:
        """
        从标注数据生成完整规则包
        Args:
            scene: 场景编码
            scene_name: 场景名称
        Returns:
            完整规则包，可直接保存为JSON文件
        """
        annotations = self._load_scene_annotations(scene)
        if not annotations:
            return None
        
        # 挖掘各类规则
        entity_rules = self._mine_entity_rules(annotations)
        intent_rules = self._mine_intent_rules(annotations)
        emotion_rules = self._mine_emotion_rules(annotations)
        negative_rules = self._mine_negative_rules(annotations)
        
        # 构造规则包
        rule_package = {
            "scene": scene,
            "scene_name": scene_name or scene,
            "entity_rules": entity_rules,
            "intent_rules": intent_rules,
            "emotion_rules": emotion_rules,
            "negative_rules": negative_rules,
            "priority": [1, 2, 3, 4],
            "generate_time": int(os.times()[4]),
            "annotation_count": len(annotations)
        }
        
        # 保存到待审核目录
        output_path = os.path.join(self.rule_output_dir, f"{scene}_rules_pending.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(rule_package, f, ensure_ascii=False, indent=2)
        
        logger.info(f"规则包生成成功: {output_path}")
        return rule_package
    
    def get_pending_rules(self, scene: str = None) -> List[str]:
        """获取待审核的规则包列表"""
        pending_files = []
        for file_name in os.listdir(self.rule_output_dir):
            if file_name.endswith("_pending.json"):
                if scene is None or file_name.startswith(f"{scene}_"):
                    pending_files.append(file_name)
        return pending_files
    
    def approve_rule_package(self, scene: str) -> bool:
        """审核通过规则包，移动到正式规则目录"""
        pending_path = os.path.join(self.rule_output_dir, f"{scene}_rules_pending.json")
        if not os.path.exists(pending_path):
            logger.error(f"待审核规则包不存在: {pending_path}")
            return False
        
        try:
            # 移动到正式规则目录
            formal_path = os.path.join(
                os.path.dirname(self.rule_output_dir),
                f"{scene}_rules.json"
            )
            import shutil
            shutil.move(pending_path, formal_path)
            logger.info(f"规则包审核通过，已更新到正式目录: {formal_path}")
            return True
        except Exception as e:
            logger.error(f"规则包审核失败: {str(e)}")
            return False

# 全局单例
