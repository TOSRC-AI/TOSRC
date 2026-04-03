"""
关键词管理API模块，包含关键词的CRUD、权重调整等接口
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict, Any
from src.api.dependencies import verify_admin_api_key
from src.bootstrap.context import get_db
from src.utils.logger import logger

# 关键词管理API路由
keyword_router = APIRouter(tags=["关键词管理"], prefix="/api/v1/admin/keyword", dependencies=[Depends(verify_admin_api_key)])

@keyword_router.get("/list")
async def get_keyword_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    type: Optional[str] = Query(None, description="关键词类型：intent/entity/emotion"),
    relation_id: Optional[int] = Query(None, description="关联ID（意图ID/实体ID）"),
    keyword: Optional[str] = Query(None, description="搜索关键词")
):
    """获取关键词列表"""
    try:
        db = get_db()
        keywords = db.get_all_keywords(type=type, relation_id=relation_id)
        
        # 搜索过滤
        if keyword:
            keywords = [
                k for k in keywords 
                if keyword in k["keyword"]
            ]
        
        # 分页
        total = len(keywords)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_keywords = keywords[start:end]
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "list": paginated_keywords,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }
    except Exception as e:
        logger.error(f"获取关键词列表失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"获取关键词列表失败：{str(e)}",
            "data": None
        }

@keyword_router.post("/add")
async def add_keyword(keyword_data: Dict[str, Any]):
    """新增关键词"""
    try:
        db = get_db()
        keyword_id = db.add_keyword(
            keyword=keyword_data["keyword"],
            type=keyword_data["type"],
            relation_id=keyword_data["relation_id"],
            weight=keyword_data.get("weight", 1.0),
            is_enabled=keyword_data.get("is_enabled", 1),
            description=keyword_data.get("description", "")
        )
        logger.info(f"新增关键词成功：{keyword_data['keyword']}")
        return {
            "code": 0,
            "message": "新增成功",
            "data": {"keyword_id": keyword_id}
        }
    except Exception as e:
        logger.error(f"新增关键词失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"新增关键词失败：{str(e)}",
            "data": None
        }

@keyword_router.post("/update")
async def update_keyword(keyword_data: Dict[str, Any]):
    """更新关键词"""
    try:
        db = get_db()
        success = db.update_keyword(
            keyword_id=keyword_data["keyword_id"],
            keyword=keyword_data["keyword"],
            weight=keyword_data.get("weight", 1.0),
            is_enabled=keyword_data.get("is_enabled", 1),
            description=keyword_data.get("description", "")
        )
        if success:
            logger.info(f"更新关键词成功：ID={keyword_data['keyword_id']}")
            return {
                "code": 0,
                "message": "更新成功",
                "data": None
            }
        return {
            "code": 404,
            "message": "关键词不存在",
            "data": None
        }
    except Exception as e:
        logger.error(f"更新关键词失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"更新关键词失败：{str(e)}",
            "data": None
        }

@keyword_router.post("/delete/{keyword_id}")
async def delete_keyword(keyword_id: int):
    """删除关键词"""
    try:
        db = get_db()
        success = db.delete_keyword(keyword_id)
        if success:
            logger.info(f"删除关键词成功：ID={keyword_id}")
            return {
                "code": 0,
                "message": "删除成功",
                "data": None
            }
        return {
            "code": 404,
            "message": "关键词不存在",
            "data": None
        }
    except Exception as e:
        logger.error(f"删除关键词失败：{str(e)}", exc_info=True)
        return {
            "code": 500,
            "message": f"删除关键词失败：{str(e)}",
            "data": None
        }