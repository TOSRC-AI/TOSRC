#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOSRC-Single 单租户版本主入口文件
仅保留核心服务初始化逻辑，所有业务路由从API模块统一导入
适配场景：离线/内网单租户部署，无外网依赖
"""
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time

# 新的模块化导入
from src.utils.logger import logger
from src.config.loader import get_global_config
from src.bootstrap.context import get_tenant_context
from src.api import api_router
from src.api.dependencies import verify_admin_api_key
from src.middleware.exception_handler import setup_exception_handlers

# 加载全局配置
global_config = get_global_config()
ADMIN_API_KEY = global_config["admin"]["admin_api_key"]
SERVICE_HOST = global_config["service"]["host"]
SERVICE_PORT = global_config["service"]["port"]
STATIC_MAX_AGE = global_config["cache"]["static_max_age"]
HTML_MAX_AGE = global_config["cache"]["html_max_age"]

# 限流配置
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={"code": 429, "message": "请求过于频繁，请稍后再试", "data": None}
    )

# 生命周期事件处理
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """服务生命周期管理，符合FastAPI最新规范"""
    # 服务启动逻辑：提前初始化所有核心组件
    tenant_context = get_tenant_context()
    tenant_context.init()
    
    # 注入上下文到app，便于API模块调用
    app.state.tenant_context = tenant_context
    
    logger.info("✅ TOSRC-Single 单租户服务启动完成，离线模式已启用")
    logger.info(f"🚀 服务监听地址：http://{SERVICE_HOST}:{SERVICE_PORT}")
    logger.info(f"🔑 管理后台API Key：{ADMIN_API_KEY}")
    
    yield
    
    # 服务优雅关闭逻辑
    logger.info("正在关闭服务...")
    # 释放数据库连接等资源
    tenant_context = get_tenant_context()
    if hasattr(tenant_context.db, "close"):
        tenant_context.db.get_connection().close()
        logger.info("数据库连接已关闭")
    logger.info("✅ TOSRC-Single 服务已关闭")

# 初始化FastAPI应用
app = FastAPI(
    title="TOSRC-Single 语义路由调度引擎",
    description="单租户离线版本，支持本地语义识别、规则包管理、自动学习",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 管理后台认证中间件
@app.middleware("http")
async def admin_auth_middleware(request, call_next):
    """管理后台API认证，静态资源和基础接口开放"""
    # 静态资源、首页、文档不需要认证
    if request.url.path.startswith("/static") or \
       request.url.path == "/" or \
       request.url.path.startswith("/admin") or \
       request.url.path.startswith("/api/docs") or \
       request.url.path.startswith("/api/redoc") or \
       request.url.path.startswith("/api/v1/base"):
        return await call_next(request)
    
    # 管理后台API接口需要API Key认证
    if request.url.path.startswith("/api/v1/admin/"):
        api_key = request.headers.get(global_config["admin"]["api_key_header"]) or \
                  request.query_params.get("admin_api_key")
        if not api_key or api_key != ADMIN_API_KEY:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={
                    "code": 401,
                    "message": "管理后台API Key无效，请在请求头或查询参数中携带正确的API Key",
                    "data": None
                }
            )
        return await call_next(request)
    
    # 其他业务接口走API Key认证（后续完善）
    return await call_next(request)

# 静态资源缓存中间件
class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # 静态资源缓存1天
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = f"public, max-age={STATIC_MAX_AGE}"
            response.headers["Expires"] = time.strftime(
                "%a, %d %b %Y %H:%M:%S GMT", 
                time.gmtime(time.time() + STATIC_MAX_AGE)
            )
        # HTML页面缓存5分钟
        elif request.url.path.endswith(".html") or request.url.path in ["/", "/admin"]:
            response.headers["Cache-Control"] = f"public, max-age={HTML_MAX_AGE}"
        return response

app.add_middleware(CacheControlMiddleware)

# 注册限流异常处理
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 注册全局异常处理器
setup_exception_handlers(app)

# 挂载静态资源
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# 注册所有API路由（从API模块统一导入）
app.include_router(api_router)

# 首页路由（普通用户前端）
@app.get("/")
async def index():
    """首页（普通用户前端）"""
    return FileResponse("static/index.html")

# 管理后台路由（支持带/和不带/的路径）
@app.get("/admin")
@app.get("/admin/")
@app.get("/admin/{path:path}")
async def admin_page(path: str = "index.html"):
    """管理后台页面路由"""
    admin_file = Path(f"static/admin/{path}")
    if admin_file.exists() and admin_file.is_file():
        return FileResponse(f"static/admin/{path}")
    return FileResponse("static/admin/index.html")

# 健康检查路由（兼容旧版）
@app.get("/health")
async def health_check_legacy():
    """健康检查接口（兼容旧版路径）"""
    from src.api.v1.base import health_check
    return await health_check(request=None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        reload=False,
        workers=1,
        access_log=False
    )