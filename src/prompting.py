from src.schemas import RetrievedChunk


def build_support_prompt(question: str, chunks: list[RetrievedChunk], tone: str) -> str:
    context_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        title = chunk.metadata.get("title", "Untitled")
        section = chunk.metadata.get("section", "General")
        url = chunk.metadata.get("url", "")
        context_blocks.append(
            f"[{index}] Title: {title}\nSection: {section}\nURL: {url}\nContent: {chunk.text}"
        )

    context = "\n\n".join(context_blocks) or "No internal context was found."
    return f"""You are an internal assistant for customer support agents.
Use the internal context to draft a reply the agent can edit before sending.
You must not invent policy details. If the context is insufficient, say that no reliable internal source was found.
Do not expose internal-only notes verbatim to the customer. Convert them into customer-safe wording.

Tone: {tone}

Customer question:
{question}

Internal context:
{context}

Return the response in English with these sections:
Suggested reply
Internal evidence
Risk reminders
"""
