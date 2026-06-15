"""
Pipeline xử lý dữ liệu:
  1. Chunk văn bản dài thành các đoạn nhỏ (LangChain TextSplitter)
  2. Tạo vector embedding cho mỗi chunk (Gemini API)
  3. Insert vào Supabase (PostgreSQL + pgvector)
"""
import time
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from src.config import settings
from src.gemini_client import get_embeddings_batch
from src.supabase_client import get_supabase

def chunk_text(text: str, chunk_size: int = None, chunk_overlap: int = None) -> list[str]:
    """
    Chia văn bản thành các chunks nhỏ hơn.

    Args:
        text: Văn bản gốc cần chia
        chunk_size: Kích thước tối đa mỗi chunk (ký tự)
        chunk_overlap: Số ký tự chồng lấp giữa 2 chunk liên tiếp

    Returns:
        Danh sách các chunk text
    """
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_text(text)
    logger.debug(f"Split text ({len(text)} chars) into {len(chunks)} chunks")
    return chunks

def prepare_chunks(documents: list[dict]) -> list[dict]:
    """
    Nhận danh sách documents gốc → chunk từng document
    → trả về list các chunk records sẵn sàng để embed.

    Output format:
      {"content": "chunk text...", "metadata": {"ticker": "AAPL", "source": "info", ...}}
    """
    chunk_records = []
    for doc in documents:
        chunks = chunk_text(doc["content"])
        for i, chunk in enumerate(chunks):
            chunk_records.append({
                "content": chunk,
                "metadata": {
                    "ticker": doc.get("ticker"),
                    "source": doc.get("source"),
                    "date": doc.get("date"),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            })

    logger.info(f"Prepared {len(chunk_records)} chunks from {len(documents)} documents")
    return chunk_records

def embed_and_insert(chunk_records: list[dict], batch_size: int = 20) -> dict:
    """
    Embed tất cả chunks (theo batch) và insert vào Supabase.

    Args:
        chunk_records: Output từ prepare_chunks()
        batch_size: Số chunks xử lý mỗi batch (tránh rate limit Gemini)

    Returns:
        {"total": int, "inserted": int, "failed": int, "duration_seconds": float}
    """
    supabase = get_supabase()
    inserted = 0
    failed = 0
    start_time = time.time()

    for i in range(0, len(chunk_records), batch_size):
        batch = chunk_records[i:i + batch_size]
        texts = [r["content"] for r in batch]

        try:
            # Step 1: Batch embed
            embeddings = get_embeddings_batch(texts)

            # Step 2: Chuẩn bị rows cho insert
            rows = []
            for record, embedding in zip(batch, embeddings):
                rows.append({
                    "content": record["content"],
                    "embedding": embedding,
                    "metadata": record["metadata"],
                })

            # Step 3: Insert vào Supabase
            result = supabase.table("financial_documents").insert(rows).execute()
            inserted += len(rows)
            logger.info(
                f"Batch {i // batch_size + 1}: Inserted {len(rows)} records"
            )

        except Exception as e:
            failed += len(batch)
            logger.error(f"Batch {i // batch_size + 1} failed: {e}")

        # Rate limiting: nghỉ 1s giữa các batch
        time.sleep(1)

    duration = time.time() - start_time
    stats = {
        "total": len(chunk_records),
        "inserted": inserted,
        "failed": failed,
        "duration_seconds": round(duration, 2),
    }
    logger.info(f"Pipeline complete: {stats}")
    return stats

def run_pipeline(documents: list[dict]) -> dict:
    """Chạy toàn bộ pipeline: chunk → embed → insert."""
    logger.info("=" * 60)
    logger.info("STARTING DATA PIPELINE")
    logger.info("=" * 60)

    chunk_records = prepare_chunks(documents)
    stats = embed_and_insert(chunk_records)

    logger.info("=" * 60)
    logger.info(f"PIPELINE FINISHED: {stats}")
    logger.info("=" * 60)
    return stats