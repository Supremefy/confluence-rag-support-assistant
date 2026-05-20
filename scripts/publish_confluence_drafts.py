from argparse import ArgumentParser
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import get_settings, require_confluence_settings
from src.confluence import ConfluenceClient, markdown_to_storage_html


DRAFT_DIR = ROOT / "data" / "confluence-drafts"
DEFAULT_LABEL = "support-kb"


def main() -> None:
    parser = ArgumentParser(description="Publish local markdown drafts to Confluence.")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Actually create pages in Confluence. Without this flag, the script only previews.",
    )
    parser.add_argument(
        "--label",
        default=DEFAULT_LABEL,
        help=f"Label to add to created pages. Defaults to {DEFAULT_LABEL}.",
    )
    parser.add_argument(
        "--parent-page-id",
        default=None,
        help="Optional Confluence parent page ID for created pages.",
    )
    args = parser.parse_args()

    settings = get_settings()
    confluence_settings = require_confluence_settings(settings)
    if not confluence_settings.space_key:
        raise RuntimeError("CONFLUENCE_SPACE_KEY is required to publish draft pages")

    drafts = sorted(DRAFT_DIR.glob("*.md"))
    if not drafts:
        print(f"No markdown drafts found in {DRAFT_DIR}")
        return

    client = ConfluenceClient(confluence_settings)
    mode = "PUBLISH" if args.publish else "DRY RUN"
    print(f"{mode}: {len(drafts)} draft pages")
    print(f"Space: {confluence_settings.space_key}")
    print(f"Label: {args.label}")

    for path in drafts:
        markdown = path.read_text(encoding="utf-8")
        title = _extract_title(markdown) or path.stem.replace("-", " ").title()
        print(f"- {title}")

        if not args.publish:
            continue

        storage_html = markdown_to_storage_html(markdown)
        response = client.create_page(
            title=title,
            storage_html=storage_html,
            space_key=confluence_settings.space_key,
        )
        page_id = str(response["id"])
        client.add_label(page_id, args.label)
        print(f"  created page id: {page_id}")

    if not args.publish:
        print("No pages were created. Re-run with --publish to write to Confluence.")


def _extract_title(markdown: str) -> str | None:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


if __name__ == "__main__":
    main()
