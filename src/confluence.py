from dataclasses import dataclass
import base64
from html import escape
import json
from html.parser import HTMLParser
from urllib import parse, request

from src.chunker import chunk_text
from src.schemas import DocumentChunk


@dataclass
class ConfluenceSettings:
    base_url: str
    email: str
    api_token: str
    space_key: str | None = None
    cql: str | None = None
    limit: int = 50


@dataclass
class ConfluencePage:
    page_id: str
    title: str
    url: str
    text: str
    metadata: dict[str, str | int | float | bool | None]
    sections: list[tuple[str, str]]


@dataclass
class ConfluenceSection:
    heading: str
    text: str


class ConfluenceClient:
    def __init__(self, settings: ConfluenceSettings):
        self.settings = settings

    def auth_headers(self) -> dict[str, str]:
        raw = f"{self.settings.email}:{self.settings.api_token}".encode("utf-8")
        token = base64.b64encode(raw).decode("ascii")
        return {"Accept": "application/json", "Authorization": f"Basic {token}"}

    def build_search_url(self, start: int = 0) -> str:
        cql = self.settings.cql or _default_cql(self.settings.space_key)
        params = {
            "cql": cql,
            "limit": str(self.settings.limit),
            "start": str(start),
            "expand": "body.storage,version,space",
        }
        return f"{_normalize_base_url(self.settings.base_url)}/rest/api/content/search?{parse.urlencode(params)}"

    def fetch_pages(self) -> list[ConfluencePage]:
        pages: list[ConfluencePage] = []
        start = 0
        while True:
            url = self.build_search_url(start=start)
            req = request.Request(url, headers=self.auth_headers(), method="GET")
            with request.urlopen(req, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))

            batch = parse_search_results(payload, fallback_base_url=self.settings.base_url)
            pages.extend(batch)
            if not batch or len(batch) < self.settings.limit:
                break
            start += self.settings.limit
        return pages

    def create_page(self, title: str, storage_html: str, space_key: str) -> dict:
        payload = build_create_page_payload(space_key, title, storage_html)
        return self._post_json("/rest/api/content", payload)

    def add_label(self, page_id: str, label: str) -> dict:
        payload = [{"prefix": "global", "name": label}]
        return self._post_json(f"/rest/api/content/{page_id}/label", payload)

    def _post_json(self, path: str, payload: dict | list) -> dict:
        url = f"{_normalize_base_url(self.settings.base_url)}{path}"
        body = json.dumps(payload).encode("utf-8")
        headers = {**self.auth_headers(), "Content-Type": "application/json"}
        req = request.Request(url, data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}


def confluence_pages_to_chunks(pages: list[ConfluencePage]) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for page in pages:
        sections = page.sections or [(str(page.metadata.get("section", "Full page")), page.text)]
        for section_heading, section_text in sections:
            chunks.extend(
                chunk_text(
                    section_text,
                    source={
                        "page_id": page.page_id,
                        "title": page.title,
                        "url": page.url,
                        **page.metadata,
                        "section": section_heading,
                    },
                    # Keep hardcoded for the MVP; promote to env config when tuning real KB quality.
                    max_words=450,
                    overlap_words=80,
                )
            )
    return chunks


def build_create_page_payload(
    space_key: str,
    title: str,
    storage_html: str,
    parent_page_id: str | None = None,
) -> dict:
    payload: dict = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": storage_html,
                "representation": "storage",
            }
        },
    }
    if parent_page_id:
        payload["ancestors"] = [{"id": parent_page_id}]
    return payload


def markdown_to_storage_html(markdown: str) -> str:
    html_parts: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            html_parts.append(f"<p>{escape(' '.join(paragraph))}</p>")
            paragraph.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            continue
        if line.startswith("# "):
            flush_paragraph()
            html_parts.append(f"<h1>{escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            flush_paragraph()
            html_parts.append(f"<h2>{escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            flush_paragraph()
            html_parts.append(f"<h3>{escape(line[4:].strip())}</h3>")
        elif line.startswith("- "):
            flush_paragraph()
            html_parts.append(f"<p>&bull; {escape(line[2:].strip())}</p>")
        else:
            paragraph.append(line)

    flush_paragraph()
    return "\n".join(html_parts)


def parse_search_results(
    payload: dict,
    fallback_base_url: str | None = None,
) -> list[ConfluencePage]:
    base_url = (payload.get("_links", {}).get("base") or fallback_base_url or "").rstrip("/")
    pages: list[ConfluencePage] = []
    for item in payload.get("results", []):
        storage = item.get("body", {}).get("storage", {})
        text = html_to_text(str(storage.get("value", "")))
        if not text:
            continue
        sections = html_to_sections(str(storage.get("value", "")))

        webui = item.get("_links", {}).get("webui", "")
        url = f"{base_url}{webui}" if webui.startswith("/") else webui
        version = item.get("version", {})
        space = item.get("space", {})
        title = str(item.get("title", "Untitled"))
        page_id = str(item.get("id", ""))
        pages.append(
            ConfluencePage(
                page_id=page_id,
                title=title,
                url=url,
                text=text,
                sections=[(section.heading, section.text) for section in sections],
                metadata={
                    "space_key": space.get("key"),
                    "version": version.get("number"),
                    "updated_at": version.get("when"),
                    "section": "Full page",
                },
            )
        )
    return pages


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return " ".join(parser.parts).strip()


def html_to_sections(html: str) -> list[ConfluenceSection]:
    parser = _SectionExtractor()
    parser.feed(html)
    parser.close()
    return parser.sections()


def _default_cql(space_key: str | None) -> str:
    parts = ["type=page"]
    if space_key:
        parts.append(f'space="{space_key}"')
    return " and ".join(parts) + " order by lastmodified desc"


def _normalize_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    parsed = parse.urlparse(normalized)
    if parsed.netloc.endswith(".atlassian.net") and not parsed.path:
        return f"{normalized}/wiki"
    return normalized


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.parts.append(stripped)


class _SectionExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current_tag: str | None = None
        self.current_heading: str | None = None
        self.heading_buffer: list[str] = []
        self.content_buffer: list[str] = []
        self.found_heading = False
        self._sections: list[ConfluenceSection] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.current_tag = tag.lower()
        if self.current_tag in {"h1", "h2", "h3"}:
            self.heading_buffer = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"h1", "h2", "h3"}:
            heading = " ".join(self.heading_buffer).strip()
            if tag == "h1" and not self.found_heading:
                self.found_heading = True
            elif heading:
                self._flush_section()
                self.current_heading = heading
                self.found_heading = True
            self.heading_buffer = []
        self.current_tag = None

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if not stripped:
            return
        if self.current_tag in {"h1", "h2", "h3"}:
            self.heading_buffer.append(stripped)
        elif self.current_heading:
            self.content_buffer.append(stripped)

    def sections(self) -> list[ConfluenceSection]:
        self._flush_section()
        return self._sections

    def _flush_section(self) -> None:
        if self.current_heading and self.content_buffer:
            self._sections.append(
                ConfluenceSection(
                    heading=self.current_heading,
                    text=" ".join(self.content_buffer).strip(),
                )
            )
        self.content_buffer = []
