"""
API模块入口，聚合所有路由，供main.py统一导入
"""
from fastapi import APIRouter
from .v1.base import base_router
from .v1.intent import intent_router
from .v1.keyword import keyword_router
from .v1.rule import rule_router
from .v1.stats import stats_router
from .v1.chat import router as chat_router
from .v1.config import router as config_router
from .v1.admin.intent import router as admin_intent_router
from .v1.admin.keyword import router as admin_keyword_router
from .v1.admin.rule import router as admin_rule_router
from .v1.admin.stats import router as admin_stats_router
from .v1.admin.batch import router as admin_batch_router
from .v1.admin.test import router as admin_test_router
# 后续添加其他API模块

# 根API路由，聚合所有子路由
# 注意：子路由已包含 /api/v1/ 前缀，此处不再添加前缀
api_router = APIRouter()

# 注册各版本API路由
api_router.include_router(base_router)
api_router.include_router(intent_router)
api_router.include_router(keyword_router)
api_router.include_router(rule_router)
api_router.include_router(stats_router)
api_router.include_router(chat_router)
api_router.include_router(config_router)
api_router.include_router(admin_intent_router)
api_router.include_router(admin_keyword_router)
api_router.include_router(admin_rule_router)
api_router.include_router(admin_stats_router)
api_router.include_router(admin_batch_router)
api_router.include_router(admin_test_router)

# 对外导出聚合后的路由
__all__ = ["api_router"]