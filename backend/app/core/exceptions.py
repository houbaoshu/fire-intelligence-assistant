"""应用异常与全局异常处理器。

错误响应对齐 API.md §1.3 错误信封::

    {"error": {"code": "...", "message": "..."}}

业务代码抛出 ``AppException``（或其工厂构造的子类），由 main.py 中注册的
全局 handler 统一转换为标准错误响应；未预期异常一律映射为 500 INTERNAL_ERROR，
不向客户端暴露堆栈。
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger("exceptions")


class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=_error_body(code, message))


def unauthorized(message: str = "认证失败") -> AppException:
    return AppException("UNAUTHORIZED", message, status.HTTP_401_UNAUTHORIZED)


def forbidden(message: str = "无权访问") -> AppException:
    return AppException("FORBIDDEN", message, status.HTTP_403_FORBIDDEN)


def not_found(message: str = "资源不存在") -> AppException:
    return AppException("NOT_FOUND", message, status.HTTP_404_NOT_FOUND)


def conflict(code: str, message: str) -> AppException:
    return AppException(code, message, status.HTTP_409_CONFLICT)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
        return error_response(exc.code, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            "VALIDATION_ERROR", "请求参数校验失败", status.HTTP_400_BAD_REQUEST
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code_map = {
            400: "VALIDATION_ERROR",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "VALIDATION_ERROR",
            409: "TASK_STATE_CONFLICT",
            413: "FILE_TOO_LARGE",
        }
        code = code_map.get(exc.status_code, "INTERNAL_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        return error_response(code, message, exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.error("未处理异常: %s", type(exc).__name__, exc_info=exc)
        return error_response(
            "INTERNAL_ERROR", "服务器内部错误", status.HTTP_500_INTERNAL_SERVER_ERROR
        )
