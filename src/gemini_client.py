from google import genai
from google.genai import types
from src.config import settings
from loguru import logger

# Khởi tạo client 1 lần duy nhất
client = genai.Client(api_key=settings.google_api_key)

def get_embedding(text: str) -> list[float]:
    """Tạo embedding 768 chiều cho 1 đoạn text."""
    logger.debug("Generating embedding", text_length=len(text))
    response = client.models.embed_content(
        model=settings.embedding_model,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=settings.embedding_dimension,
        ),
    )
    return response.embeddings[0].values

def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Tạo embedding cho nhiều đoạn text cùng lúc (batch)."""
    logger.info("Batch embedding", count=len(texts))
    response = client.models.embed_content(
        model=settings.embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(
            output_dimensionality=settings.embedding_dimension,
        ),
    )
    return [emb.values for emb in response.embeddings]

def chat_completion(
    user_message: str,
    system_instruction: str = "You are a helpful financial advisor.",
    temperature: float = 0.7,
) -> str:
    """Gọi Gemini 2.0 Flash để sinh câu trả lời."""
    logger.info("LLM call", model=settings.llm_model, prompt_length=len(user_message))
    response = client.models.generate_content(
        model=settings.llm_model,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=2048,
        ),
    )
    logger.info("LLM response", response_length=len(response.text))
    return response.text