# -*- coding: utf-8 -*-
"""
错误码定义

错误码规范：
- 0: 成功
- 1xx: 系统级错误
- 2xx: 配置/初始化错误
- 3xx: 数据库/存储错误
- 4xx: 业务逻辑错误（客户端错误）
- 5xx: 外部服务错误
- 6xx: 安全/认证错误
"""
from enum import Enum
from typing import Dict, Any


class ErrorCode(Enum):
    """错误码枚举"""

    # 成功
    SUCCESS = (0, "成功")

    # 系统级错误 (1xx)
    SYSTEM_ERROR = (100, "系统内部错误")
    SERVICE_UNAVAILABLE = (101, "服务暂不可用")
    RATE_LIMIT_EXCEEDED = (102, "请求过于频繁，请稍后再试")
    TIMEOUT_ERROR = (103, "请求超时")
    NOT_IMPLEMENTED = (104, "功能未实现")

    # 配置/初始化错误 (2xx)
    CONFIG_ERROR = (200, "配置错误")
    CONFIG_NOT_FOUND = (201, "配置文件不存在")
    CONFIG_INVALID = (202, "配置格式无效")
    INIT_ERROR = (203, "初始化失败")

    # 数据库/存储错误 (3xx)
    DB_ERROR = (300, "数据库错误")
    DB_CONNECTION_ERROR = (301, "数据库连接失败")
    DB_QUERY_ERROR = (302, "数据库查询错误")
    DB_DUPLICATE_KEY = (303, "数据重复")
    DB_NOT_FOUND = (304, "数据不存在")
    DB_POOL_EXHAUSTED = (305, "数据库连接池已满")
    JSONL_ERROR = (310, "JSONL日志错误")
    ARCHIVE_ERROR = (311, "归档操作失败")

    # 业务逻辑错误 (4xx)
    PARAM_ERROR = (400, "参数错误")
    PARAM_MISSING = (401, "缺少必要参数")
    PARAM_INVALID = (402, "参数格式无效")
    INTENT_NOT_FOUND = (410, "意图不存在")
    INTENT_EXISTS = (411, "意图已存在")
    KEYWORD_NOT_FOUND = (420, "关键词不存在")
    KEYWORD_EXISTS = (421, "关键词已存在")
    RULE_NOT_FOUND = (430, "规则不存在")
    ENTITY_NOT_FOUND = (440, "实体不存在")

    # 外部服务错误 (5xx)
    EXTERNAL_SERVICE_ERROR = (500, "外部服务错误")
    LLM_SERVICE_ERROR = (501, "LLM服务调用失败")

    # 安全/认证错误 (6xx)
    AUTH_ERROR = (600, "认证失败")
    API_KEY_INVALID = (601, "API Key无效")
    API_KEY_MISSING = (602, "缺少API Key")
    PERMISSION_DENIED = (603, "权限不足")
    RESOURCE_FORBIDDEN = (604, "禁止访问该资源")

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

    def to_dict(self, detail: str = None) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code,
            "message": self.message,
            "detail": detail or self.message
        }

    def to_response(self, data: Any = None, detail: str = None) -> Dict[str, Any]:
        """生成标准响应"""
        return {
            "code": self.code,
            "message": self.message,
            "detail": detail or self.message,
            "data": data
        }


# 快捷函数
def success_response(data: Any = None, message: str = "成功") -> Dict[str, Any]:
    """成功响应"""
    return {
        "code": 0,
        "message": message,
        "data": data
    }


def error_response(error_code: ErrorCode, detail: str = None, data: Any = None) -> Dict[str, Any]:
    """错误响应"""
    return error_code.to_response(data=data, detail=detail)
