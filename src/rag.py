from src.ai import AiClient
from src.risk import classify_risks
from src.schemas import AskResponse, Source
from src.vector_store import VectorStore


class RagService:
    def __init__(self, ai_client: AiClient, vector_store: VectorStore):
        self.ai_client = ai_client
        self.vector_store = vector_store

    def answer(self, question: str, tone: str = "calm") -> AskResponse:
        risks = classify_risks(question)
        chunks = self.vector_store.search(question, limit=5)
        answer = self.ai_client.generate_support_answer(question, chunks, tone, risks)
        sources = [
            Source(
                title=str(chunk.metadata.get("title", "Untitled")),
                url=str(chunk.metadata.get("url", "")),
                section=(
                    str(chunk.metadata.get("section"))
                    if chunk.metadata.get("section") is not None
                    else None
                ),
                score=round(chunk.score, 3),
            )
            for chunk in chunks
        ]
        return AskResponse(
            answer=answer,
            risks=risks,
            sources=sources,
            used_mock_ai=self.ai_client.use_mock,
        )
