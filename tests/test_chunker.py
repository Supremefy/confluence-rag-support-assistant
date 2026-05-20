import unittest

from src.chunker import chunk_text


class ChunkerTests(unittest.TestCase):
    def test_chunk_text_preserves_metadata_and_creates_overlapping_chunks(self):
        text = " ".join(f"word{i}" for i in range(18))
        chunks = chunk_text(
            text,
            source={
                "page_id": "refund-policy",
                "title": "Refund Policy",
                "url": "https://example.test/refund",
            },
            max_words=8,
            overlap_words=2,
        )

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].text, "word0 word1 word2 word3 word4 word5 word6 word7")
        self.assertTrue(chunks[1].text.startswith("word6 word7"))
        self.assertEqual(chunks[0].metadata["title"], "Refund Policy")
        self.assertEqual(chunks[0].metadata["chunk_index"], 0)


if __name__ == "__main__":
    unittest.main()
