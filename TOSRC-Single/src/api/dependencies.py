"""
API依赖模块，统一封装权限校验、请求拦截等公共逻辑
"""
from fastapi import Header, HTTPException
from src.config.loader import get_global_config
from src.utils.logger import logger

# 从配置模块获取配置
global_config = get_global_config()
ADMIN_API_KEY = global_config["admin"]["admin_api_key"]
ADMIN_API_KEY_HEADER = global_config["admin"]["api_key_header"]

async def verify_admin_api_key(x_admin_api_key: str = Header(None)):
    """
    管理后台API Key校验依赖
    仅在需要管理员权限的接口上添加此依赖
    """
    if not x_admin_api_key or x_admin_api_key != ADMIN_API_KEY:
        logger.warning(f"管理员API Key校验失败，请求Key：{x_admin_api_key}")
        raise HTTPException(
            status_code=401,
            detail="管理后台API Key无效，请配置正确的管理员API Key"
        )
    return True