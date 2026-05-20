from dataclasses import asdict
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from src.ai import AiClient
from src.config import get_settings, require_confluence_settings
from src.confluence import ConfluenceClient, confluence_pages_to_chunks
from src.ingest import load_markdown_documents
from src.rag import RagService
from src.vector_store import VectorStore


settings = get_settings()
ai_client = AiClient(settings)
vector_store = VectorStore(settings, ai_client)
rag_service = RagService(ai_client, vector_store)


class SupportRagHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self._send_file(Path("public/index.html"), "text/html; charset=utf-8")
            return
        if self.path == "/api/health":
            self._send_json({"status": "ok", "mock_ai": ai_client.use_mock})
            return
        if self.path.startswith("/static/"):
            relative = unquote(self.path.removeprefix("/static/"))
            path = Path("public") / relative
            content_type = _content_type(path)
            self._send_file(path, content_type)
            return
        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        if self.path == "/api/ingest-samples":
            vector_store.clear()
            chunks = load_markdown_documents(Path("data/sample-docs"))
            count = vector_store.upsert_chunks(chunks)
            self._send_json({"chunks_indexed": count})
            return
        if self.path == "/api/ingest-confluence":
            try:
                confluence_settings = require_confluence_settings(settings)
                pages = ConfluenceClient(confluence_settings).fetch_pages()
                chunks = confluence_pages_to_chunks(pages)
                vector_store.clear()
                count = vector_store.upsert_chunks(chunks)
                self._send_json({"pages_indexed": len(pages), "chunks_indexed": count})
            except Exception as error:
                self._send_json({"error": str(error)}, status=400)
            return
        if self.path == "/api/ask":
            payload = self._read_json()
            question = str(payload.get("question", "")).strip()
            tone = str(payload.get("tone", "calm"))
            if not question:
                self._send_json({"error": "question is required"}, status=400)
                return
            response = rag_service.answer(question, tone)
            self._send_json(asdict(response))
            return
        self._send_json({"error": "Not found"}, status=404)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "Not found"}, status=404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _content_type(path: Path) -> str:
    if path.suffix == ".css":
        return "text/css; charset=utf-8"
    if path.suffix == ".js":
        return "application/javascript; charset=utf-8"
    if path.suffix == ".html":
        return "text/html; charset=utf-8"
    return "application/octet-stream"


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), SupportRagHandler)
    print(f"Customer Support RAG Demo running at http://{host}:{port}")
    print(f"Mock AI: {ai_client.use_mock}")
    server.serve_forever()
