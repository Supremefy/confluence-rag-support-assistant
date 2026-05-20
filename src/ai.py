import json
import re
from urllib import request

from src.config import Settings
from src.prompting import build_support_prompt
from src.schemas import RetrievedChunk


class AiClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def use_mock(self) -> bool:
        return self.settings.use_mock_ai or self.settings.openai_api_key is None

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.use_mock:
            return [_mock_embedding(text) for text in texts]

        payload = {"model": self.settings.openai_embedding_model, "input": texts}
        data = _openai_post("/v1/embeddings", payload, self.settings.openai_api_key)
        return [item["embedding"] for item in data["data"]]

    def generate_support_answer(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        tone: str,
        risks: list[str],
    ) -> str:
        if self.use_mock:
            return _mock_answer(question, chunks, risks)

        prompt = build_support_prompt(question=question, chunks=chunks, tone=tone)
        payload = {"model": self.settings.openai_chat_model, "input": prompt}
        data = _openai_post("/v1/responses", payload, self.settings.openai_api_key)
        output = data.get("output", [])
        texts: list[str] = []
        for item in output:
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    texts.append(content.get("text", ""))
        return "\n".join(texts).strip() or data.get("output_text", "")


def _openai_post(path: str, payload: dict, api_key: str | None) -> dict:
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required when USE_MOCK_AI=false")
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"https://api.openai.com{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _mock_embedding(text: str, dimensions: int = 64) -> list[float]:
    vector = [0.0] * dimensions
    for token in _tokenize_for_mock_embedding(text):
        bucket = sum(ord(char) for char in token) % dimensions
        vector[bucket] += 1.0
    length = sum(value * value for value in vector) ** 0.5 or 1.0
    return [value / length for value in vector]


def _tokenize_for_mock_embedding(text: str) -> list[str]:
    lowered = text.lower()
    ascii_words = re.findall(r"[a-z0-9]+", lowered)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", lowered)
    cjk_bigrams = [left + right for left, right in zip(cjk_chars, cjk_chars[1:])]
    return ascii_words + cjk_chars + cjk_bigrams


def _mock_answer(question: str, chunks: list[RetrievedChunk], risks: list[str]) -> str:
    if not chunks:
        return (
            "Suggested reply\n"
            "Hello, I could not find a reliable internal source for this question yet. "
            "To avoid giving you incorrect information, I will verify this internally before replying.\n\n"
            "Internal evidence\nNo matching internal source was found.\n\n"
            "Risk reminders\nDo not promise refunds, compensation, credits, or exceptions without a supporting policy source."
        )

    top = chunks[0]
    title = top.metadata.get("title", "Internal source")
    risk_text = ", ".join(risks) if risks else "No obvious high-risk keyword detected"
    return (
        "Suggested reply\n"
        f"Hello, regarding your question, \"{question}\", I need to check this against our internal process. "
        "Based on the available policy, this case should be reviewed using the order status, actual service usage, and applicable refund rules. "
        "I can help collect the required details and submit the request for review.\n\n"
        "Internal evidence\n"
        f"- {title}: {top.text[:220]}\n\n"
        "Risk reminders\n"
        f"- Detected risk types: {risk_text}. For refunds, billing, compensation, or contract questions, avoid promising a final outcome directly."
    )
