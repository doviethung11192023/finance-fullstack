# sử dụng pydantic để validate toàn bộ biến môi trường ngày lúc khởi động nếu thiếu biến, app sẽ crash sớm với thông báo rõ ràng thay vì lỗi runtime bất ngờ

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_key: str

    # Gemini
    google_api_key: str

    # App
    log_level: str = "INFO"
    embedding_model: str = "text-embedding-004"
    embedding_dimension: int = 768
    llm_model: str = "gemini-2.0-flash"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5

    class Config:
        env_file = ".env"

settings = Settings()