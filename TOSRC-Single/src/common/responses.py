# -*- coding: utf-8 -*-
"""
标准响应模型

提供统一的API响应格式，支持Pydantic验证
"""
from typing import Any, Optional, TypeVar, Generic
from pydantic import BaseModel, Field
from .error_codes import ErrorCode

T = TypeVar('T')


class StandardResponse(BaseModel, Generic[T]):
    """
    标准API响应模型

    统一响应格式：
    {
        "code": 0,           // 错误码，0表示成功
        "message": "成功",   // 提示信息
        "data": {...}        // 业务数据
    }
    """
    code: int = Field(default=0, description="错误码，0表示成功")
    message: str = Field(default="success", description="提示信息")
    data: Optional[T] = Field(default=None, description="业务数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 0,
                "message": "success",
                "data": {}
            }
        }


class ErrorResponse(BaseModel):
    """错误响应模型"""
    code: int = Field(description="错误码")
    message: str = Field(description="错误概要")
    detail: str = Field(description="详细错误信息")
    data: Optional[Any] = Field(default=None, description="附加数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 400,
                "message": "参数错误",
                "detail": "缺少必要参数：user_id",
                "data": None
            }
        }


class PaginationData(BaseModel, Generic[T]):
    """分页数据结构"""
    items: list[T] = Field(description="数据列表")
    total: int = Field(description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")
    pages: int = Field(default=1, description="总页数")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": 20,
                "pages": 0
            }
        }


class PaginationResponse(StandardResponse[PaginationData[T]]):
    """分页响应模型"""
    pass


# ==================== 响应构建函数 ====================

def success(data: Any = None, message: str = "success") -> dict:
    """构建成功响应"""
    return {
        "code": 0,
        "message": message,
        "data": data
    }


def error(
    error_code: ErrorCode = ErrorCode.SYSTEM_ERROR,
    detail: str = None,
    data: Any = None
) -> dict:
    """构建错误响应"""
    return {
        "code": error_code.code,
        "message": error_code.message,
        "detail": detail or error_code.message,
        "data": data
    }


def pagination(
    items: list,
    total: int,
    page: int = 1,
    page_size: int = 20,
    message: str = "success"
) -> dict:
    """构建分页响应"""
    pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "code": 0,
        "message": message,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        }
    }


# ==================== HTTP状态码映射 ====================

ERROR_CODE_HTTP_STATUS = {
    # 成功
    0: 200,

    # 系统级错误
    100: 500,
    101: 503,
    102: 429,
    103: 504,
    104: 501,

    # 配置错误
    200: 500,
    201: 500,
    202: 500,
    203: 500,

    # 数据库错误
    300: 500,
    301: 500,
    302: 500,
    303: 409,
    304: 404,
    305: 503,
    310: 500,
    311: 500,

    # 业务逻辑错误
    400: 400,
    401: 400,
    402: 400,
    410: 404,
    411: 409,
    420: 404,
    421: 409,
    430: 404,
    440: 404,

    # 外部服务错误
    500: 502,
    501: 502,

    # 安全/认证错误
    600: 401,
    601: 401,
    602: 401,
    603: 403,
    604: 403,
}


def get_http_status(error_code: int) -> int:
    """根据错误码获取HTTP状态码"""
    return ERROR_CODE_HTTP_STATUS.get(error_code, 500)
