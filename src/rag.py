"""
RAG (Retrieval-Augmented Generation) Logic.

Flow:
  1. Nhận câu hỏi từ user
  2. Embed câu hỏi → vector
  3. Tìm top-k documents tương tự trong Supabase (pgvector)
  4. Ghép context + câu hỏi → prompt
  5. Gửi tới Gemini LLM → trả về câu trả lời
"""
from loguru import logger
from src.config import settings
from src.gemini_client import get_embedding, chat_completion
from src.supabase_client import get_supabase

# Audit logger — ghi vào file riêng
audit_logger = logger.bind(audit=True)

SYSTEM_PROMPT = """Bạn là một chuyên gia phân tích tài chính AI.
Dựa trên các tài liệu tham khảo được cung cấp bên dưới, hãy trả lời câu hỏi của người dùng
một cách chính xác, chi tiết và dễ hiểu.

Quy tắc:
- Chỉ sử dụng thông tin từ tài liệu tham khảo. Nếu không đủ thông tin, hãy nói rõ.
- Trích dẫn nguồn (ticker, source) khi có thể.
- Trả lời bằng tiếng Việt nếu câu hỏi bằng tiếng Việt, tiếng Anh nếu bằng tiếng Anh.
"""

def retrieve_documents(query: str, top_k: int = None) -> list[dict]:
    """
    Tìm top-k documents tương tự nhất với query.

    Returns:
        List of {"content": str, "metadata": dict, "similarity": float}
    """
    top_k = top_k or settings.top_k
    supabase = get_supabase()

    # Step 1: Embed query
    query_embedding = get_embedding(query)

    # Step 2: Gọi RPC function match_documents()
    result = supabase.rpc("match_documents", {
        "query_embedding": query_embedding,
        "match_threshold": 0.5,
        "match_count": top_k,
    }).execute()

    documents = result.data or []
    logger.info(
        "Documents retrieved",
        query_length=len(query),
        top_k=top_k,
        found=len(documents),
    )
    return documents

def generate_answer(query: str, documents: list[dict]) -> str:
    """
    Ghép context từ documents + câu hỏi → gọi LLM.
    """
    # Xây dựng context string
    context_parts = []
    for i, doc in enumerate(documents, 1):
        meta = doc.get("metadata", {})
        ticker = meta.get("ticker", "N/A")
        source = meta.get("source", "N/A")
        similarity = doc.get("similarity", 0)
        context_parts.append(
            f"[Tài liệu {i}] (Ticker: {ticker}, Source: {source}, "
            f"Similarity: {similarity:.2f})\n{doc['content']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    # Xây dựng prompt
    prompt = f"""Tài liệu tham khảo:

{context}

---

Câu hỏi của người dùng: {query}

Hãy trả lời dựa trên các tài liệu tham khảo ở trên."""

    # Gọi LLM
    answer = chat_completion(prompt, system_instruction=SYSTEM_PROMPT)

    # Audit log: ghi lại prompt/response để kiểm soát chất lượng
    audit_logger.info(
        "rag_interaction",
        query=query,
        num_documents=len(documents),
        prompt_length=len(prompt),
        response_length=len(answer),
        top_similarity=documents[0]["similarity"] if documents else 0,
    )

    return answer

def query_rag(question: str) -> dict:
    """
    Entry point chính cho RAG pipeline.

    Returns:
        {
            "answer": str,
            "sources": list[dict],
            "query": str,
        }
    """
    logger.info("RAG query started", question=question)

    # Step 1: Retrieve
    documents = retrieve_documents(question)

    if not documents:
        logger.warning("No relevant documents found", question=question)
        return {
            "answer": "Xin lỗi, tôi không tìm thấy tài liệu liên quan để trả lời câu hỏi này.",
            "sources": [],
            "query": question,
        }

    # Step 2: Generate
    answer = generate_answer(question, documents)

    # Step 3: Chuẩn bị sources metadata
    sources = [
        {
            "ticker": doc.get("metadata", {}).get("ticker"),
            "source": doc.get("metadata", {}).get("source"),
            "similarity": round(doc.get("similarity", 0), 4),
            "preview": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
        }
        for doc in documents
    ]

    logger.info("RAG query completed", num_sources=len(sources))
    return {
        "answer": answer,
        "sources": sources,
        "query": question,
    }