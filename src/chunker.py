from hashlib import sha256

from src.schemas import DocumentChunk


def chunk_text(
    text: str,
    source: dict[str, str],
    max_words: int = 180,
    overlap_words: int = 30,
) -> list[DocumentChunk]:
    words = text.split()
    if not words:
        return []
    if overlap_words >= max_words:
        raise ValueError("overlap_words must be smaller than max_words")

    chunks: list[DocumentChunk] = []
    step = max_words - overlap_words
    page_id = str(source.get("page_id") or source.get("url") or source.get("title"))

    for index, start in enumerate(range(0, len(words), step)):
        chunk_words = words[start : start + max_words]
        if not chunk_words:
            continue
        chunk_text_value = " ".join(chunk_words)
        digest = sha256(f"{page_id}:{index}:{chunk_text_value}".encode("utf-8")).hexdigest()
        chunks.append(
            DocumentChunk(
                id=digest[:24],
                text=chunk_text_value,
                metadata={**source, "chunk_index": index},
            )
        )
        if start + max_words >= len(words):
            break

    return chunks
