from dataclasses import dataclass, field


@dataclass
class DocumentChunk:
    id: str
    text: str
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    text: str
    score: float
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)


@dataclass
class AskRequest:
    question: str
    tone: str = "calm"


@dataclass
class Source:
    title: str
    url: str
    score: float
    section: str | None = None


@dataclass
class AskResponse:
    answer: str
    risks: list[str]
    sources: list[Source]
    used_mock_ai: bool
