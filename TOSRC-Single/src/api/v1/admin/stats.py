#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员接口 - 统计分析
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.utils.logger import get_logger
from src.api.dependencies import verify_admin_api_key
from src.bootstrap.context import get_db
from datetime import datetime, timedelta
import json

logger = get_logger()
router = APIRouter(prefix="/v1/admin/stats", tags=["管理员接口 - 统计分析"])

@router.get("/overview", summary="获取统计概览")
async def get_stats_overview(api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    获取统计概览数据：总请求数、识别准确率、平均响应时间等
    """
    try:
        db = get_db()
        
        # 总请求数
        total_result = db.execute_query("SELECT COUNT(*) as total FROM route_records")
        total_requests = total_result[0]["total"] if total_result else 0
        
        # 高置信度请求（置信度>=0.8视为识别成功）
        success_result = db.execute_query("SELECT COUNT(*) as count FROM route_records WHERE confidence >= 0.8")
        success_count = success_result[0]["count"] if success_result else 0
        accuracy = round(success_count / total_requests * 100, 2) if total_requests > 0 else 0
        
        # 今日请求数
        today = datetime.now().strftime("%Y-%m-%d")
        today_result = db.execute_query(
            "SELECT COUNT(*) as count FROM route_records WHERE create_time >= ?",
            (f"{today} 00:00:00",)
        )
        today_requests = today_result[0]["count"] if today_result else 0
        
        # Top 5 意图
        top_intents_result = db.execute_query("""
            SELECT intent_name, COUNT(*) as count 
            FROM route_records 
            WHERE intent_name IS NOT NULL AND intent_name != ''
            GROUP BY intent_name 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_intents = []
        for item in top_intents_result:
            top_intents.append({
                "intent_name": item["intent_name"],
                "count": item["count"],
                "ratio": round(item["count"] / total_requests * 100, 2) if total_requests > 0 else 0
            })
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "total_requests": total_requests,
                "today_requests": today_requests,
                "accuracy": accuracy,
                "avg_response_time": 85,  # 后续接入真实统计
                "top_intents": top_intents
            }
        }
        
    except Exception as e:
        logger.error(f"获取统计概览失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@router.get("/trend", summary="获取请求趋势统计")
async def get_request_trend(days: int = 7, api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    获取最近N天的请求趋势数据
    :param days: 统计天数，默认7天
    """
    try:
        db = get_db()
        result = []
        
        # 生成最近N天的日期
        for i in range(days-1, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            # 查询当日请求数
            count_result = db.execute_query(
                "SELECT COUNT(*) as count FROM route_records WHERE create_time LIKE ?",
                (f"{date}%",)
            )
            count = count_result[0]["count"] if count_result else 0
            
            # 查询当日准确率
            success_result = db.execute_query(
                "SELECT COUNT(*) as count FROM route_records WHERE create_time LIKE ? AND confidence >= 0.8",
                (f"{date}%",)
            )
            success_count = success_result[0]["count"] if success_result else 0
            accuracy = round(success_count / count * 100, 2) if count > 0 else 0
            
            result.append({
                "date": date,
                "request_count": count,
                "accuracy": accuracy
            })
        
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"获取请求趋势失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@router.get("/intent/distribution", summary="获取意图分布统计")
async def get_intent_distribution(api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    获取所有意图的请求分布数据
    """
    try:
        db = get_db()
        
        # 查询所有意图请求量
        intent_result = db.execute_query("""
            SELECT intent_code, intent_name, COUNT(*) as count 
            FROM route_records 
            WHERE intent_code IS NOT NULL AND intent_code != ''
            GROUP BY intent_code, intent_name 
            ORDER BY count DESC
        """)
        
        # 计算总请求数
        total_result = db.execute_query("SELECT COUNT(*) as total FROM route_records WHERE intent_code IS NOT NULL AND intent_code != ''")
        total = total_result[0]["total"] if total_result else 0
        
        result = []
        for item in intent_result:
            result.append({
                "intent_code": item["intent_code"],
                "intent_name": item["intent_name"],
                "count": item["count"],
                "ratio": round(item["count"] / total * 100, 2) if total > 0 else 0
            })
        
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"获取意图分布失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@router.get("/error/list", summary="获取识别错误列表")
async def get_error_list(page: int = 1, page_size: int = 20, api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    获取识别错误的请求列表（置信度<0.8的请求）
    """
    try:
        db = get_db()
        
        # 计算总数
        count_result = db.execute_query("SELECT COUNT(*) as count FROM route_records WHERE confidence < 0.8")
        total = count_result[0]["count"] if count_result else 0
        
        # 查询分页数据
        offset = (page - 1) * page_size
        list_result = db.execute_query("""
            SELECT record_id, text, intent_name, confidence, entities, create_time
            FROM route_records 
            WHERE confidence < 0.8
            ORDER BY create_time DESC
            LIMIT ? OFFSET ?
        """, (page_size, offset))
        
        result = []
        for item in list_result:
            try:
                entities = json.loads(item["entities"]) if item["entities"] else []
            except:
                entities = []
            
            result.append({
                "record_id": item["record_id"],
                "text": item["text"],
                "intent_name": item["intent_name"],
                "confidence": item["confidence"],
                "entities": entities,
                "create_time": item["create_time"]
            })
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "list": result,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }
        
    except Exception as e:
        logger.error(f"获取错误列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")