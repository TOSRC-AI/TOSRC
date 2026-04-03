#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试接口（管理后台）
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from src.utils.logger import get_logger
from src.api.dependencies import verify_admin_api_key
from src.bootstrap.context import get_scheduler

logger = get_logger()
router = APIRouter(prefix="/v1/admin/test", tags=["管理员接口 - 在线测试"])

class TestRequest(BaseModel):
    """测试请求体"""
    text: str

@router.post("", summary="在线测试接口")
async def online_test(request: TestRequest, api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    管理后台在线测试语义识别效果
    """
    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="输入文本不能为空")
        
        # 临时简化实现，先让接口通，后续完善核心识别逻辑
        text = request.text
        
        # 简单关键词匹配测试
        intent = "inform"
        intent_name = "告知/陈述"
        confidence = 0.85
        entities = {}
        
        if "要租" in text or "帮我找" in text or "预约" in text:
            intent = "request"
            intent_name = "请求/指令"
            confidence = 0.95
        elif "?" in text or "怎么" in text or "什么" in text:
            intent = "question"
            intent_name = "咨询/疑问"
            confidence = 0.9
        elif "感谢" in text or "谢谢" in text or "太好了" in text or "满意" in text:
            intent = "emotion"
            intent_name = "情绪/态度"
            confidence = 0.9
        elif "你好" in text or "再见" in text or "您好" in text:
            intent = "social"
            intent_name = "社交/礼仪"
            confidence = 0.95
        
        result = {
            "text": text,
            "intent": {
                "intent_code": intent,
                "intent_name": intent_name,
                "confidence": confidence
            },
            "entities": entities,
            "emotion": {
                "sentiment": "neutral",
                "score": 0.5
            },
            "confidence": confidence,
            "cost_time": 50
        }
        
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"在线测试失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")