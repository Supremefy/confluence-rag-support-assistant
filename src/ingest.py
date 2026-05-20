from pathlib import Path

from src.chunker import chunk_text
from src.schemas import DocumentChunk


def load_markdown_documents(directory: Path) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for path in sorted(directory.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        title = _extract_title(raw) or path.stem.replace("-", " ").title()
        source = {
            "page_id": path.stem,
            "title": title,
            "url": f"local://sample-docs/{path.name}",
            "section": "Sample Confluence export",
        }
        chunks.extend(chunk_text(_markdown_to_text(raw), source=source))
    return chunks


def _extract_title(markdown: str) -> str | None:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _markdown_to_text(markdown: str) -> str:
    lines = []
    for line in markdown.splitlines():
        cleaned = line.strip().lstrip("#").strip()
        if cleaned:
            lines.append(cleaned)
    return " ".join(lines)
