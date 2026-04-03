#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局配置文件
统一管理所有全局配置和初始化的组件
"""
from pathlib import Path
from src.rule_engine import RuleEngine
from src.scene_intent_recognizer import get_intent_recognizer
from src.router_decision import RouterDecisionEngine
from ...common.utils.logger import get_logger

logger = get_logger()

# 配置运行模式
# True = 混合模式（规则+模型兜底），False = 纯规则模式（仅用规则，不加载模型）
ENABLE_MODEL_ENGINE = False  # 目前设置为纯规则模式，需要模型兜底时改为True

# 缓存配置
ENABLE_REQUEST_CACHE = True  # 是否开启高频请求缓存
CACHE_MAX_SIZE = 10000  # 最大缓存条目数，增大到10000条，覆盖更多高频请求
CACHE_TTL = 600  # 缓存过期时间（秒），延长到10分钟，减少重复计算

# 仿生架构配置
ENABLE_BIONIC_ARCH = True  # 全局仿生架构开关，默认关闭，不影响现有业务
ENABLE_BIONIC_MULTI_INTENT = False  # 是否开启多意图识别，默认关闭
# 仿生架构缓存配置，默认使用内存缓存，高性能无依赖
ENABLE_BIONIC_CACHE = False  # 关闭Redis缓存，使用内置内存缓存，无外部依赖性能更高
BIONIC_REDIS_CONFIG = {
    "host": "127.0.0.1",
    "port": 6379,
    "db": 0,
    "password": None
}

# 全局初始化组件
try:
    # 初始化规则引擎，完全从数据库加载规则，无任何硬编码
    rule_engine = RuleEngine()
    from src.metrics import set_loaded_rules_count, set_component_health
    set_loaded_rules_count(len(rule_engine.rules))
    set_component_health("rule_engine", True)
    logger.info(f"规则引擎初始化成功，加载规则数：{len(rule_engine.rules)}")
except Exception as e:
    from src.metrics import set_component_health
    set_component_health("rule_engine", False)
    logger.error(f"规则引擎初始化失败：{str(e)}")
    raise

# 初始化场景化识别器
intent_recognizer = get_intent_recognizer()
# 全局设置仿生架构开关
intent_recognizer.enable_bionic = ENABLE_BIONIC_ARCH
intent_recognizer.bionic_multi_intent = ENABLE_BIONIC_MULTI_INTENT

# 初始化路由决策引擎
router_decision_engine = RouterDecisionEngine()
# 加载路由配置：路由规则全部存储在数据库中，无需硬编码
# 仅配置默认路由，业务路由从数据库动态加载
router_decision_engine.load_route_config({
    "default_route": "通用大模型服务",
    "routes": {}
})

# 初始化仿生架构缓存
if ENABLE_BIONIC_ARCH and ENABLE_BIONIC_CACHE:
    from src.bionic.cache import bionic_cache
    bionic_cache.enable(**BIONIC_REDIS_CONFIG)

model_available = ENABLE_MODEL_ENGINE
if ENABLE_MODEL_ENGINE:
    try:
        from src.model_engine import intent_model, entity_model
        from src.metrics import set_component_health
        set_component_health("model_engine", True)
        logger.info("模型引擎初始化成功，运行模式：混合模式（规则+模型兜底）")
    except Exception as e:
        model_available = False
        from src.metrics import set_component_health
        set_component_health("model_engine", False)
        logger.warning(f"模型引擎初始化失败，已降级为纯规则模式：{str(e)}")
else:
    from src.metrics import set_component_health
    set_component_health("model_engine", False)
    logger.info("运行模式：纯规则模式，已禁用模型引擎")
