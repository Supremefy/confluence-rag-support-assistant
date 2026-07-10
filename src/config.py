from functools import lru_cache
import os
from pathlib import Path

from dataclasses import dataclass


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


@dataclass
class Settings:
    ai_provider: str
    openai_api_key: str | None
    openai_chat_model: str
    openai_embedding_model: str
    gemini_api_key: str | None
    gemini_chat_model: str
    gemini_embedding_model: str
    vector_store_dir: Path
    vector_store_backend: str
    use_mock_ai: bool
    confluence_base_url: str | None
    confluence_email: str | None
    confluence_api_token: str | None
    confluence_space_key: str | None
    confluence_cql: str | None
    confluence_limit: int


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    return Settings(
        ai_provider=os.getenv("AI_PROVIDER", "openai").lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini"),
        openai_embedding_model=os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        ),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_chat_model=os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash"),
        gemini_embedding_model=os.getenv(
            "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"
        ),
        vector_store_dir=Path(os.getenv("VECTOR_STORE_DIR", ".vector-store")),
        vector_store_backend=os.getenv("VECTOR_STORE_BACKEND", "chroma").lower(),
        use_mock_ai=os.getenv("USE_MOCK_AI", "true").lower() in {"1", "true", "yes"},
        confluence_base_url=os.getenv("CONFLUENCE_BASE_URL") or None,
        confluence_email=os.getenv("CONFLUENCE_EMAIL") or None,
        confluence_api_token=os.getenv("CONFLUENCE_API_TOKEN") or None,
        confluence_space_key=os.getenv("CONFLUENCE_SPACE_KEY") or None,
        confluence_cql=os.getenv("CONFLUENCE_CQL") or None,
        confluence_limit=int(os.getenv("CONFLUENCE_LIMIT", "50")),
    )


def require_confluence_settings(settings: Settings):
    from src.confluence import ConfluenceSettings

    missing = [
        name
        for name, value in {
            "CONFLUENCE_BASE_URL": settings.confluence_base_url,
            "CONFLUENCE_EMAIL": settings.confluence_email,
            "CONFLUENCE_API_TOKEN": settings.confluence_api_token,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing Confluence settings: {', '.join(missing)}")

    return ConfluenceSettings(
        base_url=str(settings.confluence_base_url),
        email=str(settings.confluence_email),
        api_token=str(settings.confluence_api_token),
        space_key=settings.confluence_space_key,
        cql=settings.confluence_cql,
        limit=settings.confluence_limit,
    )
