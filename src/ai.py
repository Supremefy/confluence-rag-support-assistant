import json
import re
from urllib import parse, request

from src.config import Settings
from src.prompting import build_support_prompt
from src.schemas import RetrievedChunk


class AiClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def use_mock(self) -> bool:
        return self.settings.use_mock_ai or self.settings.ai_provider == "mock"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.use_mock:
            return [_mock_embedding(text) for text in texts]
        if self.settings.ai_provider == "gemini":
            payload = _gemini_batch_embedding_payload(
                self.settings.gemini_embedding_model,
                texts,
            )
            data = _gemini_post(
                f"/v1beta/models/{self.settings.gemini_embedding_model}:batchEmbedContents",
                payload,
                self.settings.gemini_api_key,
            )
            return [embedding["values"] for embedding in data.get("embeddings", [])]
        if self.settings.ai_provider != "openai":
            raise ValueError("AI_PROVIDER must be 'mock', 'openai', or 'gemini'")

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
            return _mock_answer(question, chunks, risks, tone)

        prompt = build_support_prompt(question=question, chunks=chunks, tone=tone)
        if self.settings.ai_provider == "gemini":
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ]
            }
            data = _gemini_post(
                f"/v1beta/models/{self.settings.gemini_chat_model}:generateContent",
                payload,
                self.settings.gemini_api_key,
            )
            return _extract_gemini_text(data)
        if self.settings.ai_provider != "openai":
            raise ValueError("AI_PROVIDER must be 'mock', 'openai', or 'gemini'")

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
    return _json_post(
        f"https://api.openai.com{path}",
        payload,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )


def _gemini_post(path: str, payload: dict, api_key: str | None) -> dict:
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required when AI_PROVIDER=gemini")
    return _json_post(
        f"https://generativelanguage.googleapis.com{path}?{parse.urlencode({'key': api_key})}",
        payload,
        {"Content-Type": "application/json"},
    )


def _json_post(url: str, payload: dict, headers: dict[str, str]) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _gemini_batch_embedding_payload(model: str, texts: list[str]) -> dict:
    model_name = f"models/{model}"
    return {
        "requests": [
            {
                "model": model_name,
                "content": {"parts": [{"text": text}]},
            }
            for text in texts
        ]
    }


def _extract_gemini_text(payload: dict) -> str:
    texts: list[str] = []
    for candidate in payload.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            text = part.get("text")
            if text:
                texts.append(text)
    return "\n".join(texts).strip()


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


def _mock_answer(question: str, chunks: list[RetrievedChunk], risks: list[str], tone: str = "calm") -> str:
    tone = tone.lower().strip()
    if tone == "concise":
        no_source_reply = (
            "Short answer: I could not find a reliable internal source for this yet. "
            "I will verify it before giving a final response."
        )
        sourced_reply = (
            f"Short answer: this needs review before confirming an outcome for \"{question}\". "
            "Please check order status, service usage, and the applicable refund rules first."
        )
    elif tone == "formal":
        no_source_reply = (
            "Dear customer, I am unable to locate a verified internal source for this request at this stage. "
            "I will arrange for the matter to be reviewed before providing a final response."
        )
        sourced_reply = (
            f"Dear customer, regarding your question, \"{question}\", this request should be assessed against our internal process. "
            "The review should consider the order status, actual service usage, and applicable refund rules before any outcome is confirmed."
        )
    else:
        no_source_reply = (
            "Thank you for reaching out. I could not find a reliable internal source for this question yet. "
            "To avoid giving you incorrect information, I will verify this internally before replying."
        )
        sourced_reply = (
            f"Thank you for reaching out. Regarding your question, \"{question}\", I need to check this against our internal process. "
            "Based on the available policy, this case should be reviewed using the order status, actual service usage, and applicable refund rules. "
            "I can help collect the required details and submit the request for review."
        )

    if not chunks:
        return (
            "Suggested reply\n"
            f"{no_source_reply}\n\n"
            "Internal evidence\nNo matching internal source was found.\n\n"
            "Risk reminders\nDo not promise refunds, compensation, credits, or exceptions without a supporting policy source."
        )

    top = chunks[0]
    title = top.metadata.get("title", "Internal source")
    risk_text = ", ".join(risks) if risks else "No obvious high-risk keyword detected"
    return (
        "Suggested reply\n"
        f"{sourced_reply}\n\n"
        "Internal evidence\n"
        f"- {title}: {top.text[:220]}\n\n"
        "Risk reminders\n"
        f"- Detected risk types: {risk_text}. For refunds, billing, compensation, or contract questions, avoid promising a final outcome directly."
    )
