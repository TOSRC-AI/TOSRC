"""
基础API模块，包含健康检查、版本查询等通用接口
"""
from fastapi import APIRouter, Request
from datetime import datetime, timezone
from src.bootstrap.context import get_tenant_context
from src.utils.logger import logger

# 基础API路由
base_router = APIRouter(tags=["基础接口"], prefix="/api/v1/base")

@base_router.get("/health")
async def health_check(request: Request):
    """服务健康检查接口"""
    tenant_context = get_tenant_context()
    
    # 数据库连接检查
    db_healthy = True
    try:
        conn = tenant_context.db.get_connection()
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        logger.error(f"数据库健康检查失败：{str(e)}")
        db_healthy = False
    
    # 规则包管理器检查
    rule_healthy = True if tenant_context.rule_package_manager else False
    
    # 调度器检查
    scheduler_healthy = True if tenant_context.scheduler else False
    
    status = "healthy" if all([db_healthy, rule_healthy, scheduler_healthy]) else "unhealthy"
    logger.info(f"健康检查：服务状态={status}")
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "version": "1.0.0",
            "components": {
                "database": db_healthy,
                "rule_engine": rule_healthy,
                "scheduler": scheduler_healthy
            }
        }
    }

@base_router.get("/version")
async def get_version():
    """获取服务版本信息"""
    return {
        "code": 0,
        "message": "success",
        "data": {
            "version": "1.0.0",
            "product": "TOSRC-Single",
            "type": "单租户离线版",
            "features": ["离线语义识别", "规则包管理", "自动学习"]
        }
    }