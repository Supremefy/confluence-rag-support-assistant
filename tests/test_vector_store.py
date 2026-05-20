import tempfile
import unittest
from uuid import uuid4
from pathlib import Path

from src.ai import AiClient
from src.config import Settings
from src.schemas import DocumentChunk
from src.vector_store import VectorStore


class VectorStoreTests(unittest.TestCase):
    def test_clear_removes_existing_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(
                openai_api_key=None,
                openai_chat_model="mock",
                openai_embedding_model="mock",
                vector_store_dir=Path(tmpdir),
                vector_store_backend="json",
                use_mock_ai=True,
                confluence_base_url=None,
                confluence_email=None,
                confluence_api_token=None,
                confluence_space_key=None,
                confluence_cql=None,
                confluence_limit=50,
            )
            store = VectorStore(settings, AiClient(settings))
            store.upsert_chunks(
                [
                    DocumentChunk(
                        id="chunk-1",
                        text="Refund policy",
                        metadata={"title": "Refund Policy"},
                    )
                ]
            )

            store.clear()

            self.assertEqual(store.search("refund"), [])

    def test_json_backend_can_search_upserted_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = _settings(Path(tmpdir), backend="json")
            store = VectorStore(settings, AiClient(settings))
            store.upsert_chunks(
                [
                    DocumentChunk(
                        id="refund",
                        text="Refund policy for used service",
                        metadata={"title": "Refund Policy"},
                    ),
                    DocumentChunk(
                        id="login",
                        text="Password reset and login issue",
                        metadata={"title": "Login Policy"},
                    ),
                ]
            )

            results = store.search("Can the customer get a refund?", limit=1)

            self.assertEqual(results[0].metadata["title"], "Refund Policy")

    def test_chroma_backend_can_search_upserted_records(self):
        path = Path(".test-chroma") / str(uuid4())
        settings = _settings(path, backend="chroma")
        store = VectorStore(settings, AiClient(settings))
        store.upsert_chunks(
            [
                DocumentChunk(
                    id="refund",
                    text="Refund policy for used service",
                    metadata={"title": "Refund Policy"},
                ),
                DocumentChunk(
                    id="login",
                    text="Password reset and login issue",
                    metadata={"title": "Login Policy"},
                ),
            ]
        )

        results = store.search("Can the customer get a refund?", limit=1)

        self.assertEqual(results[0].metadata["title"], "Refund Policy")
        store.clear()
        self.assertEqual(store.search("refund"), [])
        store.close()


def _settings(path: Path, backend: str) -> Settings:
    return Settings(
        openai_api_key=None,
        openai_chat_model="mock",
        openai_embedding_model="mock",
        vector_store_dir=path,
        vector_store_backend=backend,
        use_mock_ai=True,
        confluence_base_url=None,
        confluence_email=None,
        confluence_api_token=None,
        confluence_space_key=None,
        confluence_cql=None,
        confluence_limit=50,
    )


if __name__ == "__main__":
    unittest.main()
