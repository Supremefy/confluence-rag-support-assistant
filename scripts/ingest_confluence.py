from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ai import AiClient
from src.config import get_settings, require_confluence_settings
from src.confluence import ConfluenceClient, confluence_pages_to_chunks
from src.vector_store import VectorStore


def main() -> None:
    settings = get_settings()
    confluence_settings = require_confluence_settings(settings)
    pages = ConfluenceClient(confluence_settings).fetch_pages()
    chunks = confluence_pages_to_chunks(pages)

    ai_client = AiClient(settings)
    vector_store = VectorStore(settings, ai_client)
    vector_store.clear()
    count = vector_store.upsert_chunks(chunks)
    print(f"Indexed {len(pages)} Confluence pages into {count} chunks")


if __name__ == "__main__":
    main()
