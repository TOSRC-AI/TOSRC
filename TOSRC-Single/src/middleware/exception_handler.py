# -*- coding: utf-8 -*-
"""
全局异常处理中间件

统一处理应用中的所有异常，转换为标准响应格式
"""
import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded

from src.common.exceptions import TOSRCException
from src.common.error_codes import ErrorCode
from src.common.responses import error, get_http_status

logger = logging.getLogger(__name__)


class ExceptionHandlerMiddleware:
    """
    全局异常处理中间件

    捕获所有未处理的异常，转换为标准错误响应
    """

    async def __call__(self, request: Request, call_next):
        """中间件入口"""
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self.handle_exception(request, exc)

    async def handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """处理异常并生成响应"""

        # TOSRC 业务异常
        if isinstance(exc, TOSRCException):
            return self._handle_tosrc_exception(exc)

        # FastAPI 请求校验异常
        if isinstance(exc, RequestValidationError):
            return self._handle_validation_error(exc)

        # 限流异常
        if isinstance(exc, RateLimitExceeded):
            return self._handle_rate_limit_error(exc)

        # SQLite 特定错误
        if hasattr(exc, '__class__') and 'sqlite3' in exc.__class__.__module__:
            return self._handle_sqlite_error(exc)

        # 其他未知异常
        return self._handle_unknown_error(request, exc)

    def _handle_tosrc_exception(self, exc: TOSRCException) -> JSONResponse:
        """处理业务异常"""
        logger.warning(
            f"业务异常 [{exc.error_code.code}]: {exc.detail}",
            extra={"error_code": exc.error_code.code, "detail": exc.detail}
        )

        status_code = get_http_status(exc.error_code.code)
        return JSONResponse(
            status_code=status_code,
            content=error(
                error_code=exc.error_code,
                detail=exc.detail,
                data=exc.data
            )
        )

    def _handle_validation_error(self, exc: RequestValidationError) -> JSONResponse:
        """处理参数校验异常"""
        errors = exc.errors()
        # 提取第一个错误信息
        first_error = errors[0] if errors else {}
        field = ".".join(str(x) for x in first_error.get("loc", []))
        msg = first_error.get("msg", "参数格式错误")

        detail = f"字段[{field}] {msg}" if field else msg

        logger.warning(f"参数校验错误: {detail}", extra={"errors": errors})

        return JSONResponse(
            status_code=400,
            content=error(
                error_code=ErrorCode.PARAM_INVALID,
                detail=detail,
                data={"errors": errors} if len(errors) > 1 else None
            )
        )

    def _handle_rate_limit_error(self, exc: RateLimitExceeded) -> JSONResponse:
        """处理限流异常"""
        logger.warning(f"请求限流: {str(exc)}")

        return JSONResponse(
            status_code=429,
            content=error(
                error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                detail="请求过于频繁，请稍后再试"
            )
        )

    def _handle_sqlite_error(self, exc: Exception) -> JSONResponse:
        """处理SQLite特定错误"""
        error_msg = str(exc).lower()

        # 唯一约束冲突
        if "unique" in error_msg or "constraint" in error_msg:
            logger.warning(f"SQLite唯一约束冲突: {str(exc)}")
            return JSONResponse(
                status_code=409,
                content=error(
                    error_code=ErrorCode.DB_DUPLICATE_KEY,
                    detail="数据重复，请检查唯一性约束"
                )
            )

        # 数据库锁定（并发问题）
        if "locked" in error_msg or "busy" in error_msg:
            logger.error(f"SQLite数据库锁定: {str(exc)}")
            return JSONResponse(
                status_code=503,
                content=error(
                    error_code=ErrorCode.DB_ERROR,
                    detail="数据库繁忙，请稍后重试"
                )
            )

        # 其他数据库错误
        logger.error(f"SQLite错误: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content=error(
                error_code=ErrorCode.DB_ERROR,
                detail=f"数据库操作失败: {str(exc)}"
            )
        )

    def _handle_unknown_error(self, request: Request, exc: Exception) -> JSONResponse:
        """处理未知异常"""
        # 记录详细错误信息
        error_trace = traceback.format_exc()
        logger.error(
            f"未处理异常 [{exc.__class__.__name__}]: {str(exc)}\n{error_trace}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "exception_type": exc.__class__.__name__
            }
        )

        # 生产环境隐藏详细错误
        detail = "系统内部错误，请联系管理员"
        # 开发环境可以显示更多信息
        import os
        if os.getenv("DEBUG", "false").lower() == "true":
            detail = f"{exc.__class__.__name__}: {str(exc)}"

        return JSONResponse(
            status_code=500,
            content=error(
                error_code=ErrorCode.SYSTEM_ERROR,
                detail=detail
            )
        )


def setup_exception_handlers(app):
    """
    设置全局异常处理器

    Args:
        app: FastAPI 应用实例
    """

    # 业务异常处理器
    @app.exception_handler(TOSRCException)
    async def tosrc_exception_handler(request: Request, exc: TOSRCException):
        handler = ExceptionHandlerMiddleware()
        return handler._handle_tosrc_exception(exc)

    # 参数校验异常处理器
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        handler = ExceptionHandlerMiddleware()
        return handler._handle_validation_error(exc)

    # 限流异常处理器
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        handler = ExceptionHandlerMiddleware()
        return handler._handle_rate_limit_error(exc)

    # 通用异常处理器（兜底）
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        handler = ExceptionHandlerMiddleware()
        return await handler.handle_exception(request, exc)

    logger.info("✅ 全局异常处理器已注册")


# 便捷装饰器
def handle_errors(func):
    """
    异常处理装饰器

    用于捕获函数中的异常并转换为业务异常

    使用示例：
        @handle_errors
        def some_function():
            raise ValueError("test")
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TOSRCException:
            raise
        except ValueError as e:
            raise ValidationException(
                error_code=ErrorCode.PARAM_INVALID,
                detail=str(e),
                cause=e
            ) from e
        except ConnectionError as e:
            raise DatabaseException(
                error_code=ErrorCode.DB_CONNECTION_ERROR,
                detail=f"连接失败: {str(e)}",
                cause=e
            ) from e
        except TimeoutError as e:
            raise SystemException(
                error_code=ErrorCode.TIMEOUT_ERROR,
                detail=f"操作超时: {str(e)}",
                cause=e
            ) from e
        except Exception as e:
            raise TOSRCException(
                error_code=ErrorCode.SYSTEM_ERROR,
                detail=f"操作失败: {str(e)}",
                cause=e
            ) from e

    return wrapper
