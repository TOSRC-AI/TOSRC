#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员接口 - 关键词管理
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.utils.logger import get_logger
from src.api.dependencies import verify_admin_api_key
from src.bootstrap.context import get_db

logger = get_logger()
router = APIRouter(prefix="/v1/admin/keyword", tags=["管理员接口 - 关键词管理"])

class KeywordCreateRequest(BaseModel):
    """创建关键词请求体"""
    keyword: str
    intent_code: str
    weight: int = 1
    is_enabled: int = 1
    description: Optional[str] = ""

@router.get("/list", summary="获取关键词列表")
async def get_keyword_list(page: int = 1, page_size: int = 20, intent_code: Optional[str] = None, keyword: Optional[str] = None, api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    获取关键词列表，支持分页和筛选
    """
    try:
        db = get_db()
        
        # 构建查询条件
        params = []
        where_conditions = []
        
        if intent_code:
            where_conditions.append("intent_code = ?")
            params.append(intent_code)
        
        if keyword:
            where_conditions.append("keyword LIKE ?")
            params.append(f"%{keyword}%")
        
        where_sql = ""
        if where_conditions:
            where_sql = "WHERE " + " AND ".join(where_conditions)
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as count FROM keyword_dict {where_sql}"
        count_result = db.execute_query(count_sql, params)
        total = count_result[0]['count'] if count_result else 0
        
        # 查询分页数据
        offset = (page - 1) * page_size
        list_sql = f"""
        SELECT 
            keyword_code,
            keyword,
            intent_code,
            weight,
            is_active as is_enabled,
            description,
            is_builtin,
            create_time,
            update_time
        FROM keyword_dict 
        {where_sql}
        ORDER BY weight DESC, create_time DESC
        LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        keywords = db.execute_query(list_sql, params)
        
        # 格式化返回
        result = []
        for kw in keywords:
            result.append({
                "keyword_id": kw["keyword_code"],
                "keyword": kw["keyword"],
                "intent_code": kw["intent_code"],
                "weight": kw["weight"],
                "is_enabled": kw["is_enabled"],
                "is_builtin": kw["is_builtin"],
                "description": kw["description"],
                "create_time": kw["create_time"],
                "update_time": kw["update_time"]
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
        logger.error(f"获取关键词列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@router.post("/add", summary="新增关键词")
async def add_keyword(request: KeywordCreateRequest, api_key_auth: bool = Depends(verify_admin_api_key)):
    """新增自定义关键词"""
    try:
        db = get_db()
        
        # 检查关键词是否已存在
        existing = db.execute_query(
            "SELECT keyword FROM keyword_dict WHERE keyword = ?",
            (request.keyword,)
        )
        if existing:
            raise HTTPException(status_code=400, detail="关键词已存在")
        
        # 检查关联意图是否存在
        intent_exist = db.execute_query(
            "SELECT intent_code FROM intent_dict WHERE intent_code = ?",
            (request.intent_code,)
        )
        if not intent_exist:
            raise HTTPException(status_code=400, detail="关联的意图不存在")
        
        # 生成关键词编码
        keyword_code = f"kw_{request.keyword}_{request.intent_code}".replace(" ", "_").lower()
        
        # 插入关键词
        db.execute_insert(
            """
            INSERT INTO keyword_dict 
            (keyword_code, keyword, intent_code, weight, is_active, description, is_builtin)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                keyword_code,
                request.keyword,
                request.intent_code,
                request.weight,
                request.is_enabled,
                request.description
            )
        )
        
        logger.info(f"新增关键词成功: {request.keyword} -> {request.intent_code}")
        return {
            "code": 0,
            "message": "新增成功"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"新增关键词失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"新增失败: {str(e)}")

class KeywordUpdateRequest(BaseModel):
    """更新关键词请求体"""
    intent_code: Optional[str] = None
    weight: Optional[int] = None
    is_enabled: Optional[int] = None
    description: Optional[str] = ""

@router.post("/update/{keyword_code}", summary="更新关键词信息")
@router.post("/update", summary="更新关键词信息（兼容前端）")
async def update_keyword(keyword_code: str = None, request: KeywordUpdateRequest = None, api_key_auth: bool = Depends(verify_admin_api_key)):
    # 兼容前端传keyword_id的情况
    if keyword_code is None and request and hasattr(request, 'keyword_code'):
        keyword_code = request.keyword_code
    if keyword_code is None and request and hasattr(request, 'keyword_id'):
        # 兼容旧版keyword_id（实际就是keyword_code）
        keyword_code = request.keyword_id
    
    if keyword_code is None:
        raise HTTPException(status_code=400, detail="参数错误：keyword_code或keyword_id不能为空")
    """更新关键词信息"""
    try:
        db = get_db()
        
        # 查询是否为内置关键词
        existing = db.execute_query(
            "SELECT is_builtin FROM keyword_dict WHERE keyword_code = ?",
            (keyword_code,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="关键词不存在")
        
        if existing[0]['is_builtin'] == 1:
            raise HTTPException(status_code=403, detail="内置关键词不允许修改")
        
        # 检查关联意图是否存在
        if request.intent_code:
            intent_exist = db.execute_query(
                "SELECT intent_code FROM intent_dict WHERE intent_code = ?",
                (request.intent_code,)
            )
            if not intent_exist:
                raise HTTPException(status_code=400, detail="关联的意图不存在")
        
        # 构建更新SQL
        update_fields = []
        params = []
        
        if request.intent_code is not None:
            update_fields.append("intent_code = ?")
            params.append(request.intent_code)
        if request.weight is not None:
            update_fields.append("weight = ?")
            params.append(request.weight)
        if request.is_enabled is not None:
            update_fields.append("is_active = ?")
            params.append(request.is_enabled)
        if request.description is not None:
            update_fields.append("description = ?")
            params.append(request.description)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="没有需要更新的字段")
        
        update_fields.append("update_time = CURRENT_TIMESTAMP")
        params.append(keyword_code)
        
        sql = f"UPDATE keyword_dict SET {', '.join(update_fields)} WHERE keyword_code = ?"
        success = db.execute_update(sql, params)
        
        if not success:
            raise HTTPException(status_code=404, detail="更新失败，关键词不存在")
        
        logger.info(f"更新关键词成功: {keyword_code}")
        return {
            "code": 0,
            "message": "更新成功"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"更新关键词失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@router.post("/delete/{keyword_code}", summary="删除关键词")
@router.post("/delete", summary="删除关键词（兼容前端）")
async def delete_keyword(keyword_code: str = None, api_key_auth: bool = Depends(verify_admin_api_key), keyword_id: str = None, request: dict = None):
    # 兼容前端传keyword_id的情况
    if keyword_code is None:
        if keyword_id is None and request and 'keyword_id' in request:
            keyword_id = request['keyword_id']
        if keyword_id is None:
            raise HTTPException(status_code=400, detail="参数错误：keyword_code或keyword_id不能为空")
        
        keyword_code = keyword_id
    """删除指定关键词"""
    try:
        db = get_db()
        
        # 查询是否为内置关键词
        existing = db.execute_query(
            "SELECT is_builtin FROM keyword_dict WHERE keyword_code = ?",
            (keyword_code,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="关键词不存在")
        
        if existing[0]['is_builtin'] == 1:
            raise HTTPException(status_code=403, detail="内置关键词不允许删除")
        
        # 执行删除
        success = db.execute_update(
            "DELETE FROM keyword_dict WHERE keyword_code = ?",
            (keyword_code,)
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="删除失败，关键词不存在")
        
        logger.info(f"删除关键词成功: {keyword_code}")
        return {
            "code": 0,
            "message": "删除成功"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"删除关键词失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")