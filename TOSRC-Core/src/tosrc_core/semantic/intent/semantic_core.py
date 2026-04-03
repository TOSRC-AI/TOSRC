#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局语义理解核心模块
实现人类理解逻辑：全局语义重心+语义关联度，完全纯算法无大模型
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Any
from ...common.utils.logger import get_logger
from .db import bionic_db

logger = get_logger()

# 无意义助词列表（自动忽略，权重为0）
STOP_WORDS = {"的", "了", "吗", "呢", "啊", "吧", "呀", "哦", "嗯", "有没有", "是不是", "会不会", "能不能",
             "我想", "请问", "麻烦", "一下", "帮我", "请", "你好", "您好", "在吗"}

# 语义关联度知识图谱（初始内置，可通过自动学习扩展）
# 注意：实际使用时优先从数据库加载自定义关联
DEFAULT_SEMANTIC_RELATION = {
    "租房查询": {
        "预算": 3.0, "价格": 3.0, "租金": 3.0, "价位": 2.8,
        "房型": 2.5, "一室一厅": 2.5, "两室一厅": 2.5, "loft": 2.5, "公寓": 2.5,
        "整租": 2.2, "合租": 2.2, "出租": 2.2, "求租": 2.2,
        "地铁": 2.0, "近地铁": 2.0, "地铁口": 2.0,
        "配套": 1.8, "拎包入住": 1.8, "精装修": 1.8,
        "今天": 0.5, "明天": 0.5, "现在": 0.5,
        "吃": 0.0, "喝": 0.0, "玩": 0.0
    },
    "天气查询": {
        "天气": 3.0, "温度": 3.0, "气温": 3.0, "雾霾": 3.0, "雨": 2.8, "雪": 2.8, "晴": 2.8,
        "空气质量": 2.5, "污染": 2.5, "pm2.5": 2.5,
        "今天": 2.0, "明天": 2.0, "后天": 2.0, "下周": 1.8,
        "北京": 1.5, "上海": 1.5, "广州": 1.5, "深圳": 1.5,
        "预算": 0.1, "租房": 0.1, "价格": 0.1,
        "吃": 0.0, "喝": 0.0, "玩": 0.0
    },
    "天气预警查询": {
        "预警": 3.5, "暴雨预警": 3.5, "高温预警": 3.5, "大风预警": 3.5,
        "天气": 2.0, "雨": 2.0, "雪": 2.0,
        "今天": 1.5, "明天": 1.5,
        "预算": 0.1, "租房": 0.1,
        "吃": 0.0, "喝": 0.0, "玩": 0.0
    },
    "房源报修": {
        "坏了": 3.0, "故障": 3.0, "维修": 3.0, "修一下": 3.0,
        "热水器": 2.5, "油烟机": 2.5, "空调": 2.5, "冰箱": 2.5,
        "漏水": 2.5, "漏电": 2.5, "堵了": 2.5, "不加热": 2.5,
        "厨房": 2.0, "卫生间": 2.0, "客厅": 2.0,
        "今天": 0.5, "明天": 0.5,
        "天气": 0.1, "预算": 0.1,
        "吃": 0.0, "喝": 0.0, "玩": 0.0
    },
    "房价咨询": {
        "吃": 0.0, "喝": 0.0, "玩": 0.0
    },
    "户型咨询": {
        "吃": 0.0, "喝": 0.0, "玩": 0.0
    }
}

def is_stop_word(word: str) -> bool:
    """判断是否是无意义助词"""
    return word in STOP_WORDS or len(word.strip()) == 0

def calculate_semantic_weight(word: str, position: int, total_length: int) -> float:
    """
    计算语义重心权重：
    - 无意义助词：权重0
    - 句子后半部分：权重×1.5
    - 句子前半部分：权重×1.0
    """
    if is_stop_word(word):
        return 0.0
    
    # 后半部分权重更高（核心语义通常在后面）
    if position > total_length * 0.5:
        return 1.5
    return 1.0

def get_semantic_relation(intent_id: str, word: str) -> float:
    """获取词和意图的语义关联度权重（集成向量语义层）
    1. 优先使用硬编码的关联度
    2. 没有匹配时使用向量语义匹配，查找语义相似的词
    3. 返回最高的关联度值
    """
    # 先查找精确匹配
    base_weight = SEMANTIC_RELATION.get(intent_id, {}).get(word, 0.0)
    if base_weight > 0:
        return base_weight
    
    # 字符串相似度匹配：找拼写相似的词，计算最高关联度
    from difflib import SequenceMatcher
    
    max_weight = 0.0
    intent_relations = SEMANTIC_RELATION.get(intent_id, {})
    for relation_word in intent_relations.keys():
        if relation_word == word:
            continue
        sim_score = SequenceMatcher(None, word, relation_word).ratio()
        if sim_score >= 0.7:  # 相似度阈值，可调整
            weighted_weight = intent_relations[relation_word] * sim_score
            if weighted_weight > max_weight:
                max_weight = weighted_weight
    
    if max_weight > 0:
        return max_weight
    
    # 没有找到任何关联，返回默认值1.0
    return 1.0

# 运行时语义关联关系，合并默认值和数据库自定义值
SEMANTIC_RELATION = {}

def _load_semantic_relations() -> None:
    """从数据库加载语义关联关系，合并默认配置"""
    global SEMANTIC_RELATION
    
    # 先加载默认配置
    SEMANTIC_RELATION = DEFAULT_SEMANTIC_RELATION.copy()
    
    # 从数据库加载自定义关联
    try:
        # 获取所有意图神经元
        intent_neurons = bionic_db.get_all_intent_neurons()
        for neuron in intent_neurons:
            intent_id = neuron["intent_id"]
            if intent_id not in SEMANTIC_RELATION:
                SEMANTIC_RELATION[intent_id] = {}
            
            # 加载数据库中的突触权重
            db_weights = bionic_db.get_synapse_weights_by_intent(intent_id)
            SEMANTIC_RELATION[intent_id].update(db_weights)
        
        logger.info("语义关联知识图谱加载完成")
        
    except Exception as e:
        logger.error(f"加载语义关联失败: {str(e)}，使用默认配置")

def update_semantic_relation(intent_id: str, word: str, weight: float, user_id: str = "global") -> None:
    """更新语义关联度（用于自主学习）
    同时更新内存和数据库，持久化存储
    """
    global SEMANTIC_RELATION
    
    if intent_id not in SEMANTIC_RELATION:
        SEMANTIC_RELATION[intent_id] = {}
    
    # 更新内存
    SEMANTIC_RELATION[intent_id][word] = weight
    
    # 更新数据库
    try:
        bionic_db.update_synapse_weight(intent_id, word, weight, user_id)
        logger.debug(f"更新语义关联: {intent_id} → {word} = {weight}")
    except Exception as e:
        logger.error(f"更新语义关联到数据库失败: {str(e)}")

def import_default_relations_to_db() -> None:
    """将默认语义关联导入到数据库，用于初始化"""
    try:
        imported_count = 0
        for intent_id, relations in DEFAULT_SEMANTIC_RELATION.items():
            for word, weight in relations.items():
                if bionic_db.add_synapse_weight(intent_id, word, weight):
                    imported_count += 1
        
        logger.info(f"默认语义关联导入完成，共导入{imported_count}条关联")
        
        # 重新加载关联
        _load_semantic_relations()
        
    except Exception as e:
        logger.error(f"导入默认语义关联失败: {str(e)}")

# 模块初始化时加载语义关联
_load_semantic_relations()

# 词性标注（简化版，纯规则实现）
def get_word_type(word: str) -> str:
    """获取词的类型：noun/verb/other"""
    # 简单规则判断
    if word in ["预算", "价格", "租金", "房型", "地铁", "天气", "温度", "预警", "热水器", "油烟机"]:
        return "noun"
    if word in ["租", "出租", "求租", "查询", "查", "修", "报修", "坏了", "漏水"]:
        return "verb"
    return "common"
