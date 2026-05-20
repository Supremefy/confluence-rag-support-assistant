import unittest

from src.risk import classify_risks


class RiskTests(unittest.TestCase):
    def test_classify_risks_flags_sensitive_support_topics(self):
        risks = classify_risks("Customer asks for refund and compensation after a billing issue")

        self.assertIn("refund", risks)
        self.assertIn("compensation", risks)
        self.assertIn("billing", risks)

    def test_classify_risks_returns_empty_list_for_general_question(self):
        self.assertEqual(classify_risks("How do I reset my password?"), [])


if __name__ == "__main__":
    unittest.main()
