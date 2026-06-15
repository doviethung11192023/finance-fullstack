from supabase import create_client, Client
from src.config import settings

_client: Client | None = None

def get_supabase() -> Client:
    """Singleton pattern — tái sử dụng 1 connection duy nhất."""
    global _client
    if _client is None:
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
    return _client