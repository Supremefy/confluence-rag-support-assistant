from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ai import AiClient
from src.config import get_settings
from src.ingest import load_markdown_documents
from src.vector_store import VectorStore


def main() -> None:
    settings = get_settings()
    ai_client = AiClient(settings)
    vector_store = VectorStore(settings, ai_client)
    vector_store.clear()
    chunks = load_markdown_documents(ROOT / "data/sample-docs")
    count = vector_store.upsert_chunks(chunks)
    print(f"Indexed {count} chunks")


if __name__ == "__main__":
    main()
