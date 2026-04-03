#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仿生架构核心神经元类
实现动态突触连接、权重计算、多意图并行激活
"""
import re
import jieba
from typing import List, Dict, Any, Optional, Tuple
from .db import bionic_db
from .cache import bionic_cache
from ...common.utils.logger import get_logger
from ...common.utils.price_extractor import price_extractor

logger = get_logger()

# 加载BM25语义匹配模块
try:
    from src.bm25_utils import intent_bm25
    BM25_ENABLED = True
    logger.info("BM25语义匹配模块加载成功")
except Exception as e:
    logger.warning(f"BM25模块加载失败，将使用原有匹配逻辑: {str(e)}")
    BM25_ENABLED = False

# 导入线程锁
import threading

# 中文数字映射
CN_NUM = {
    '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '百': 100, '千': 1000, '万': 10000, '亿': 100000000
}

# 中文数字单位优先级（用于分段处理）
CN_UNITS = ['亿', '万', '千', '百', '十']

def cn_to_num(cn_str: str) -> float:
    """
    中文数字转阿拉伯数字，适配租房场景常见写法：
    支持：十、十五、二十、三千五、一万二、两万五、三千零五、零点五、1千5
    兼容：混合数字+中文（如1万2）、纯单位（如万）、小数（如零点五）
    """
    if not cn_str or not isinstance(cn_str, str):
        return 0.0

    # 预处理：去除非数字/非单位字符（如"块""元""左右"），统一格式
    cn_str = cn_str.strip()
    # 兼容英文缩写（k=千，w=万）
    cn_str = cn_str.replace('k', '千').replace('K', '千').replace('w', '万').replace('W', '万')
    # 保留数字、中文数字、中文单位、小数点
    clean_chars = []
    for char in cn_str:
        if char in CN_NUM or char in CN_UNITS or char in '0123456789.点':
            clean_chars.append(char)
    cn_str = ''.join(clean_chars).replace('点', '.')
    if not cn_str:
        return 0.0

    # 处理小数场景（如"零点五""三点八"）
    if '.' in cn_str:
        integer_part, decimal_part = cn_str.split('.', 1)
        integer_num = _cn_integer_to_num(integer_part) if integer_part else 0
        decimal_num = 0.0
        # 处理小数部分（如"五"→0.5，"八"→0.8）
        if decimal_part:
            decimal_digits = []
            for char in decimal_part:
                if char in CN_NUM:
                    decimal_digits.append(str(CN_NUM[char]))
                elif char.isdigit():
                    decimal_digits.append(char)
            if decimal_digits:
                decimal_num = float(f"0.{''.join(decimal_digits)}")
        return integer_num + decimal_num

    # 处理纯整数场景
    return _cn_integer_to_num(cn_str)

def _cn_integer_to_num(cn_str: str) -> int:
    """内部函数：处理整数型中文数字（递归安全）"""
    if not cn_str:
        return 0

    # 处理混合数字+中文（如"1千5""2万"）
    cn_str = cn_str.replace('1千', '一千').replace('2千', '两千').replace('3千', '三千')
    cn_str = cn_str.replace('1万', '一万').replace('2万', '两万').replace('3万', '三万')
    cn_str = cn_str.replace('1百', '一百').replace('2百', '两百').replace('3百', '三百')

    # 优先处理大单位（亿、万），避免递归死循环
    for unit in ['亿', '万']:
        if unit in cn_str:
            parts = cn_str.split(unit, 1)
            left = _cn_integer_to_num(parts[0]) if parts[0] else 1  # 处理"万"→1万，"亿"→1亿
            
            # 处理右边部分时，如果右边是单个数字且没有后续单位，直接根据当前单位补全
            # 如"一万二"：parts[1]是"二"，直接乘以1000；兼容阿拉伯数字如"1万2"
            if len(parts) > 1 and parts[1]:
                right_part = parts[1].strip()
                is_single_digit = len(right_part) == 1 and right_part.isdigit()
                is_single_cn = len(right_part) == 1 and right_part in CN_NUM and CN_NUM[right_part] < 10
                if is_single_cn:
                    right = CN_NUM[right_part] * 1000 if unit == '万' else CN_NUM[right_part] * 10000000
                elif is_single_digit:
                    right = int(right_part) * 1000 if unit == '万' else int(right_part) * 10000000
                else:
                    right = _cn_integer_to_num(right_part)
            else:
                right = 0
                
            return left * CN_NUM[unit] + right

    # 处理千、百、十
    total = 0
    current = 0
    last_unit = None  # 记录上一个处理的单位，用于处理省略场景
    
    for char in cn_str:
        if char == '十':
            # 处理"十""十五""二十"：十单独出现=10，前面无数字=10，前面有数字=数字*10
            current = 10 if current == 0 else current * 10
            total += current
            current = 0
            last_unit = '十'
        elif char == '百':
            # 处理"百""千"：前面无数字=1*单位（如"百"=100），前面有数字=数字*单位
            unit_val = CN_NUM[char]
            current = unit_val if current == 0 else current * unit_val
            total += current
            current = 0
            last_unit = '百'
        elif char == '千':
            unit_val = CN_NUM[char]
            current = unit_val if current == 0 else current * unit_val
            total += current
            current = 0
            last_unit = '千'
        elif char == '零':
            # 零表示中间无单位，重置当前数字并清空上一个单位，避免后续数字被错误放大
            current = 0
            last_unit = None
        elif char in CN_NUM:
            # 处理个位数字（一~九）
            current = CN_NUM[char]
        elif char.isdigit():
            # 处理混合数字（如"15"→15）
            current = int(char)

    # 处理省略写法：最后剩余的数字根据上一个单位补全
    # 如"三千五"→上一个单位是千，5*100=500 → 3000+500=3500
    # 如"一万二"→上一个单位是万，2*1000=2000 → 10000+2000=12000
    # 如"一百八"→上一个单位是百，8*10=80 → 100+80=180
    if current > 0:
        if last_unit == '万':
            current *= 1000  # 万后面的数字是千级
        elif last_unit == '千':
            current *= 100  # 千后面的数字是百级
        elif last_unit == '百':
            current *= 10  # 百后面的数字是十级
        total += current

    # 修正"十"的特殊场景（如"十五"→15，"二十"→20）
    if total == 0 and cn_str == '十':
        total = 10

    return total

class SynapseNeuronCore:
    """突触神经元核心类（线程安全单例模式）"""
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # 双重检查锁定，确保线程安全
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化核心（使用标志位避免重复初始化）"""
        if SynapseNeuronCore._initialized:
            return
        with SynapseNeuronCore._lock:
            if not SynapseNeuronCore._initialized:
                self._load_neurons()
                SynapseNeuronCore._initialized = True
                logger.info("SynapseNeuronCore 初始化完成")

    def _init_core(self):
        """初始化核心（兼容旧版本调用）"""
        if not SynapseNeuronCore._initialized:
            self._load_neurons()
            SynapseNeuronCore._initialized = True
    
    def _load_neurons(self):
        """加载所有意图神经元和突触权重，自动同步场景配置到数据库"""
        # 第一步：同步场景配置中的意图到数据库
        self._sync_intents_from_config()
        
        # 第二步：从数据库加载神经元和权重
        self.intent_neurons = bionic_db.get_all_intent_neurons()
        self.synapse_weights = {}
        for neuron in self.intent_neurons:
            intent_id = neuron["intent_id"]
            self.synapse_weights[intent_id] = bionic_db.get_synapse_weights_by_intent(intent_id)
        logger.info(f"仿生架构核心初始化完成，加载意图神经元数量：{len(self.intent_neurons)}")
    
    def _sync_intents_from_config(self):
        """从场景配置文件同步所有意图到数据库"""
        try:
            from src.scene_loader import get_scene_loader
            
            # 获取场景加载器实例
            loader = get_scene_loader()
            
            # 获取所有已加载的场景配置
            scene_configs = loader.scene_config_cache
            
            synced_count = 0
            for scene_id, scene_config in scene_configs.items():
                # 跳过未启用的场景
                if not scene_config.get("base", {}).get("enabled", True):
                    continue
                    
                # 同步场景下的所有意图
                intents = scene_config.get("intent", {}).get("intents", [])
                for intent_config in intents:
                    intent_id = intent_config.get("intent_id", "")
                    if not intent_id:
                        continue
                    intent_name = intent_config.get("intent_name", intent_id)
                    description = intent_config.get("description", "")
                    base_priority = intent_config.get("priority", 1)
                    
                    # 添加到数据库
                    # 先查询是否已存在，存在的话不覆盖已有的route_target
                    exists = False
                    try:
                        with bionic_db.get_connection(write=False) as conn:
                            cursor = conn.cursor()
                            cursor.execute('SELECT id FROM intent_neurons WHERE intent_id = ?', (intent_id,))
                            exists = cursor.fetchone() is not None
                    except:
                        pass
                    
                    if not exists:
                        if bionic_db.add_intent_neuron(
                            scene_id=scene_id,
                            intent_id=intent_id,
                            intent_name=intent_name,
                            description=description,
                            base_priority=base_priority
                        ):
                            synced_count += 1
            
            if synced_count > 0:
                logger.info(f"自动同步场景意图到数据库完成，共同步{synced_count}个意图神经元")
                
        except Exception as e:
            logger.error(f"同步场景意图失败: {str(e)}", exc_info=True)
    
    def reload(self):
        """重载神经元和权重"""
        self._load_neurons()
    
    def _correct_text(self, text: str) -> str:
        """语义纠错：自动修正常见错别字和口语化表达（暂时停用，后续从数据库读取纠错规则）"""
        # 纠错规则后续迁移到数据库，暂时直接返回原始文本
        return text
    
    def _tokenize(self, text: str) -> List[Dict[str, Any]]:
        """语义分词，最小语义单元拆分，附带位置和词性信息"""
        # 先进行语义纠错
        corrected_text = self._correct_text(text)
        # 再按jieba分词
        words = jieba.lcut(corrected_text)
        total_length = len(words)
        tokenized = []
        
        for idx, word in enumerate(words):
            word_stripped = word.strip()
            # 停用词功能后续从数据库加载，暂时停用
            if not word_stripped: # or word_stripped in self.stop_words:
                continue
                
            # 计算位置权重：句子后半部分权重×1.5
            position_weight = 1.5 if idx > total_length / 2 else 1.0
            
            # 基础词性权重判断（简化实现，可后续扩展词性标注）
            word_length = len(word_stripped)
            if word_length >= 2:
                # 名词/动词通常长度≥2，权重×2
                type_weight = 2.0
            else:
                # 助词/单字权重×0.1
                type_weight = 0.1
            
            tokenized.append({
                "word": word_stripped,
                "position": idx,
                "position_weight": position_weight,
                "type_weight": type_weight,
                "total_weight": position_weight * type_weight
            })
        
        return tokenized
    
    def calculate_activation_scores(self, text: str, user_id: str = "global") -> Dict[str, float]:
        """计算所有意图神经元的激活强度（全局注意力打分算法）
        核心规则：
        1. 核心短语权重占70%，边缘词占30%
        2. 句子后半部分权重×1.5，名词/动词×2，助词×0.1
        3. 结合语义关联度和突触权重
        """
        from .semantic_core import calculate_semantic_weight, get_semantic_relation, is_stop_word
        
        tokens = self._tokenize(text)
        total_length = len(tokens)
        activation_scores = {}
        
        # 计算所有词的总权重，用于归一化
        total_word_weight = sum([t["total_weight"] for t in tokens]) if tokens else 1
        
        for neuron in self.intent_neurons:
            intent_id = neuron["intent_id"]
            base_priority = neuron["base_priority"]
            
            # 先查缓存
            weights = bionic_cache.get_synapse_weights(intent_id, user_id)
            if weights is None:
                # 缓存未命中，从数据库查询
                weights = self.synapse_weights.get(intent_id, {})
                # 个性化权重优先
                if user_id != "global":
                    user_weights = bionic_db.get_synapse_weights_by_intent(intent_id, user_id)
                    weights.update(user_weights)
                # 写入缓存
                bionic_cache.set_synapse_weights(intent_id, weights, user_id)
            
            total_score = base_priority * 0.5
            core_score = 0.0  # 核心短语得分（70%权重）
            edge_score = 0.0  # 边缘词得分（30%权重）
            
            for idx, token in enumerate(tokens):
                word = token["word"]
                attention_weight = token["total_weight"]
                
                # 忽略无意义助词
                if is_stop_word(word):
                    continue
                    
                # 计算语义关联度权重
                rel_weight = get_semantic_relation(intent_id, word)
                # 原有突触权重
                syn_weight = weights.get(word, 1.0)
                
                # 词的基础得分
                word_score = attention_weight * rel_weight * syn_weight
                
                # 区分核心词和边缘词：权重超过平均权重2倍的为核心词
                avg_weight = total_word_weight / total_length if total_length > 0 else 1
                if attention_weight >= avg_weight * 2:
                    core_score += word_score
                else:
                    edge_score += word_score
            
            # 加权合并：核心词70%，边缘词30%
            total_score += (core_score * 0.7 + edge_score * 0.3)
            
            # 融合BM25语义相似度得分（增强语义容错性）
            if BM25_ENABLED:
                bm25_score = intent_bm25.get_intent_score(text, intent_id)
                # BM25得分权重占40%，原有得分占60%，增强语义区分能力，解决相似意图混淆问题
                total_score = total_score * 0.6 + bm25_score * 0.4 * 10  # 乘以10对齐得分量级
            
            # 归一化处理，避免长文本得分过高
            if total_length > 0:
                total_score = total_score / (total_length * 0.5)
            
            activation_scores[intent_id] = max(0.0, total_score)
        
        return activation_scores

    def _match_general_intents(self, text: str) -> Dict[str, float]:
        """
        匹配6大类通用意图（独立方法，后续可扩展机器学习、规则引擎等多种匹配方式）
        :param text: 原始文本
        :return: 通用意图得分字典
        """
        text_lower = text.lower()
        intent_scores = {}
        
        # 从数据库缓存读取所有意图关键词，完全无硬编码
        intent_keyword_map = bionic_db.get_intent_keyword_cache()
        
        for intent_code, keywords in intent_keyword_map.items():
            match_count = 0
            for keyword in keywords:
                if keyword in text_lower:
                    match_count += 1
            if match_count > 0:
                score = match_count * 2.0  # 通用意图权重更高
                intent_scores[intent_code] = score
        
        return intent_scores
    
    def _merge_intent_scores(self, business_scores: Dict[str, float], general_scores: Dict[str, float]) -> Dict[str, float]:
        """
        合并业务意图和通用意图的分数（独立方法，后续可配置合并权重、优先级等策略）
        :param business_scores: 业务意图得分
        :param general_scores: 通用意图得分
        :return: 合并后的得分
        """
        # 目前只保留通用意图，后续可根据配置选择合并策略
        # return {**business_scores, **general_scores} # 合并所有意图
        return general_scores  # 暂时只使用通用意图
    
    def recognize_intent(self, text: str, user_id: str = "global", enable_multi_intent: bool = True, multi_intent_threshold: float = 0.5) -> Dict[str, Any]:
        """
        识别意图，支持多意图并行激活，按「优先级+激活强度」综合排序
        :param text: 用户输入文本
        :param user_id: 用户ID
        :param enable_multi_intent: 是否开启多意图识别（默认开启）
        :param multi_intent_threshold: 多意图阈值，激活强度达到主意图的百分比以上则保留
        :return: 识别结果
        """
        # 1. 计算业务意图激活分数（原有业务逻辑，后续可独立扩展
        activation_scores = self.calculate_activation_scores(text, user_id)
        
        # 2. 匹配6大类通用意图（独立方法，后续可扩展其他匹配算法
        general_intent_scores = self._match_general_intents(text)
        
        # 3. 合并意图分数（统一合并策略可独立配置）
        all_scores = self._merge_intent_scores(activation_scores, general_intent_scores)
        
        intent_dict_cache = bionic_db.get_intent_dict_cache()
        
        # 兜底逻辑：如果没有匹配到任何意图，默认返回请求类顶层意图（确保前端显示正常）
        if not all_scores or not intent_dict_cache:
            return {
                "main_intent": "request",
                "main_intent_name": "请求/指令",
                "main_priority": 100,
                "intent_confidence": 0.6,
                "scene_id": "default",
                "all_intents": [{"intent_code": "request", "intent_name": "请求/指令", "priority": 100, "confidence": 0.6}],
                "sub_intent": None,
                "sub_intent_name": None,
                "entities": []
            }
        
        max_score = max(all_scores.values()) if max(all_scores.values()) > 0 else 1
        
        # 第一步：过滤掉低于阈值的意图，优先保留6大类通用意图，业务意图优先级降低
        filtered_intents = []
        for intent_id, score in all_scores.items():
            normalized_score = score / max_score
            if normalized_score >= multi_intent_threshold:
                # 所有意图信息完全从数据库读取，无硬编码
                intent_info = intent_dict_cache.get(intent_id, {})
                if intent_info:
                    filtered_intents.append({
                        "intent_code": intent_id,
                        "intent_name": intent_info.get("intent_name", intent_id),
                        "priority": intent_info.get("priority", 999),
                        "confidence": round(normalized_score, 4),
                        "parent_code": intent_info.get("parent_code", "")
                    })
        
        # 第二步：综合排序：先按优先级升序（优先级数字越小越靠前），再按置信度降序
        sorted_intents = sorted(
            filtered_intents, 
            key=lambda x: (x["priority"], -x["confidence"])
        )
        
        # 主意图取排序后的第一个
        main_intent = sorted_intents[0] if sorted_intents else None
        
        result = {
            "main_intent": main_intent["intent_code"] if main_intent else None,
            "main_intent_name": main_intent["intent_name"] if main_intent else None,
            "main_priority": main_intent["priority"] if main_intent else 999,
            "intent_confidence": main_intent["confidence"] if main_intent else 0.0,
            "scene_id": main_intent.get("scene_id", "default") if main_intent else "default",
            "all_intents": sorted_intents,  # 所有匹配到的意图，按优先级+置信度综合排序
            "synapse_weights": all_scores
        }
        
        # 子意图（兼容旧逻辑）
        if len(sorted_intents) >= 2:
            result["sub_intent"] = sorted_intents[1]["intent_code"]
            result["sub_intent_name"] = sorted_intents[1]["intent_name"]
        else:
            result["sub_intent"] = None
            result["sub_intent_name"] = None
        
        # 提取文本中的房源实体
        try:
            entities = self._extract_entities(text)
            result["entities"] = entities
        except Exception as e:
            print(f"实体提取异常: {e}")
            result["entities"] = []
        
        # 匹配业务意图（当前默认租房领域，后续可扩展多行业切换）
        try:
            business_intents = self._match_business_intents(text, industry_code="rental")
            result["business_intent"] = business_intents
        except Exception as e:
            print(f"业务意图匹配异常: {e}")
            result["business_intent"] = []
        
        # 情绪分析
        try:
            emotion_result = self._analyze_emotion(text)
            result["emotion"] = emotion_result
        except Exception as e:
            print(f"情绪分析异常: {e}")
            result["emotion"] = {}
        
        return result
    
    def _analyze_emotion(self, text: str) -> Dict[str, Any]:
        """
        情绪分析：正负向识别、强度判断、反讽识别
        :param text: 原始文本
        :return: 情绪分析结果
        """
        text_lower = text.lower()
        emotion_keyword_cache = bionic_db.get_emotion_keyword_cache()
        emotion_dict_cache = bionic_db.get_emotion_dict_cache()
        
        # 匹配到的情绪关键词
        matched_emotions = []
        has_sarcasm = False
        total_positive_score = 0.0
        total_negative_score = 0.0
        max_intensity = 0.0
        
        # 遍历所有情绪关键词，实现最长匹配优先，避免短关键词干扰
        # 先按关键词长度倒序排序，优先匹配长关键词
        sorted_keywords = sorted(emotion_keyword_cache.keys(), key=lambda x: -len(x))
        matched_positions = set()  # 记录已经匹配到的字符位置，避免重复匹配
        
        for keyword in sorted_keywords:
            emotion_list = emotion_keyword_cache[keyword]
            keyword_len = len(keyword)
            
            # 查找所有匹配位置
            start_idx = 0
            while True:
                pos = text_lower.find(keyword, start_idx)
                if pos == -1:
                    break
                
                # 检查这个位置是否已经被更长的关键词匹配过
                overlap = False
                for i in range(pos, pos + keyword_len):
                    if i in matched_positions:
                        overlap = True
                        break
                
                if not overlap:
                    # 标记这些位置为已匹配
                    for i in range(pos, pos + keyword_len):
                        matched_positions.add(i)
                    
                    # 统计匹配
                    for emotion in emotion_list:
                        score = emotion["weight"]
                        if emotion["emotion_type"] == "positive":
                            total_positive_score += score
                        elif emotion["emotion_type"] == "negative":
                            total_negative_score += score
                        elif emotion["emotion_type"] == "sarcasm":
                            has_sarcasm = True
                        
                        # 记录匹配到的情绪
                        emotion_info = emotion_dict_cache.get(emotion["emotion_code"], {})
                        matched_emotions.append({
                            "emotion_code": emotion["emotion_code"],
                            "emotion_name": emotion_info.get("emotion_name", "未知"),
                            "emotion_type": emotion["emotion_type"],
                            "score": score,
                            "keyword": keyword,
                            "is_anti_sarcasm": emotion["is_anti_sarcasm"]
                        })
                        
                        # 计算最大强度
                        current_intensity = score * emotion_info.get("intensity_weight", 1.0)
                        if current_intensity > max_intensity:
                            max_intensity = current_intensity
                
                start_idx = pos + 1
        
        # 反讽处理：反转情绪极性
        if has_sarcasm:
            total_positive_score, total_negative_score = total_negative_score, total_positive_score
        
        # 计算最终情绪类型
        if total_positive_score > total_negative_score:
            final_type = "positive"
            final_type_name = "正向情绪"
            final_score = total_positive_score
        elif total_negative_score > total_positive_score:
            final_type = "negative"
            final_type_name = "负向情绪"
            final_score = total_negative_score
        else:
            final_type = "neutral"
            final_type_name = "中性情绪"
            final_score = 0.0
        
        # 计算情绪强度（归一化到0-10分）
        if final_score > 0:
            intensity = min(round(final_score * 2, 1), 10.0)
        else:
            intensity = 0.0
        
        # 按得分排序匹配到的情绪
        matched_emotions.sort(key=lambda x: -x["score"])
        
        return {
            "type": final_type,
            "type_name": final_type_name,
            "intensity": intensity,
            "has_sarcasm": has_sarcasm,
            "matched_emotions": matched_emotions[:3]  # 最多返回前3个匹配度最高的情绪
        }
    
    def _match_business_intents(self, text: str, industry_code: str = "rental") -> List[Dict[str, Any]]:
        """
        匹配业务领域意图，支持多行业扩展（通用底座）
        :param text: 原始文本
        :param industry_code: 行业编码，默认rental(租房)
        :return: 业务意图列表
        """
        text_lower = text.lower()
        intent_scores = {}
        
        # 从数据库缓存读取对应行业的业务意图关键词
        business_keyword_map = bionic_db.get_business_intent_keyword_cache(industry_code)
        business_intent_list = bionic_db.get_business_intent_cache(industry_code)
        
        # 关键词匹配
        for intent_code, keywords in business_keyword_map.items():
            match_count = 0
            for keyword in keywords:
                if keyword in text_lower:
                    match_count += 1
            if match_count > 0:
                intent_scores[intent_code] = match_count * 2.0
        
        # 转换为标准化结果
        result = []
        max_score = max(intent_scores.values()) if intent_scores else 1
        
        for intent_code, score in intent_scores.items():
            normalized_score = score / max_score
            # 找到对应的意图信息
            intent_info = next((i for i in business_intent_list if i["intent_code"] == intent_code), None)
            if intent_info:
                result.append({
                    "intent_code": intent_code,
                    "intent_name": intent_info["intent_name"],
                    "priority": intent_info["priority"],
                    "confidence": round(normalized_score, 4),
                    "related_general_intent": intent_info["related_general_intent"]
                })
        
        # 按优先级+置信度排序
        result.sort(key=lambda x: (x["priority"], -x["confidence"]))
        return result
    
    def _extract_entities(self, text: str, industry_code: str = "rental") -> List[Dict[str, Any]]:
        """
        提取文本中的实体，从数据库缓存读取实体关键词规则，实现最长匹配优先，避免重复提取
        :param text: 原始文本
        :param industry_code: 行业编码，默认rental(租房)
        :return: 实体列表，包含类型、名称、匹配文本
        """
        text_lower = text.lower()
        all_matches = []
        
        # 1. 从数据库缓存读取通用实体关键词
        entity_keyword_map = bionic_db.get_entity_keyword_cache()
        
        # 2. 读取业务实体关键词，合并到匹配规则（优先级更高）
        business_entity_keyword_map = bionic_db.get_business_entity_keyword_cache(industry_code)
        business_entities = bionic_db.get_business_entity_cache(industry_code)
        
        for entity_type, keywords in business_entity_keyword_map.items():
            # 获取业务实体的名称
            entity_name = entity_type
            for be in business_entities:
                if be["entity_type"] == entity_type:
                    entity_name = be["entity_name"]
                    break
            # 添加到匹配规则
            if entity_type not in entity_keyword_map:
                entity_keyword_map[entity_type] = {}
            entity_keyword_map[entity_type][entity_name] = keywords
        
        # 第一步：收集所有匹配到的关键词及其位置信息
        for entity_type, entity_dict in entity_keyword_map.items():
            for entity_name, keywords in entity_dict.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        # 找到所有匹配位置
                        start_idx = 0
                        while True:
                            pos = text_lower.find(keyword, start_idx)
                            if pos == -1:
                                break
                            all_matches.append({
                                "keyword": keyword,
                                "start": pos,
                                "end": pos + len(keyword),
                                "length": len(keyword),
                                "type": entity_type,
                                "name": entity_name
                            })
                            start_idx = pos + 1
        
        # 第二步：最长匹配优先，过滤被包含的短匹配
        filtered_matches = []
        # 先按长度从大到小排序
        all_matches_sorted = sorted(all_matches, key=lambda x: -x["length"])
        used_positions = set()
        
        for match in all_matches_sorted:
            # 检查当前匹配的位置是否已经被使用
            overlap = False
            for i in range(match["start"], match["end"]):
                if i in used_positions:
                    overlap = True
                    break
            if not overlap:
                filtered_matches.append(match)
                # 标记位置为已使用
                for i in range(match["start"], match["end"]):
                    used_positions.add(i)
        
        # 第三步：去重（同一位置的相同关键词只保留一个）
        unique_matches = {}
        for match in filtered_matches:
            key = f"{match['start']}_{match['end']}_{match['keyword']}"
            if key not in unique_matches:
                unique_matches[key] = match
        
        # 收集所有已匹配的位置
        matched_positions = set()
        for match in unique_matches.values():
            for i in range(match["start"], match["end"]):
                matched_positions.add(i)
        
        # 第四步：转换为返回格式，按出现位置排序，特殊实体扩展处理
        entities = []
        for match in sorted(unique_matches.values(), key=lambda x: x["start"]):
            match_text = match["keyword"]
            # 特殊处理：小区/花园/公寓类实体，自动向前扩展提取完整名称
            if match["type"] == "community":
                # 向前查找连续的中文/数字/字母，遇到助词/代词/标点/空格就停止
                start = match["start"]
                # 停止字符列表：助词、代词、标点等非名称字符
                stop_chars = {"的", "这", "那", "套", "个", "是", "有", "在", "和", "与", " ", "\t", "\n", "，", "。", "！", "？", "、", "；", "："}
                # 最多向前扩展10个字符，避免过长
                max_extend = 10
                extend_count = 0
                while start > 0 and extend_count < max_extend:
                    prev_char = text[start - 1]
                    # 遇到停止字符则停止
                    if prev_char in stop_chars:
                        break
                    # 允许中文字符、数字、字母作为小区名称的一部分
                    if ('\u4e00' <= prev_char <= '\u9fff') or prev_char.isalnum():
                        start -= 1
                        extend_count += 1
                    else:
                        break
                # 如果有扩展内容，更新匹配文本
                if start < match["start"]:
                    match_text = text[start:match["end"]]
            
            # 过滤空值和单独的租金关键词（避免和后面的金额重复）
            if match["type"] == "rent_info" and match_text in ["租金", "房租", "月租", "价格", "预算"]:
                # 检查后面是否有金额实体，避免重复
                has_amount = False
                for other_match in unique_matches.values():
                    if other_match["type"] == "rent_info" and other_match["start"] > match["start"] \
                        and any(c.isdigit() for c in other_match["keyword"]):
                        has_amount = True
                        break
                if has_amount:
                    continue
            
            entities.append({
                "type": match["type"],
                "name": match["name"],
                "text": match_text
            })
        
        # 额外处理：使用专业价格提取器自动识别金额，支持所有常见格式
        # 金额自动识别完全基于已匹配的实体（100%从数据库动态获取，无任何硬编码）
        rent_entity_type = None
        rent_entity_name = None
        rent_keyword_index = -1
        
        # 从业务实体配置中判断哪些是金额类实体（完全数据库驱动，零硬编码）
        if entities:
            # 获取当前业务类型的所有金额类实体定义
            business_entities = bionic_db.get_business_entity_cache(industry_code)
            amount_entity_types = [be["entity_type"] for be in business_entities if be.get("is_amount_entity", 0) == 1]
            
            # 查找金额类实体，优先匹配第一个
            for i, entity in enumerate(entities):
                if entity["type"] in amount_entity_types:
                    rent_entity_type = entity["type"]
                    rent_entity_name = entity["name"]
                    # 记录单独的租金关键词位置，后续去重
                    if entity["text"] in ["租金", "房租", "月租", "价格", "预算"]:
                        rent_keyword_index = i
                    break
        
        # 如果没有匹配到金额类实体，则不自动识别金额，避免归属错误
        if not rent_entity_type:
            return entities
        
        # 使用专业价格提取器提取金额（支持结构化、口语化、错别字、修饰词、多价格）
        prices = price_extractor.extract(text)
        valid_prices = []
        
        # 筛选有效价格，排除位置重叠的
        for price_info in prices:
            if not price_info["raw_price"] or price_info["start"] < 0:
                continue
                
            # 检查是否被其他实体占用
            overlap = False
            for i in range(price_info["start"], price_info["end"]):
                if i in matched_positions:
                    overlap = True
                    break
            if not overlap:
                valid_prices.append(price_info)
        
        # 处理价格：多个价格合并为区间，单个价格直接显示
        if valid_prices:
            # 按照金额排序
            valid_prices.sort(key=lambda x: x["number"])
            
            if len(valid_prices) >= 2:
                # 多价格合并为区间：自动识别上下限
                min_price = valid_prices[0]
                max_price = valid_prices[-1]
                
                # 处理第一个价格的浮动范围（左右/大概）
                min_val = min_price["number"]
                if min_price["modifier"] in ["左右", "大概", "差不多", "约"]:
                    min_val = min_val * 0.9  # 下浮10%
                elif min_price["modifier"] in ["以上", "至少", "大于", "超过"]:
                    min_val = min_val  # 就是下限
                
                # 处理第二个价格的上限
                max_val = max_price["number"]
                if max_price["modifier"] in ["左右", "大概", "差不多", "约"]:
                    max_val = max_val * 1.1  # 上浮10%
                elif max_price["modifier"] in ["以内", "不超过", "低于", "小于"]:
                    max_val = max_val  # 就是上限
                
                # 合并显示
                entities.append({
                    "type": rent_entity_type,
                    "name": rent_entity_name,
                    "text": f"{min_price['raw_price']} ~ {max_price['raw_price']}（{int(min_val)}-{int(max_val)}元）"
                })
                
                # 标记所有价格位置
                for price in valid_prices:
                    for i in range(price["start"], price["end"]):
                        matched_positions.add(i)
            else:
                # 单个价格
                price_info = valid_prices[0]
                display_text = f"{price_info['raw_price']}（{price_info['number']:.0f}{price_info['unit']}）"
                
                # 添加浮动说明
                if price_info["modifier"] in ["左右", "大概", "差不多", "约"]:
                    display_text = f"{display_text}（±10%浮动）"
                elif price_info["modifier"] in ["以内", "不超过", "低于", "小于"]:
                    display_text = f"{display_text}（上限）"
                elif price_info["modifier"] in ["以上", "至少", "大于", "超过"]:
                    display_text = f"{display_text}（下限）"
                
                entities.append({
                    "type": rent_entity_type,
                    "name": rent_entity_name,
                    "text": display_text
                })
                
                # 标记位置
                for i in range(price_info["start"], price_info["end"]):
                    matched_positions.add(i)
        
        # 去重：如果成功提取到金额实体，删除前面单独的租金关键词
        if len([e for e in entities if e["type"] == rent_entity_type and any(c.isdigit() for c in e["text"])]) > 0 and rent_keyword_index >= 0:
            del entities[rent_keyword_index]
        
        return entities

# 全局单例实例
