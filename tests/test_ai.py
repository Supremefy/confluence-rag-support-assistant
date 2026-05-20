import unittest

from src.ai import _mock_embedding
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


if __name__ == "__main__":
    unittest.main()
