import unittest

from src.ai import (
    _extract_gemini_text,
    _gemini_batch_embedding_payload,
    _mock_answer,
    _mock_embedding,
)
from src.schemas import RetrievedChunk
from src.vector_store import _cosine_similarity


class MockEmbeddingTests(unittest.TestCase):
    def test_mock_embedding_matches_related_refund_text_better(self):
        query = _mock_embedding("Can the customer get a refund after using the service?")
        refund = _mock_embedding("Refund policy used service do not promise a full refund")
        account = _mock_embedding("Account login verification code email single sign-on")

        self.assertGreater(
            _cosine_similarity(query, refund),
            _cosine_similarity(query, account),
        )



class MockAnswerTests(unittest.TestCase):
    def test_mock_answer_changes_with_reply_tone(self):
        chunk = RetrievedChunk(
            text="Used services require refund review before promising an outcome.",
            score=0.9,
            metadata={"title": "Refund Policy"},
        )

        calm = _mock_answer("Can we offer a full refund?", [chunk], ["refund"], "calm")
        concise = _mock_answer("Can we offer a full refund?", [chunk], ["refund"], "concise")
        formal = _mock_answer("Can we offer a full refund?", [chunk], ["refund"], "formal")

        self.assertIn("Thank you for reaching out", calm)
        self.assertIn("Short answer", concise)
        self.assertIn("Dear customer", formal)
        self.assertNotEqual(calm, concise)
        self.assertNotEqual(calm, formal)


class GeminiHelperTests(unittest.TestCase):
    def test_gemini_batch_embedding_payload_wraps_each_text(self):
        payload = _gemini_batch_embedding_payload("gemini-embedding-001", ["one", "two"])

        self.assertEqual(len(payload["requests"]), 2)
        self.assertEqual(payload["requests"][0]["model"], "models/gemini-embedding-001")
        self.assertEqual(payload["requests"][0]["content"]["parts"][0]["text"], "one")
        self.assertEqual(payload["requests"][1]["content"]["parts"][0]["text"], "two")

    def test_extract_gemini_text_collects_candidate_parts(self):
        payload = {
            "candidates": [
                {"content": {"parts": [{"text": "Hello"}, {"text": " world"}]}}
            ]
        }

        self.assertEqual(_extract_gemini_text(payload), "Hello\n world")

if __name__ == "__main__":
    unittest.main()
