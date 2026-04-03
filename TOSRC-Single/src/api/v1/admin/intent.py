#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员接口 - 意图管理
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.utils.logger import get_logger
from src.api.dependencies import verify_admin_api_key
from src.bootstrap.context import get_db

logger = get_logger()
router = APIRouter(prefix="/v1/admin/intent", tags=["管理员接口 - 意图管理"])

@router.get("/list", summary="获取意图树形列表")
async def get_intent_list(keyword: Optional[str] = None, api_key_auth: bool = Depends(verify_admin_api_key)):
    """
    获取完整意图树形列表，支持关键词搜索
    :param keyword: 搜索关键词（匹配意图名称/编码）
    """
    try:
        db = get_db()
        
        # 构建查询条件
        params = []
        where_conditions = []
        
        if keyword:
            where_conditions.append("(intent_name LIKE ? OR intent_code LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        where_sql = ""
        if where_conditions:
            where_sql = "WHERE " + " AND ".join(where_conditions)
        
        # 查询所有意图数据
        list_sql = f'''
        SELECT 
            intent_code, 
            intent_name, 
            intent_level as level, 
            parent_code, 
            priority, 
            is_active as is_enabled, 
            is_builtin,
            description
        FROM intent_dict 
        {where_sql}
        ORDER BY priority ASC
        '''
        intents = db.execute_query(list_sql, params)
        
        # 先转成字典列表
        intent_list = []
        intent_map = {}
        for index, intent in enumerate(intents):
            intent_item = {
                "intent_id": index + 1,
                "intent_code": intent["intent_code"],
                "intent_name": intent["intent_name"],
                "level": intent["level"],
                "parent_id": 0,
                "parent_code": intent["parent_code"],
                "priority": intent["priority"],
                "is_enabled": intent["is_enabled"],
                "is_builtin": intent["is_builtin"],
                "description": intent["description"],
                "children": []
            }
            intent_map[intent["intent_code"]] = intent_item
            intent_list.append(intent_item)
        
        # 构建树形结构
        root_intents = []
        for intent in intent_list:
            parent_code = intent.get("parent_code", "")
            if not parent_code or parent_code.strip() == "" or parent_code not in intent_map:
                root_intents.append(intent)
            else:
                intent_map[parent_code]["children"].append(intent)
                intent["parent_id"] = intent_map[parent_code]["intent_id"]
        
        return {
            "code": 0,
            "message": "success",
            "data": root_intents
        }
        
    except Exception as e:
        logger.error(f"获取意图列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

class IntentCreateRequest(BaseModel):
    """创建意图请求体"""
    intent_code: str
    intent_name: str
    level: int
    parent_code: Optional[str] = None
    priority: int = 999
    is_enabled: int = 1
    description: Optional[str] = ""

@router.post("/add", summary="新增意图")
async def add_intent(request: IntentCreateRequest, api_key_auth: bool = Depends(verify_admin_api_key)):
    """新增自定义意图（内置意图禁止添加）"""
    try:
        db = get_db()
        
        # 检查是否已存在
        existing = db.execute_query(
            "SELECT intent_code FROM intent_dict WHERE intent_code = ?",
            (request.intent_code,)
        )
        if existing:
            raise HTTPException(status_code=400, detail="意图编码已存在")
        
        # 插入新意图（自定义意图is_builtin=0）
        db.execute_insert(
            """
            INSERT INTO intent_dict 
            (intent_code, intent_name, intent_level, parent_code, priority, is_active, description, is_builtin)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                request.intent_code,
                request.intent_name,
                request.level,
                request.parent_code,
                request.priority,
                request.is_enabled,
                request.description
            )
        )
        
        logger.info(f"新增意图成功: {request.intent_code} - {request.intent_name}")
        return {
            "code": 0,
            "message": "新增成功"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"新增意图失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"新增失败: {str(e)}")

class IntentUpdateRequest(BaseModel):
    """更新意图请求体"""
    intent_name: Optional[str] = None
    level: Optional[int] = None
    parent_code: Optional[str] = None
    priority: Optional[int] = None
    is_enabled: Optional[int] = None
    description: Optional[str] = ""

@router.post("/update/{intent_code}", summary="更新意图信息")
@router.post("/update", summary="更新意图信息（兼容前端）")
async def update_intent(intent_code: str = None, request: IntentUpdateRequest = None, api_key_auth: bool = Depends(verify_admin_api_key)):
    # 兼容前端传intent_id的情况
    if intent_code is None and request and hasattr(request, 'intent_code'):
        intent_code = request.intent_code
    if intent_code is None and request and hasattr(request, 'intent_id'):
        # 根据intent_id查询intent_code
        db = get_db()
        result = db.execute_query(
            "SELECT intent_code FROM intent_dict WHERE rowid = ?",
            (request.intent_id,)
        )
        if not result:
            raise HTTPException(status_code=404, detail="意图不存在")
        intent_code = result[0]['intent_code']
    """更新意图信息"""
    try:
        db = get_db()
        
        # 查询是否为内置意图
        existing = db.execute_query(
            "SELECT is_builtin FROM intent_dict WHERE intent_code = ?",
            (intent_code,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="意图不存在")
        
        if existing[0]['is_builtin'] == 1:
            raise HTTPException(status_code=403, detail="内置通用意图不允许修改")
        
        # 构建更新SQL
        update_fields = []
        params = []
        
        if request.intent_name is not None:
            update_fields.append("intent_name = ?")
            params.append(request.intent_name)
        if request.level is not None:
            update_fields.append("intent_level = ?")
            params.append(request.level)
        if request.parent_code is not None:
            update_fields.append("parent_code = ?")
            params.append(request.parent_code)
        if request.priority is not None:
            update_fields.append("priority = ?")
            params.append(request.priority)
        if request.is_enabled is not None:
            update_fields.append("is_active = ?")
            params.append(request.is_enabled)
        if request.description is not None:
            update_fields.append("description = ?")
            params.append(request.description)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="没有需要更新的字段")
        
        params.append(intent_code)
        sql = f"UPDATE intent_dict SET {', '.join(update_fields)} WHERE intent_code = ?"
        
        success = db.execute_update(sql, params)
        if not success:
            raise HTTPException(status_code=404, detail="更新失败，意图不存在")
        
        logger.info(f"更新意图成功: {intent_code}")
        return {
            "code": 0,
            "message": "更新成功"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"更新意图失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@router.post("/delete/{intent_code}", summary="删除意图")
@router.post("/delete", summary="删除意图（兼容前端）")
async def delete_intent(intent_code: str = None, api_key_auth: bool = Depends(verify_admin_api_key), intent_id: int = None, request: dict = None):
    # 兼容前端传intent_id的情况
    if intent_code is None:
        if intent_id is None and request and 'intent_id' in request:
            intent_id = request['intent_id']
        if intent_id is None:
            raise HTTPException(status_code=400, detail="参数错误：intent_code或intent_id不能为空")
        
        # 根据intent_id查询intent_code
        db = get_db()
        result = db.execute_query(
            "SELECT intent_code FROM intent_dict WHERE rowid = ?",
            (intent_id,)
        )
        if not result:
            raise HTTPException(status_code=404, detail="意图不存在")
        intent_code = result[0]['intent_code']
    """删除指定意图（内置意图禁止删除）"""
    try:
        db = get_db()
        
        # 查询是否为内置意图
        existing = db.execute_query(
            "SELECT is_builtin FROM intent_dict WHERE intent_code = ?",
            (intent_code,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="意图不存在")
        
        if existing[0]['is_builtin'] == 1:
            raise HTTPException(status_code=403, detail="内置通用意图不允许删除")
        
        # 检查是否有子级意图
        children = db.execute_query(
            "SELECT intent_code FROM intent_dict WHERE parent_code = ?",
            (intent_code,)
        )
        if children:
            raise HTTPException(status_code=400, detail="该意图下存在子级意图，请先删除子级意图")
        
        # 执行删除
        success = db.execute_update(
            "DELETE FROM intent_dict WHERE intent_code = ?",
            (intent_code,)
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="删除失败，意图不存在")
        
        logger.info(f"删除意图成功: {intent_code}")
        return {
            "code": 0,
            "message": "删除成功"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"删除意图失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")