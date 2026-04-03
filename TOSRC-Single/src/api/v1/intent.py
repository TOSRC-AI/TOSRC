"""
意图管理API模块，包含意图的CRUD、权重调整等接口
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, Dict, Any
from src.api.dependencies import verify_admin_api_key
from src.bootstrap.context import get_db
from src.utils.logger import logger
from src.common.exceptions import NotFoundException, DuplicateException, BusinessException
from src.common.error_codes import ErrorCode
from src.common.responses import success, error

# 意图管理API路由
intent_router = APIRouter(tags=["意图管理"], prefix="/api/v1/admin/intent", dependencies=[Depends(verify_admin_api_key)])


@intent_router.get("/list")
async def get_intent_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词")
):
    """获取意图列表（树形结构）"""
    db = get_db()
    intents = db.get_all_intents()

    # 搜索过滤
    if keyword:
        intents = [
            i for i in intents
            if keyword in i["intent_name"] or keyword in i["intent_code"]
        ]

    # 构造树形结构
    intent_map = {}
    root_intents = []

    # 先创建所有节点的映射
    for intent in intents:
        intent_data = {
            "intent_id": intent["intent_id"],
            "intent_code": intent["intent_code"],
            "intent_name": intent["intent_name"],
            "parent_id": intent["parent_id"],
            "level": intent["level"],
            "priority": intent["priority"],
            "is_enabled": intent["is_enabled"] == 1,
            "description": intent["description"],
            "children": []
        }
        intent_map[intent["intent_id"]] = intent_data

    # 组装树形结构
    for intent_id, intent_data in intent_map.items():
        parent_id = intent_data["parent_id"]
        if parent_id == 0:
            root_intents.append(intent_data)
        else:
            if parent_id in intent_map:
                intent_map[parent_id]["children"].append(intent_data)

    return success(data=root_intents)


@intent_router.post("/add")
async def add_intent(intent_data: Dict[str, Any]):
    """新增意图"""
    db = get_db()

    # 检查意图代码是否已存在
    existing = db.execute_query(
        "SELECT intent_id FROM intents WHERE intent_code = ?",
        (intent_data["intent_code"],)
    )
    if existing:
        raise DuplicateException(resource="意图", key=intent_data["intent_code"])

    intent_id = db.add_intent(
        intent_code=intent_data["intent_code"],
        intent_name=intent_data["intent_name"],
        parent_id=intent_data.get("parent_id", 0),
        level=intent_data.get("level", 1),
        priority=intent_data.get("priority", 1),
        is_enabled=1 if intent_data.get("is_enabled", True) else 0,
        description=intent_data.get("description", "")
    )
    logger.info(f"新增意图成功：{intent_data['intent_name']}，ID={intent_id}")
    return success(data={"intent_id": intent_id}, message="新增成功")


@intent_router.post("/update")
async def update_intent(intent_data: Dict[str, Any]):
    """更新意图"""
    db = get_db()

    # 检查意图是否存在
    existing = db.get_intent_by_id(intent_data["intent_id"])
    if not existing:
        raise NotFoundException(resource="意图", resource_id=intent_data["intent_id"])

    success_update = db.update_intent(
        intent_id=intent_data["intent_id"],
        intent_code=intent_data.get("intent_code"),
        intent_name=intent_data.get("intent_name"),
        parent_id=intent_data.get("parent_id"),
        level=intent_data.get("level"),
        priority=intent_data.get("priority"),
        is_enabled=1 if intent_data.get("is_enabled") else 0 if "is_enabled" in intent_data else None,
        description=intent_data.get("description")
    )

    if success_update:
        logger.info(f"更新意图成功：ID={intent_data['intent_id']}")
        return success(message="更新成功")

    raise BusinessException(
        error_code=ErrorCode.INTENT_NOT_FOUND,
        detail="意图不存在或更新失败"
    )


@intent_router.post("/delete/{intent_id}")
async def delete_intent(intent_id: int):
    """删除意图"""
    db = get_db()

    # 检查意图是否存在
    existing = db.get_intent_by_id(intent_id)
    if not existing:
        raise NotFoundException(resource="意图", resource_id=intent_id)

    success_delete = db.delete_intent(intent_id)
    if success_delete:
        logger.info(f"删除意图成功：ID={intent_id}")
        return success(message="删除成功")

    raise BusinessException(
        error_code=ErrorCode.INTENT_NOT_FOUND,
        detail="意图不存在或删除失败"
    )
