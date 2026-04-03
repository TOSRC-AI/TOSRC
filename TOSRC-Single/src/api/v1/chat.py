#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天接口（用户侧）
"""
from fastapi import APIRouter, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional
import time
import json
import os
from src.utils.logger import get_logger
from src.bootstrap.context import get_scheduler, get_db
from src.utils.route_logger import RouteLogger
from src.common.exceptions import AuthException, ValidationException
from src.common.error_codes import ErrorCode
from src.common.responses import success

# 初始化 JSONL 路由记录器
route_logger = RouteLogger(log_dir=os.getenv("ROUTE_LOG_DIR", "data/logs/routes"))

logger = get_logger()
router = APIRouter(prefix="/v1/chat", tags=["用户侧 - 聊天接口"])


class ChatRequest(BaseModel):
    """聊天请求体"""
    text: str
    context: Optional[Dict[str, Any]] = None


@router.post("", summary="聊天语义识别接口")
async def chat_process(request: ChatRequest, x_api_key: str = Header(None)):
    """
    处理用户输入文本，返回语义识别结果
    """
    # 校验API Key
    from src.config.loader import get_global_config
    global_config = get_global_config()
    ADMIN_API_KEY = global_config["admin"]["admin_api_key"]

    if not x_api_key or x_api_key != ADMIN_API_KEY:
        raise AuthException(
            error_code=ErrorCode.API_KEY_INVALID,
            detail="API Key无效"
        )

    if not request.text.strip():
        raise ValidationException(
            error_code=ErrorCode.PARAM_MISSING,
            detail="输入文本不能为空"
        )

    # 通用识别逻辑，完全从数据库读取，无任何硬编码行业数据
    text = request.text
    db = get_db()
    start_time = time.time()

    # 1. 查询所有意图信息（适配新表结构）
    intent_map = {}
    all_intents = db.execute_query(
        "SELECT intent_code, intent_name, level, parent_id, priority FROM intents WHERE is_enabled = 1")
    for intent in all_intents:
        # 字段映射兼容旧逻辑
        intent["intent_level"] = intent["level"]
        intent["parent_code"] = intent["parent_id"]
        intent_map[intent["intent_code"]] = intent

    # 2. 意图识别（基于训练好的关键词模型）
    intent_scores = {}
    # 加载意图关键词模型
    model_path = "data/models/intent_keywords.json"
    intent_model = {}
    if os.path.exists(model_path):
        with open(model_path, "r", encoding="utf-8") as f:
            intent_model = json.load(f)

    # 提取文本的2-3元组关键词
    text_kw = set()
    n = len(text)
    for i in range(n):
        if i + 1 < n and not text[i].isspace() and not text[i + 1].isspace():
            text_kw.add(text[i:i + 2])
        if i + 2 < n and not text[i].isspace() and not text[i + 1].isspace() and not text[i + 2].isspace():
            text_kw.add(text[i:i + 3])

    # 计算每个意图的匹配得分
    for intent_code, intent_data in intent_model.items():
        keywords = intent_data.get("keywords", [])
        if not keywords:
            continue
        match_count = len([kw for kw in keywords if kw in text_kw])
        score = match_count / len(keywords) * 100
        intent_scores[intent_code] = score

    # 3. 确定最高得分意图
    top_intent_code = "inform"
    confidence = 0.5
    if intent_scores:
        top_intent_code = max(intent_scores.items(), key=lambda x: x[1])[0]
        max_score = intent_scores[top_intent_code]
        confidence = round(max_score / 100, 2) if max_score > 0 else 0.5

    # 4. 实体提取（规则匹配+NER模型融合，优先保留长实体）
    entities = []
    all_candidates = []  # 存储所有候选实体，最后统一去重
    entity_type_map = {}

    # 4.1 先从数据库加载实体类型信息
    entity_types = db.execute_query("SELECT entity_code, entity_name, entity_type FROM entity_types")
    for et in entity_types:
        entity_type_map[et["entity_code"]] = et

    # 4.2 规则匹配（同时匹配实体值表和关键词表，覆盖所有导入的实体）
    # 4.2.1 先匹配entity_values表的实体值
    value_entities = db.execute_query("""
        SELECT ev.value as keyword, ev.entity_code, ev.weight
        FROM entity_values ev
        JOIN entity_types et ON ev.entity_code = et.entity_code
        WHERE ev.is_enabled = 1
    """)

    # 4.2.2 再匹配entity_keywords表的扩展关键词
    keyword_entities = db.execute_query("""
        SELECT ek.keyword, ek.entity_code, ek.weight
        FROM entity_keywords ek
        JOIN entity_types et ON ek.entity_code = et.entity_code
        WHERE ek.is_enabled = 1
    """)

    # 合并所有规则实体
    all_rule_entities = value_entities + keyword_entities

    # 先收集所有匹配到的候选实体
    for re in all_rule_entities:
        kw = re["keyword"]
        if kw in text:
            et = entity_type_map.get(re["entity_code"], {})
            start_idx = text.find(kw)
            end_idx = start_idx + len(kw)
            all_candidates.append({
                "type": et.get("entity_type", re["entity_code"]),
                "name": et.get("entity_name", re["entity_code"]),
                "text": kw,
                "value": kw,
                "entity_code": re["entity_code"],
                "source": "rule",
                "confidence": re.get("weight", 1.0),
                "start": start_idx,
                "end": end_idx
            })

    # 4.3 NER模型识别（动态加载插件，无需修改核心代码）
    try:
        from src.plugin.ner.offline_ner_plugin import OfflineNerPlugin
        ner_plugin = OfflineNerPlugin()
        if ner_plugin.initialize({}):
            ner_entities = ner_plugin.extract_entities(text)
            for ne in ner_entities:
                if ne["confidence"] >= 0.7:
                    # 尝试匹配现有实体类型
                    entity_code = f"entity_{ne['type']}"
                    et = entity_type_map.get(entity_code, {})
                    all_candidates.append({
                        "type": ne["type"],
                        "name": et.get("entity_name", ne["type"]),
                        "text": ne["value"],
                        "value": ne["value"],
                        "entity_code": entity_code,
                        "source": "ner",
                        "confidence": ne["confidence"],
                        "start": ne["start"],
                        "end": ne["end"]
                    })
            ner_plugin.destroy()
    except Exception as e:
        logger.debug(f"NER识别跳过: {str(e)}")

    # 4.4 实体去重：按长度降序排序，优先保留更长的实体，删除重叠短实体
    all_candidates.sort(key=lambda x: (-(x["end"] - x["start"])))
    used_spans = set()
    for ent in all_candidates:
        # 检查是否和已保留的实体重叠
        overlap = False
        for (s, e) in used_spans:
            if not (ent["end"] <= s or ent["start"] >= e):
                overlap = True
                break
        if not overlap:
            used_spans.add((ent["start"], ent["end"]))
            # 去掉内部字段，返回给前端
            entities.append({k: v for k, v in ent.items() if k not in ["start", "end"]})

    # 5. 构建返回意图列表
    all_intents_list = []
    top_intent = intent_map.get(top_intent_code, {
        "intent_code": "inform",
        "intent_name": "告知/陈述",
        "intent_level": 1,
        "priority": 300
    })

    # 一级意图
    all_intents_list.append({
        "intent_code": top_intent["intent_code"],
        "intent_name": top_intent["intent_name"],
        "confidence": confidence,
        "priority": top_intent["priority"],
        "level": top_intent["intent_level"]
    })

    # 二级意图（如果有父级）
    if top_intent.get("parent_code") and top_intent["parent_code"] in intent_map:
        parent_intent = intent_map[top_intent["parent_code"]]
        all_intents_list.insert(0, {
            "intent_code": parent_intent["intent_code"],
            "intent_name": parent_intent["intent_name"],
            "confidence": confidence,
            "priority": parent_intent["priority"],
            "level": parent_intent["intent_level"]
        })

    # 计算耗时
    cost_time = int((time.time() - start_time) * 1000)

    # 适配前端期望的返回格式
    result = {
        "text": text,
        "intent": {
            "all_intents": all_intents_list
        },
        "confidence": confidence,
        "entities": entities,
        "emotion": {
            "sentiment": "neutral",
            "score": 0.5,
            "name": "中性"
        },
        "cost_time": cost_time,
        "intents": [
            {
                "name": top_intent["intent_name"],
                "confidence": confidence
            }
        ],
        "business_intent": []
    }

    # 记录请求到 JSONL（高性能）和 SQLite（兼容）
    try:
        # 1. JSONL 记录（高性能，推荐）
        route_logger.save(
            text=request.text,
            intent={
                "intent_code": top_intent.get("intent_code"),
                "intent_name": top_intent.get("intent_name"),
                "intent_level": top_intent.get("intent_level")
            },
            entities=entities,
            confidence=confidence,
            mode="rule",
            latency_ms=result.get("cost_time", 0),
            user_id="anonymous",
            scene="chat",
            emotion=result.get("emotion")
        )

        # 2. SQLite 记录（向后兼容，可选）
        if os.getenv("ENABLE_SQLITE_LOG", "true").lower() == "true":
            db.execute_insert(
                """
                INSERT INTO route_records
                (text, intent_code, intent_name, entities, confidence, cost_time)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    request.text,
                    top_intent["intent_code"],
                    top_intent["intent_name"],
                    str(entities),
                    confidence,
                    result.get("cost_time", 0)
                )
            )
    except Exception as e:
        logger.warning(f"记录请求日志失败: {str(e)}")

    return success(data=result)
