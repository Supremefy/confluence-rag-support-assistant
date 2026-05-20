import unittest

from src.prompting import build_support_prompt
from src.schemas import RetrievedChunk


class PromptingTests(unittest.TestCase):
    def test_build_support_prompt_includes_context_and_requires_sources(self):
        prompt = build_support_prompt(
            question="Can the customer get a full refund?",
            chunks=[
                RetrievedChunk(
                    text="Refunds within 14 days may be reviewed if service was used.",
                    score=0.91,
                    metadata={
                        "title": "Refund Policy",
                        "url": "https://example.test/refund",
                        "section": "Used service",
                    },
                )
            ],
            tone="calm",
        )

        self.assertIn("Can the customer get a full refund?", prompt)
        self.assertIn("Refund Policy", prompt)
        self.assertIn("must not invent", prompt)
        self.assertIn("Suggested reply", prompt)


if __name__ == "__main__":
    unittest.main()
