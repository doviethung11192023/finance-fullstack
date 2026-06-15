"""
FastAPI Application Entry Point.

Endpoints:
  - POST /query       → RAG: Hỏi đáp dựa trên dữ liệu tài chính
  - GET  /health/live  → Liveness probe
  - GET  /health/ready → Readiness probe
  - GET  /metrics      → Prometheus metrics (auto-generated)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from loguru import logger

from src.logging_config import setup_logging
from src.middleware import RequestLoggingMiddleware
from src.health import router as health_router
from src.rag import query_rag

# === Lifespan: Setup/Teardown ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info("🚀 Application starting up")
    yield
    # Shutdown
    logger.info("🛑 Application shutting down")

# === FastAPI App ===
app = FastAPI(
    title="AI Financial Insight API",
    description="RAG-powered financial Q&A system using Gemini + Supabase",
    version="1.0.0",
    lifespan=lifespan,
)

# === Middleware ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# === Prometheus Metrics ===
# Tự động expose /metrics endpoint
# Exclude health + metrics endpoints khỏi metrics (tránh noise)
Instrumentator(
    excluded_handlers=["/health/live", "/health/ready", "/metrics", "/docs", "/openapi.json"],
).instrument(app).expose(app)

# === Health Routes ===
app.include_router(health_router)

# === Request/Response Models ===
class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Câu hỏi về tài chính",
        examples=["Tình hình tài chính của Apple như thế nào?"],
    )

class SourceInfo(BaseModel):
    ticker: str | None
    source: str | None
    similarity: float
    preview: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    query: str

# === API Endpoints ===
@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    🔍 RAG Query Endpoint

    Nhận câu hỏi từ người dùng → tìm kiếm tài liệu liên quan
    → sinh câu trả lời bằng Gemini AI.
    """
    result = query_rag(request.question)
    return result