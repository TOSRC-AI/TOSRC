#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用价格提取器（基于分层正则+语义兜底方案）
完全适配仿生架构，支持自主学习扩展
"""
import re
from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional, TypedDict

class PriceInfo(TypedDict):
    """价格信息类型定义"""
    raw_price: str
    number: float
    unit: str
    modifier: str
    start: int
    end: int
    need_learn: Optional[bool]

from ...common.utils.semantic_classifier import number_classifier

# 核心价格正则（预编译）：支持3k5、2w3这种缩写格式
PRICE_CORE_PATTERN = re.compile(
    r'(?P<number>\d+(?:\.\d+)?)'
    r'(?P<unit>元|万|千|k|块|仟|圆|w|W)?'
    r'(?P<suffix_num>\d)?'  # 支持3k5=3500、2w3=23000
    r'|'
    r'(?P<unit2>元|万|千|k|块|仟|圆|w|W)'
    r'(?P<number2>\d+(?:\.\d+)?)',
    re.IGNORECASE | re.UNICODE
)

# 价格修饰词正则（预编译）
PRICE_MODIFIER_PATTERN = re.compile(r'左右|上下|不超|不超过|不低于|不少于|大概|大约|差不多|以内|以上|以下', re.UNICODE)

# 口语化/错别字映射表（可通过仿生架构自主学习扩展）
PRICE_SLANG_MAP = {
    "仟": "千",
    "圆": "元",
    "块钱": "元",
    "qian": "千",
    "wan": "万",
    "kuai": "块",
    "yuan": "元",
    "w": "万",
    "W": "万",
    "k": "千",
    "K": "千"
}

def get_similarity(a: str, b: str) -> float:
    """计算字符串相似度，兼容错别字"""
    return SequenceMatcher(None, a, b).ratio()

def extract_price_core(text: str) -> List[PriceInfo]:
    """核心价格提取（结构化价格，支持提取多个价格）"""
    prices = []
    
    # 提取修饰词
    modifiers = PRICE_MODIFIER_PATTERN.findall(text)
    
    # 提取数字+单位
    matches = PRICE_CORE_PATTERN.finditer(text)
    for match in matches:
        number = match.group("number") or match.group("number2")
        unit = match.group("unit") or match.group("unit2")
        suffix_num = match.group("suffix_num")  # 3k5的5
        
        if not number:
            continue
            
        # 金额单位明确的，直接通过，不需要语义分类校验
        unit = match.group("unit") or match.group("unit2")
        if unit and unit.strip():
            # 只需要检查是否是面积单位
            match_end = match.end()
            if match_end < len(text):
                next_char = text[match_end:match_end+2] if match_end + 2 <= len(text) else text[match_end:]
                if next_char.startswith(("平", "㎡", "m²", "平方")):
                    continue
            # 明确带金额单位的直接放行，避免误过滤
            pass
        else:
            # 没有明确单位的纯数字，才需要语义分类校验
            start = max(0, match.start() - 10)
            end = min(len(text), match.end() + 10)
            context = text[start:end]
            label, confidence = number_classifier.predict(context)
            
            # 置信度>70%且是金额才保留
            if confidence < 0.7 or label != "amount":
                continue
        
        # 处理后缀数字：3k5=3500
        number_float = float(number)
        if suffix_num and unit in ["千", "k", "K", "万", "w", "W"]:
            suffix = float(suffix_num)
            if unit in ["千", "k", "K"]:
                number_float = number_float * 1000 + suffix * 100
            elif unit in ["万", "w", "W"]:
                number_float = number_float * 10000 + suffix * 1000
        
        # 单位标准化
        unit_norm = "元"
        if unit in ["万", "仟", "w", "W"]:
            if not suffix_num:  # 后缀已经算过乘数
                number_float *= 10000
        elif unit in ["千", "k", "K"]:
            if not suffix_num:  # 后缀已经算过乘数
                number_float *= 1000
        elif unit in ["块", "圆", "yuan", "kuai"]:
            unit_norm = "元"
        
        # 查找匹配位置附近的修饰词
        modifier = ""
        match_start = match.start()
        match_end = match.end()
        for m in modifiers:
            m_pos = text.find(m)
            if abs(m_pos - match_end) < 5 or abs(m_pos - match_start) < 5:
                modifier = m
                break
        
        price_info = {
            "raw_price": f"{match.group(0)}{modifier}",
            "number": number_float,
            "unit": unit_norm,
            "modifier": modifier,
            "start": match_start,
            "end": match_end
        }
        prices.append(price_info)
    
    return prices

def extract_price_fuzzy(text: str) -> List[PriceInfo]:
    """模糊价格提取（兼容口语化/错别字，支持多个价格）"""
    # 替换口语化/错别字
    text_processed = text
    for slang, norm in PRICE_SLANG_MAP.items():
        text_processed = text_processed.replace(slang, norm)
    
    # 核心匹配
    prices = extract_price_core(text_processed)
    
    # 兜底：提取纯数字（无单位），增加校验避免误识别
    if not prices and any(char.isdigit() for char in text):
        numbers = re.finditer(r'\d+(?:\.\d+)?', text)
        for match in numbers:
            num = match.group()
            start = match.start()
            end = match.end()
            
            # 1. 排除面积单位：数字后面是平/㎡等
            if end < len(text):
                next_char = text[end:end+2] if end + 2 <= len(text) else text[end:]
                if next_char.startswith(("平", "㎡", "m²", "平方")):
                    continue
            
            # 2. 语义分类校验：必须是金额类型
            context_start = max(0, start - 10)
            context_end = min(len(text), end + 10)
            context = text[context_start:context_end]
            label, confidence = number_classifier.predict(context)
            if confidence < 0.7 or label != "amount":
                continue
            
            # 全部校验通过才加入
            price_info = {
                "raw_price": f"{num}元",
                "number": float(num),
                "unit": "元",
                "modifier": "",
                "start": start,
                "end": end
            }
            prices.append(price_info)
    
    return prices

# 全局提取函数
def extract_price(text: str) -> List[PriceInfo]:
    """对外统一接口：提取所有价格信息"""
    return extract_price_fuzzy(text)

# 仿生架构扩展：价格提取器（支持自主学习）
class BionicPriceExtractor:
    def __init__(self):
        self.unmatched_samples = []  # 未匹配样本池（用于自主学习）
        self.slang_map = PRICE_SLANG_MAP.copy()  # 可动态更新的映射表
    
    def extract(self, text: str) -> List[PriceInfo]:
        """提取价格（整合模糊匹配+自主学习，支持多个价格）"""
        prices = extract_price_fuzzy(text)
        
        # 未匹配则存入样本池
        if not prices and any(char.isdigit() for char in text):
            self.unmatched_samples.append(text)
            return [{
                "raw_price": "",
                "number": 0.0,
                "unit": "元",
                "modifier": "",
                "start": -1,
                "end": -1,
                "need_learn": True
            }]
        
        # 添加学习标记
        for price in prices:
            price["need_learn"] = False
        
        return prices
    
    def learn(self, sample: str, correct_number: float) -> Dict[str, str]:
        """自主学习：更新映射表"""
        # 提取样本中的非数字特征
        non_digit_chars = [c for c in sample if not c.isdigit()]
        non_digit_str = "".join(non_digit_chars).strip()
        
        if not non_digit_str:
            return self.slang_map
        
        # 匹配最可能的单位
        target_unit = ""
        if correct_number >= 10000:
            target_unit = "万"
        elif correct_number >= 1000:
            target_unit = "千"
        else:
            target_unit = "元"
        
        # 更新映射表
        if non_digit_str not in self.slang_map:
            self.slang_map[non_digit_str] = target_unit
            # 全局更新
            global PRICE_SLANG_MAP
            PRICE_SLANG_MAP[non_digit_str] = target_unit
        
        return self.slang_map

# 全局单例
price_extractor = BionicPriceExtractor()
