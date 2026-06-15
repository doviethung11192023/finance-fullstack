"""
Middleware ghi lại mọi HTTP request/response.
Mỗi request được gán 1 unique request_id để trace xuyên suốt.
"""
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Gắn request_id vào context → tất cả log trong request này đều có request_id
        with logger.contextualize(request_id=request_id):
            logger.info(
                "request_started",
                method=request.method,
                url=str(request.url.path),
                query_params=str(request.query_params),
                client_ip=request.client.host if request.client else None,
            )

            try:
                response = await call_next(request)
            except Exception as e:
                logger.exception("request_failed", error=str(e))
                raise

            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.info(
                "request_completed",
                method=request.method,
                url=str(request.url.path),
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

        # Thêm request_id vào response header → client có thể dùng để debug
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = str(duration_ms)
        return response