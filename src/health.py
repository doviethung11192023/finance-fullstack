"""
Health Check Endpoints theo best practice Kubernetes.

- /health/live  → Liveness:  App có đang chạy không? (KHÔNG check dependencies)
- /health/ready → Readiness: App có sẵn sàng nhận traffic không? (CHECK dependencies)
"""
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(tags=["Health"])

@router.get("/health/live")
async def liveness():
    """
    Liveness probe — App có đang chạy không?
    Nếu fail → container cần restart.
    KHÔNG check external dependencies.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@router.get("/health/ready")
async def readiness():
    """
    Readiness probe — App có sẵn sàng phục vụ traffic?
    Check song song: Database + Gemini API.
    Nếu fail → ngừng route traffic tới instance này.
    """
    checks = {}

    db_ok, gemini_ok = await asyncio.gather(
        _check_database(),
        _check_gemini(),
        return_exceptions=True,
    )

    checks["database"] = "ok" if db_ok is True else f"error: {db_ok}"
    checks["gemini_api"] = "ok" if gemini_ok is True else f"error: {gemini_ok}"

    if not all(v == "ok" for v in checks.values()):
        logger.warning("Readiness check failed", checks=checks)
        raise HTTPException(status_code=503, detail={
            "status": "not_ready",
            "checks": checks,
        })

    return {
        "status": "ready",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

async def _check_database() -> bool:
    try:
        from src.supabase_client import get_supabase
        supabase = get_supabase()
        result = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: supabase.table("financial_documents").select("id").limit(1).execute()
            ),
            timeout=3.0,
        )
        return True
    except Exception as e:
        return str(e)

async def _check_gemini() -> bool:
    try:
        from src.gemini_client import client
        await asyncio.wait_for(
            asyncio.to_thread(
                lambda: client.models.embed_content(
                    model="text-embedding-004",
                    contents="health check",
                )
            ),
            timeout=5.0,
        )
        return True
    except Exception as e:
        return str(e)