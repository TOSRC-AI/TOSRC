#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置接口
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Dict, Any
from src.utils.logger import get_logger
from src.bootstrap.context import get_db

logger = get_logger()
router = APIRouter(prefix="/v1/config", tags=["配置接口"])

@router.get("/intent_dict", summary="获取意图字典")
async def get_intent_dict(x_api_key: str = Header(None)):
    """
    获取所有意图的字典映射，供前端使用
    """
    try:
        # 校验API Key
        from src.config.loader import get_global_config
        global_config = get_global_config()
        ADMIN_API_KEY = global_config["admin"]["admin_api_key"]
        
        if not x_api_key or x_api_key != ADMIN_API_KEY:
            raise HTTPException(status_code=401, detail="API Key无效")
        
        db = get_db()
        intents = db.execute_query("SELECT intent_code, intent_name, parent_code, intent_level as level, priority FROM intent_dict")
        
        intent_dict = {}
        for intent in intents:
            intent_dict[intent["intent_code"]] = {
                "intent_code": intent["intent_code"],
                "intent_name": intent["intent_name"],
                "parent_code": intent["parent_code"],
                "level": intent["level"],
                "priority": intent["priority"]
            }
        
        return {
            "code": 200,
            "message": "success",
            "data": intent_dict
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"获取意图字典失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")