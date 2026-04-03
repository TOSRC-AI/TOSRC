#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调度引擎：核心控制层，根据配置和规则置信度决定请求走规则引擎还是LLM
完全兼容《外接LLM调教系统方案》中的调度逻辑，支持多场景、可配置、热更新
"""
import os
import json
import threading
from typing import Dict, Any, Tuple, Optional
from ..common.utils.logger import get_logger
from ..common.interface.dal import BaseDAL
from ..common.interface.net import BaseNetworkAdapter
from ..common.interface.tenant import BaseTenantAdapter
from .strategy.rule_package_manager import RulePackageManager
from .strategy.rule_miner import RuleMiner
from ..semantic.neuron_core import NeuronCore
from ..plugin.manager.llm_annotator import LLMAnnotator
from ..plugin.manager.auto_learner import AutoLearner

logger = get_logger()

class Scheduler:
    """调度引擎核心类
    依赖抽象接口，所有差异化实现由适配层注入
    """
    def __init__(self, 
                 dal: BaseDAL,
                 net_adapter: BaseNetworkAdapter,
                 neuron_core: NeuronCore,
                 llm_annotator: LLMAnnotator,
                 auto_learner: AutoLearner,
                 rule_package_manager: RulePackageManager,
                 rule_miner: RuleMiner,
                 tenant_adapter: Optional[BaseTenantAdapter] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        初始化调度引擎
        :param dal: 数据访问层适配实例（单租户传SQLite实现，多租户传MySQL实现）
        :param net_adapter: 网络适配实例（单租户传离线实现，多租户传联网实现）
        :param neuron_core: 语义识别核心实例（由适配层创建传入）
        :param llm_annotator: LLM标注器实例（由适配层创建传入）
        :param auto_learner: 自动学习模块实例（由适配层创建传入）
        :param rule_package_manager: 规则包管理器实例（由适配层创建传入）
        :param rule_miner: 规则挖掘模块实例（由适配层创建传入）
        :param tenant_adapter: 租户适配实例（仅多租户需要，单租户可不传）
        :param config: 调度配置，不传则使用默认配置
        """
        # 适配层实例（Core仅依赖接口，不关心具体实现）
        self.dal = dal
        self.net_adapter = net_adapter
        self.tenant_adapter = tenant_adapter
        # 配置文件路径
        self.config_path = "config/scheduler_config.json"
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        # 加载调度配置
        self.config = config or self._load_config()
        # 所有核心模块由适配层创建传入，避免重复初始化
        self.rule_engine = neuron_core
        self.llm_annotator = llm_annotator
        self.auto_learner = auto_learner
        self.rule_package_manager = rule_package_manager
        self.rule_miner = rule_miner
        logger.info("调度引擎初始化成功")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载调度配置，不存在则创建默认配置"""
        default_config = {
            "confidence_threshold": 0.9,  # 规则置信度阈值
            "llm_fallback_rate_threshold": 0.05,  # LLM fallback率阈值，低于可关闭LLM
            "rule_coverage_threshold": 0.95,  # 规则覆盖率阈值，高于可关闭LLM
            "log_enable": True,  # 是否启用日志
            "llm_call_limit": 1000,  # 每日LLM调用上限
            "llm_enabled": True,  # 全局LLM开关
            "mode": "hybrid",  # 运行模式: rule_only/hybrid/llm_only
            "scene_rule_map": {  # 场景-规则包映射
                "rental": "rental_rules.json"
            },
            "auto_reload_config": True  # 配置自动热更新
        }
        
        # 配置文件不存在则创建默认配置
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            logger.info("已创建默认调度配置文件: config/scheduler_config.json")
            return default_config
        
        # 加载现有配置
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            # 补全缺失的配置项
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            logger.info("调度配置加载成功")
            return config
        except Exception as e:
            logger.error(f"调度配置加载失败，使用默认配置: {str(e)}")
            return default_config
    
    def _reload_config_if_needed(self) -> None:
        """配置自动热更新"""
        if self.config.get("auto_reload_config", True) and os.path.exists(self.config_path):
            # 检查修改时间，有更新则重载
            # 简化实现，后续可优化为监听文件变化
            pass
    
    def _get_rule_confidence(self, entities: list, intents: list) -> float:
        """计算规则识别结果的置信度
        基于匹配到的实体数量、意图置信度综合计算
        """
        if not entities and not intents:
            return 0.0
        
        # 简单计算：有实体+0.3，每个意图置信度取最高值
        confidence = 0.3 if entities else 0.0
        max_intent_conf = max([intent.get("confidence", 0.0) for intent in intents], default=0.0)
        confidence += max_intent_conf * 0.7
        
        return min(confidence, 1.0)
    
    def _adapt_result(self, text: str, entities: list, intents: list, emotion: dict = None, 
                    mode: str = "rule", confidence: float = 1.0) -> Dict[str, Any]:
        """统一适配返回格式，兼容现有系统和方案中的标准格式
        """
        # 现有系统的返回格式（适配前端）
        top_intent = intents[0] if intents else {}
        
        return {
            "text": text,
            "intents": intents,
            "entities": entities,
            "emotion": emotion or {},
            "top_intent": top_intent.get("name", ""),
            "top_intent_confidence": top_intent.get("confidence", 0.0),
            # 方案中要求的扩展字段
            "mode": mode,
            "source": "rule" if mode == "rule_only" else "llm",
            "confidence": confidence
        }
    
    def process(self, text: str, scene: str = "rental", allow_llm: bool = None, 
               need_annotation: bool = False) -> Dict[str, Any]:
        """
        核心调度处理方法
        Args:
            text: 用户输入文本
            scene: 行业场景编码
            allow_llm: 是否允许调用LLM，覆盖全局配置
            need_annotation: 是否返回LLM原始标注数据
        Returns:
            统一结构化识别结果
        """
        self._reload_config_if_needed()
        allow_llm = allow_llm if allow_llm is not None else self.config.get("llm_enabled", True)
        mode = self.config.get("mode", "hybrid")
        
        # 模式1：仅规则引擎模式
        if mode == "rule_only" or not allow_llm:
            # 调用现有规则引擎识别
            entities = self.rule_engine._extract_entities(text, scene)
            intent_result = self.rule_engine.recognize_intent(text, enable_multi_intent=True)
            intents = intent_result.get("intents", [])
            emotion = self.rule_engine._analyze_emotion(text)
            
            confidence = self._get_rule_confidence(entities, intents)
            return self._adapt_result(text, entities, intents, emotion, 
                                     mode="rule_only", confidence=confidence)
        
        # 模式2：仅LLM模式（预留，后续实现）
        if mode == "llm_only" and self.llm_annotator:
            # TODO: 调用LLM标注模块
            llm_result = self.llm_annotator.annotate(text, scene)
            # 自动存入标注库
            # TODO: 标注数据入库逻辑
            return self._adapt_result(text, [], [], mode="llm_only")
        
        # 模式3：混合模式（默认），优先规则引擎，低置信度fallback到LLM
        # 第一步：优先调用规则引擎
        entities = self.rule_engine._extract_entities(text, scene)
        intents = self.rule_engine._extract_intent(text, scene)
        emotion = self.rule_engine._extract_emotion(text)
        confidence = self._get_rule_confidence(entities, intents)
        
        # 置信度达标，直接返回规则结果
        if confidence >= self.config.get("confidence_threshold", 0.9):
            return self._adapt_result(text, entities, intents, emotion, 
                                     mode="hybrid", confidence=confidence)
        
        # 置信度不足，fallback到LLM标注
        if self.llm_annotator and self.llm_annotator.client:
            logger.info(f"规则置信度{confidence:.2%} < 阈值{self.config.get('confidence_threshold', 0.9):.2%}，fallback到LLM标注")
            llm_annotation = self.llm_annotator.annotate(text, scene)
            
            if llm_annotation:
                # 将LLM标注结果适配为系统统一格式
                llm_entities = []
                for ent in llm_annotation.get("entities", []):
                    # 查找实体类型对应的显示名称
                    entity_name = ent.get("entity", "")
                    # 尝试从规则包中获取实体名称
                    scene_rules = rule_package_manager.get_scene_rules(scene)
                    for er in scene_rules.get("entity_rules", []):
                        if er.get("entity_type") == entity_name:
                            # 暂用实体类型作为名称，后续可以优化映射
                            entity_name = er.get("entity_type", entity_name)
                            break
                    
                    llm_entities.append({
                        "type": ent.get("entity", ""),
                        "name": entity_name,
                        "text": f"{ent.get('value', '')}{ent.get('unit', '')}"
                    })
                
                # 适配意图格式
                llm_intents = [{
                    "name": llm_annotation.get("intent", {}).get("name", ""),
                    "confidence": llm_annotation.get("intent", {}).get("confidence", 1.0),
                    "is_negated": llm_annotation.get("intent", {}).get("is_negated", False),
                    "is_question": llm_annotation.get("intent", {}).get("is_question", False)
                }]
                
                # 适配情绪格式
                llm_emotion = llm_annotation.get("emotion", {})
                
                logger.info("LLM标注成功，返回LLM结果")
                
                # 异步触发自动学习检查，不影响响应速度
                def async_learn_check():
                    try:
                        auto_learner.learn(scene)
                    except Exception as e:
                        logger.error(f"自动学习检查失败: {str(e)}")
                
                threading.Thread(target=async_learn_check, daemon=True).start()
                
                return self._adapt_result(text, llm_entities, llm_intents, llm_emotion, 
                                         mode="hybrid", confidence=1.0)
        
        # LLM不可用或标注失败，fallback回规则结果
        logger.warning("LLM不可用或标注失败，返回规则结果")
        return self._adapt_result(text, entities, intents, emotion, 
                                 mode="hybrid", confidence=confidence)

# 全局单例
