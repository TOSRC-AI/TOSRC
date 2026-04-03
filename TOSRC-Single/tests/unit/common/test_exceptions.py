"""
业务异常体系单元测试
"""
import pytest
from src.common.error_codes import ErrorCode, success_response, error_response
from src.common.exceptions import (
    TOSRCException,
    DatabaseException,
    ValidationException,
    NotFoundException,
    DuplicateException,
    AuthException
)
from src.common.responses import success, error, pagination, get_http_status


class TestErrorCodes:
    """测试错误码定义"""

    def test_error_code_success(self):
        """测试成功错误码"""
        assert ErrorCode.SUCCESS.code == 0
        assert ErrorCode.SUCCESS.message == "成功"

    def test_error_code_system_error(self):
        """测试系统错误码"""
        assert ErrorCode.SYSTEM_ERROR.code == 100
        assert ErrorCode.DB_ERROR.code == 300
        assert ErrorCode.PARAM_ERROR.code == 400
        assert ErrorCode.AUTH_ERROR.code == 600

    def test_error_code_to_dict(self):
        """测试错误码转字典"""
        result = ErrorCode.PARAM_ERROR.to_dict(detail="缺少参数")
        assert result["code"] == 400
        assert result["message"] == "参数错误"
        assert result["detail"] == "缺少参数"

    def test_error_code_to_response(self):
        """测试错误码转响应"""
        result = ErrorCode.DB_NOT_FOUND.to_response(data=None)
        assert result["code"] == 304
        assert result["message"] == "数据不存在"
        assert result["data"] is None


class TestSuccessResponse:
    """测试成功响应"""

    def test_success_response(self):
        """测试基础成功响应"""
        result = success_response(data={"id": 1}, message="创建成功")
        assert result["code"] == 0
        assert result["message"] == "创建成功"
        assert result["data"]["id"] == 1

    def test_error_response(self):
        """测试错误响应"""
        result = error_response(ErrorCode.PARAM_INVALID, detail="字段格式错误")
        assert result["code"] == 402
        assert result["message"] == "参数格式无效"
        assert result["detail"] == "字段格式错误"


class TestTOSRCException:
    """测试基础业务异常"""

    def test_basic_exception(self):
        """测试基础异常"""
        exc = TOSRCException(
            error_code=ErrorCode.SYSTEM_ERROR,
            detail="系统错误"
        )
        assert exc.error_code == ErrorCode.SYSTEM_ERROR
        assert exc.detail == "系统错误"
        assert "[100] 系统错误" in str(exc)

    def test_exception_with_cause(self):
        """测试带原因链的异常"""
        cause = ValueError("原始错误")
        exc = TOSRCException(
            error_code=ErrorCode.DB_ERROR,
            detail="数据库失败",
            cause=cause
        )
        assert exc.cause == cause
        assert "原始错误" in str(exc)

    def test_exception_to_dict(self):
        """测试异常转字典"""
        exc = TOSRCException(
            error_code=ErrorCode.PARAM_MISSING,
            detail="缺少user_id"
        )
        result = exc.to_dict()
        assert result["code"] == 401
        assert result["message"] == "缺少必要参数"
        assert result["detail"] == "缺少user_id"

    def test_exception_with_data(self):
        """测试带数据的异常"""
        exc = TOSRCException(
            error_code=ErrorCode.PARAM_INVALID,
            detail="验证失败",
            data={"fields": ["name", "email"]}
        )
        result = exc.to_dict()
        assert result["data"]["fields"] == ["name", "email"]


class TestSpecificExceptions:
    """测试具体业务异常"""

    def test_database_exception(self):
        """测试数据库异常"""
        exc = DatabaseException(
            error_code=ErrorCode.DB_CONNECTION_ERROR,
            detail="连接超时"
        )
        assert exc.error_code.code == 301
        assert "连接超时" in str(exc)

    def test_validation_exception(self):
        """测试验证异常"""
        exc = ValidationException(
            error_code=ErrorCode.PARAM_INVALID,
            detail="email格式不正确"
        )
        assert exc.error_code.code == 402

    def test_not_found_exception(self):
        """测试资源不存在异常"""
        exc = NotFoundException(resource="用户", resource_id=123)
        assert exc.error_code.code == 304
        assert "用户 [123] 不存在" == exc.detail

    def test_not_found_without_id(self):
        """测试无ID的资源不存在异常"""
        exc = NotFoundException(resource="配置")
        assert "配置不存在" == exc.detail

    def test_duplicate_exception(self):
        """测试数据重复异常"""
        exc = DuplicateException(resource="用户", key="admin")
        assert exc.error_code.code == 303
        assert "用户 [admin] 已存在" == exc.detail

    def test_auth_exception(self):
        """测试认证异常"""
        exc = AuthException(
            error_code=ErrorCode.API_KEY_INVALID,
            detail="Token已过期"
        )
        assert exc.error_code.code == 601


class TestResponseFunctions:
    """测试响应函数"""

    def test_success_function(self):
        """测试success函数"""
        result = success(data={"list": []}, message="查询成功")
        assert result["code"] == 0
        assert result["message"] == "查询成功"
        assert result["data"]["list"] == []

    def test_success_without_data(self):
        """测试无数据的success函数"""
        result = success()
        assert result["code"] == 0
        assert result["data"] is None

    def test_error_function(self):
        """测试error函数"""
        result = error(
            error_code=ErrorCode.DB_NOT_FOUND,
            detail="记录不存在"
        )
        assert result["code"] == 304
        assert result["message"] == "数据不存在"
        assert result["detail"] == "记录不存在"

    def test_error_without_detail(self):
        """测试无详情的error函数"""
        result = error(error_code=ErrorCode.SYSTEM_ERROR)
        assert result["detail"] == ErrorCode.SYSTEM_ERROR.message

    def test_pagination_function(self):
        """测试分页函数"""
        result = pagination(
            items=[1, 2, 3],
            total=100,
            page=2,
            page_size=20
        )
        assert result["code"] == 0
        assert result["data"]["items"] == [1, 2, 3]
        assert result["data"]["total"] == 100
        assert result["data"]["page"] == 2
        assert result["data"]["pages"] == 5  # ceil(100/20)

    def test_pagination_empty(self):
        """测试空分页"""
        result = pagination(items=[], total=0)
        assert result["data"]["pages"] == 0


class TestHttpStatusMapping:
    """测试HTTP状态码映射"""

    def test_success_status(self):
        """测试成功状态码"""
        assert get_http_status(0) == 200

    def test_system_error_status(self):
        """测试系统错误状态码"""
        assert get_http_status(100) == 500
        assert get_http_status(101) == 503

    def test_rate_limit_status(self):
        """测试限流状态码"""
        assert get_http_status(102) == 429

    def test_not_found_status(self):
        """测试不存在状态码"""
        assert get_http_status(304) == 404

    def test_duplicate_status(self):
        """测试重复状态码"""
        assert get_http_status(303) == 409

    def test_auth_status(self):
        """测试认证状态码"""
        assert get_http_status(600) == 401
        assert get_http_status(603) == 403

    def test_unknown_status(self):
        """测试未知错误码默认返回500"""
        assert get_http_status(999) == 500


class TestExceptionChaining:
    """测试异常链"""

    def test_exception_chain(self):
        """测试异常链传递"""
        try:
            try:
                raise ValueError("底层错误")
            except ValueError as e:
                raise DatabaseException(
                    error_code=ErrorCode.DB_ERROR,
                    detail="数据库操作失败",
                    cause=e
                ) from e
        except DatabaseException as e:
            assert e.cause is not None
            assert isinstance(e.cause, ValueError)

    def test_exception_to_response_with_data(self):
        """测试带数据的异常响应"""
        exc = ValidationException(
            error_code=ErrorCode.PARAM_INVALID,
            detail="字段验证失败",
            data={"invalid_fields": ["age", "email"]}
        )
        response = exc.to_response()
        assert response["data"]["invalid_fields"] == ["age", "email"]
