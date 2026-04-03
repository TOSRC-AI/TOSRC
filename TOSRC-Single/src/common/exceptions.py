# -*- coding: utf-8 -*-
"""
业务异常定义

提供完整的业务异常体系，支持错误码、详细信息和元数据
"""
from typing import Any, Dict, Optional
from .error_codes import ErrorCode


class TOSRCException(Exception):
    """
    TOSRC 基础业务异常

    特性：
    - 支持错误码
    - 支持详细错误信息
    - 支持元数据扩展
    - 支持链式异常

    使用示例：
        raise TOSRCException(ErrorCode.PARAM_ERROR, detail="缺少user_id参数")
        raise DatabaseException(ErrorCode.DB_CONNECTION_ERROR, detail="SQLite连接失败")
    """

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.SYSTEM_ERROR,
        detail: str = None,
        data: Any = None,
        cause: Exception = None
    ):
        """
        初始化异常

        Args:
            error_code: 错误码枚举
            detail: 详细错误信息（会覆盖默认message）
            data: 附加数据
            cause: 原始异常（用于链式异常）
        """
        self.error_code = error_code
        self.detail = detail or error_code.message
        self.data = data
        self.cause = cause

        # 生成错误消息
        message = f"[{error_code.code}] {self.detail}"
        if cause:
            message += f" (caused by: {str(cause)})"

        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于API响应"""
        result = {
            "code": self.error_code.code,
            "message": self.error_code.message,
            "detail": self.detail
        }
        if self.data is not None:
            result["data"] = self.data
        return result

    def to_response(self) -> Dict[str, Any]:
        """生成FastAPI响应格式"""
        return self.to_dict()


# ==================== 具体业务异常 ====================

class SystemException(TOSRCException):
    """系统级异常"""
    def __init__(self, error_code: ErrorCode = ErrorCode.SYSTEM_ERROR, **kwargs):
        super().__init__(error_code=error_code, **kwargs)


class ConfigException(TOSRCException):
    """配置异常"""
    def __init__(self, error_code: ErrorCode = ErrorCode.CONFIG_ERROR, **kwargs):
        super().__init__(error_code=error_code, **kwargs)


class DatabaseException(TOSRCException):
    """数据库异常"""
    def __init__(self, error_code: ErrorCode = ErrorCode.DB_ERROR, **kwargs):
        super().__init__(error_code=error_code, **kwargs)


class ValidationException(TOSRCException):
    """参数校验异常"""
    def __init__(self, error_code: ErrorCode = ErrorCode.PARAM_ERROR, **kwargs):
        super().__init__(error_code=error_code, **kwargs)


class BusinessException(TOSRCException):
    """业务逻辑异常"""
    def __init__(self, error_code: ErrorCode = ErrorCode.SYSTEM_ERROR, **kwargs):
        super().__init__(error_code=error_code, **kwargs)


class NotFoundException(BusinessException):
    """资源不存在异常"""
    def __init__(self, resource: str = "资源", resource_id: Any = None, **kwargs):
        detail = f"{resource}不存在"
        if resource_id:
            detail = f"{resource} [{resource_id}] 不存在"
        super().__init__(
            error_code=ErrorCode.DB_NOT_FOUND,
            detail=detail,
            **kwargs
        )


class DuplicateException(BusinessException):
    """数据重复异常"""
    def __init__(self, resource: str = "数据", key: str = None, **kwargs):
        detail = f"{resource}已存在"
        if key:
            detail = f"{resource} [{key}] 已存在"
        super().__init__(
            error_code=ErrorCode.DB_DUPLICATE_KEY,
            detail=detail,
            **kwargs
        )


class AuthException(TOSRCException):
    """认证/授权异常"""
    def __init__(self, error_code: ErrorCode = ErrorCode.AUTH_ERROR, **kwargs):
        super().__init__(error_code=error_code, **kwargs)


class ExternalServiceException(TOSRCException):
    """外部服务异常"""
    def __init__(self, error_code: ErrorCode = ErrorCode.EXTERNAL_SERVICE_ERROR, **kwargs):
        super().__init__(error_code=error_code, **kwargs)


class JSONLException(TOSRCException):
    """JSONL日志异常"""
    def __init__(self, error_code: ErrorCode = ErrorCode.JSONL_ERROR, **kwargs):
        super().__init__(error_code=error_code, **kwargs)


class ArchiveException(TOSRCException):
    """归档操作异常"""
    def __init__(self, error_code: ErrorCode = ErrorCode.ARCHIVE_ERROR, **kwargs):
        super().__init__(error_code=error_code, **kwargs)
