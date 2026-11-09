"""统一错误响应。

不管哪里出错，调用方拿到的都是同一个形状：
    {"error": {"code": "...", "message": "...", "details": [...]}}

code 给程序判断，message 给人看。
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")


class AppError(Exception):
    """业务错误：路由里 raise 它，由下面的处理器翻译成 HTTP 响应。"""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def _error(status_code: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return _error(exc.status_code, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        return _error(exc.status_code, "HTTP_ERROR", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        details = [
            {
                "field": ".".join(str(part) for part in err["loc"]),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return _error(422, "VALIDATION_ERROR", "参数校验失败", details)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        # traceback 只进日志，绝不返回给调用方
        logger.exception("未处理异常: %s %s", request.method, request.url.path)
        return _error(500, "INTERNAL_ERROR", "服务器内部错误")
