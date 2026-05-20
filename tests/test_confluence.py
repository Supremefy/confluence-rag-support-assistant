import base64
import unittest

from src.confluence import (
    ConfluenceClient,
    ConfluencePage,
    ConfluenceSettings,
    build_create_page_payload,
    confluence_pages_to_chunks,
    html_to_sections,
    markdown_to_storage_html,
    parse_search_results,
)


class ConfluenceClientTests(unittest.TestCase):
    def test_build_search_url_uses_space_key_and_limit(self):
        client = ConfluenceClient(
            ConfluenceSettings(
                base_url="https://example.atlassian.net/wiki",
                email="agent@example.com",
                api_token="token",
                space_key="SUPPORT",
                limit=25,
            )
        )

        url = client.build_search_url()

        self.assertIn("/rest/api/content/search", url)
        self.assertIn("space%3D%22SUPPORT%22", url)
        self.assertIn("type%3Dpage", url)
        self.assertIn("limit=25", url)
        self.assertIn("expand=body.storage%2Cversion%2Cspace", url)

    def test_build_search_url_adds_wiki_path_for_atlassian_cloud_site_root(self):
        client = ConfluenceClient(
            ConfluenceSettings(
                base_url="https://example.atlassian.net",
                email="agent@example.com",
                api_token="token",
                space_key="SUPPORT",
            )
        )

        url = client.build_search_url()

        self.assertTrue(url.startswith("https://example.atlassian.net/wiki/rest/api/"))

    def test_auth_header_uses_basic_auth(self):
        client = ConfluenceClient(
            ConfluenceSettings(
                base_url="https://example.atlassian.net/wiki",
                email="agent@example.com",
                api_token="token",
                space_key="SUPPORT",
            )
        )

        headers = client.auth_headers()
        expected = base64.b64encode(b"agent@example.com:token").decode("ascii")

        self.assertEqual(headers["Authorization"], f"Basic {expected}")
        self.assertEqual(headers["Accept"], "application/json")


class ConfluenceParsingTests(unittest.TestCase):
    def test_parse_search_results_extracts_page_text_and_metadata(self):
        payload = {
            "results": [
                {
                    "id": "123",
                    "title": "Refund Policy",
                    "_links": {"webui": "/spaces/SUPPORT/pages/123/Refund+Policy"},
                    "space": {"key": "SUPPORT"},
                    "version": {"number": 7, "when": "2026-05-19T01:02:03.000Z"},
                    "body": {
                        "storage": {
                            "value": "<h1>Refund Policy</h1><p>Customers may request a refund.</p>"
                        }
                    },
                }
            ],
            "_links": {"base": "https://example.atlassian.net/wiki"},
        }

        pages = parse_search_results(payload)

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].title, "Refund Policy")
        self.assertEqual(pages[0].text, "Refund Policy Customers may request a refund.")
        self.assertEqual(
            pages[0].url,
            "https://example.atlassian.net/wiki/spaces/SUPPORT/pages/123/Refund+Policy",
        )
        self.assertEqual(pages[0].metadata["space_key"], "SUPPORT")
        self.assertEqual(pages[0].metadata["version"], 7)

    def test_html_to_sections_groups_content_under_headings(self):
        sections = html_to_sections(
            "<h1>Refund Policy</h1>"
            "<h2>Summary</h2><p>Customers may request a refund.</p>"
            "<h2>Escalation</h2><p>Escalate disputes.</p>"
        )

        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0].heading, "Summary")
        self.assertEqual(sections[0].text, "Customers may request a refund.")
        self.assertEqual(sections[1].heading, "Escalation")
        self.assertEqual(sections[1].text, "Escalate disputes.")

    def test_confluence_pages_to_chunks_uses_section_metadata(self):
        page = ConfluencePage(
            page_id="123",
            title="Refund Policy",
            url="https://example.test/refund",
            text="Refund Policy Summary Customers may request a refund. Escalation Escalate disputes.",
            sections=[
                ("Summary", "Customers may request a refund."),
                ("Escalation", "Escalate disputes."),
            ],
            metadata={"space_key": "SUPPORT", "section": "Confluence page"},
        )

        chunks = confluence_pages_to_chunks([page])

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].metadata["section"], "Summary")
        self.assertEqual(chunks[1].metadata["section"], "Escalation")


class ConfluencePublishingTests(unittest.TestCase):
    def test_markdown_to_storage_html_converts_headings_and_paragraphs(self):
        html = markdown_to_storage_html(
            "# Refund Policy\n\n## Summary\n\nCustomers may request a refund."
        )

        self.assertIn("<h1>Refund Policy</h1>", html)
        self.assertIn("<h2>Summary</h2>", html)
        self.assertIn("<p>Customers may request a refund.</p>", html)

    def test_build_create_page_payload_uses_storage_representation(self):
        payload = build_create_page_payload(
            space_key="SD",
            title="Refund Policy",
            storage_html="<h1>Refund Policy</h1>",
        )

        self.assertEqual(payload["type"], "page")
        self.assertEqual(payload["title"], "Refund Policy")
        self.assertEqual(payload["space"]["key"], "SD")
        self.assertEqual(payload["body"]["storage"]["representation"], "storage")
        self.assertEqual(payload["body"]["storage"]["value"], "<h1>Refund Policy</h1>")


if __name__ == "__main__":
    unittest.main()
