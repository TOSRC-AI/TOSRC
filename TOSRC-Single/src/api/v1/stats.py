"""
统计分析API模块，包含系统统计、路由统计、学习统计等接口
支持JSONL路由记录查询
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from src.api.dependencies import verify_admin_api_key
from src.bootstrap.context import get_db
from src.utils.logger import logger
from src.utils.route_logger import RouteLogger
import os

# 统计分析API路由
stats_router = APIRouter(tags=["统计分析"], prefix="/api/v1/admin/stats", dependencies=[Depends(verify_admin_api_key)])

# 初始化 JSONL 路由记录器
route_logger = RouteLogger(log_dir=os.getenv("ROUTE_LOG_DIR", "data/logs/routes"))

@stats_router.get("/overview")
async def get_overview_stats():
    """获取系统概览统计"""
    try:
        db = get_db()
        
        # 获取总数统计
        total_intents = len(db.get_all_intents())
        total_entities = len(db.get_all_entities())
        total_keywords = len(db.get_all_keywords())
        total_requests = db.get_route_count()
        
        # 获取近7天统计
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)
        week_stats = db.get_stats_by_time_range(
            start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "total_intents": total_intents,
                "total_entities": total_entities,
                "total_keywords": total_keywords,
                "total_requests": total_requests,
                "week_requests": week_stats["total_requests"],
                "week_avg_confidence": round(week_stats["avg_confidence"], 2) if week_stats["avg_confidence"] else 0
            }
        }
    except Exception as e:
        logger.error(f"获取概览统计失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"获取概览统计失败：{str(e)}",
            "data": None
        }

@stats_router.get("/trend")
async def get_trend_stats(
    days: int = Query(7, ge=1, le=30, description="统计天数")
):
    """获取请求趋势统计"""
    try:
        db = get_db()
        trend_data = []
        
        end_time = datetime.now(timezone.utc)
        for i in range(days):
            current_date = end_time - timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")
            day_start = date_str + " 00:00:00"
            day_end = date_str + " 23:59:59"
            
            day_stats = db.get_stats_by_time_range(day_start, day_end)
            trend_data.append({
                "date": date_str,
                "requests": day_stats["total_requests"],
                "avg_confidence": round(day_stats["avg_confidence"], 2) if day_stats["avg_confidence"] else 0
            })
        
        # 按日期正序排列
        trend_data.reverse()
        
        return {
            "code": 0,
            "message": "success",
            "data": trend_data
        }
    except Exception as e:
        logger.error(f"获取趋势统计失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"获取趋势统计失败：{str(e)}",
            "data": None
        }

@stats_router.get("/route/records")
async def get_route_records(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取路由记录列表"""
    try:
        db = get_db()
        
        offset = (page - 1) * page_size
        records = db.get_route_records(limit=page_size, offset=offset)
        total = db.get_route_count()
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "list": records,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }
    except Exception as e:
        logger.error(f"获取路由记录失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"获取路由记录失败：{str(e)}",
            "data": None
        }


# ==================== JSONL 路由记录接口 ====================

@stats_router.get("/jsonl/routes")
async def get_jsonl_routes(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    days: int = Query(7, ge=1, le=30, description="查询近N天")
):
    """
    从 JSONL 获取路由记录（高性能版本）
    """
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)

        # 从 JSONL 查询
        records = route_logger.query(
            start_time=start_time,
            end_time=end_time,
            limit=page_size
        )

        return {
            "code": 0,
            "message": "success",
            "data": {
                "list": records,
                "page": page,
                "page_size": page_size,
                "source": "jsonl"
            }
        }
    except Exception as e:
        logger.error(f"获取JSONL路由记录失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"获取路由记录失败：{str(e)}",
            "data": None
        }


@stats_router.get("/jsonl/stats")
async def get_jsonl_stats(
    days: int = Query(7, ge=1, le=30, description="统计天数")
):
    """
    从 JSONL 获取统计分析（高性能版本）
    """
    try:
        stats = route_logger.get_stats(days=days)

        return {
            "code": 0,
            "message": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取JSONL统计失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"获取统计失败：{str(e)}",
            "data": None
        }


@stats_router.get("/jsonl/accuracy")
async def get_jsonl_accuracy(
    days: int = Query(7, ge=1, le=30, description="统计天数")
):
    """
    从 JSONL 获取意图识别准确率统计
    """
    try:
        accuracy = route_logger.get_intent_accuracy(days=days)

        return {
            "code": 0,
            "message": "success",
            "data": accuracy
        }
    except Exception as e:
        logger.error(f"获取准确率统计失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"获取准确率统计失败：{str(e)}",
            "data": None
        }


@stats_router.get("/jsonl/files")
async def get_jsonl_files():
    """
    获取日志文件统计
    """
    try:
        stats = route_logger.get_log_stats()

        return {
            "code": 0,
            "message": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取日志文件统计失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"获取日志文件统计失败：{str(e)}",
            "data": None
        }