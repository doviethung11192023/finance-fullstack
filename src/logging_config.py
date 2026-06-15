"""
Cấu hình Logging tập trung cho toàn bộ ứng dụng.

Features:
  - JSON structured logs (production)
  - Pretty colored logs (development)
  - Intercept tất cả stdlib loggers (uvicorn, httpx, etc.)
  - Rotation & retention cho log files
  - Async-safe (enqueue=True)
"""
import sys
import logging
from loguru import logger
from src.config import settings

def setup_logging():
    """Khởi tạo hệ thống logging. Gọi 1 lần khi app khởi động."""

    # Xóa handler mặc định của Loguru
    logger.remove()

    # === Console Output ===
    # JSON format cho production, pretty format cho development
    logger.add(
        sys.stdout,
        serialize=True,           # JSON structured output
        level=settings.log_level,
        enqueue=True,             # Non-blocking, async-safe
        backtrace=True,           # Chi tiết traceback khi có exception
        diagnose=False,           # Tắt diagnose trong production (bảo mật)
    )

    # === File Output ===
    # Log file với rotation tự động
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="00:00",         # Rotate mỗi ngày lúc nửa đêm
        retention="7 days",       # Giữ log 7 ngày
        compression="gz",        # Nén log cũ
        serialize=True,
        level="DEBUG",
        enqueue=True,
    )

    # === RAG Audit Log ===
    # Log riêng cho prompt/response (audit trail)
    logger.add(
        "logs/rag_audit_{time:YYYY-MM-DD}.log",
        rotation="50 MB",
        retention="30 days",
        serialize=True,
        level="INFO",
        filter=lambda record: record["extra"].get("audit") is True,
        enqueue=True,
    )

    # === Intercept stdlib loggers ===
    # Chuyển hướng log từ uvicorn, httpx, etc. → Loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            logger.opt(depth=6, exception=record.exc_info).log(
                level, record.getMessage()
            )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Intercept các logger cụ thể
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "httpx"]:
        logging.getLogger(logger_name).handlers = [InterceptHandler()]

    logger.info("Logging system initialized", log_level=settings.log_level)