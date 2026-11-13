"""Validation tests for the Open Knowledge Format (OKF v0.2) bundle under docs/."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"

ALLOWED_STATUSES = {"draft", "stable", "deprecated"}
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
DATE_HEADING_RE = re.compile(r"^## \d{4}-\d{2}-\d{2}\b", re.MULTILINE)


def _extract_frontmatter_keys(content: str) -> dict[str, str]:
    """Parse top-level YAML frontmatter keys without external dependencies."""
    match = FRONTMATTER_RE.match(content)
    assert match is not None, "Missing YAML frontmatter delimited by ---"

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line[0].isspace():
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def test_okf_reserved_files_exist() -> None:
    """Bundle root must declare okf_version 0.2 in index.md and include log.md."""
    root_index = DOCS_ROOT / "index.md"
    root_log = DOCS_ROOT / "log.md"

    assert root_index.is_file(), "Missing bundle root docs/index.md"
    assert root_log.is_file(), "Missing reserved changelog docs/log.md"

    index_fields = _extract_frontmatter_keys(root_index.read_text(encoding="utf-8"))
    assert index_fields.get("okf_version") == "0.2"
    assert index_fields.get("type") == "index"

    log_text = root_log.read_text(encoding="utf-8")
    log_fields = _extract_frontmatter_keys(log_text)
    assert log_fields.get("type") == "log"
    assert DATE_HEADING_RE.search(log_text) is not None, "docs/log.md needs ## YYYY-MM-DD entries"


def test_all_docs_have_valid_okf_frontmatter() -> None:
    """Every markdown document in docs/ must expose core OKF v0.2 metadata."""
    md_files = sorted(DOCS_ROOT.rglob("*.md"))
    assert md_files, "Expected markdown files under docs/"

    for md_file in md_files:
        rel = md_file.relative_to(REPO_ROOT)
        fields = _extract_frontmatter_keys(md_file.read_text(encoding="utf-8"))

        for required in ("type", "title", "description", "status"):
            assert fields.get(required), (
                f"{rel} is missing non-empty frontmatter field '{required}'"
            )

        status = fields["status"]
        assert status in ALLOWED_STATUSES, f"{rel} has invalid status '{status}'"

        if fields["type"] == "study-note" and md_file.name != "_template.md":
            assert "sources" in fields, f"{rel} (study-note) must declare 'sources'"
            assert "verified" in fields, f"{rel} (study-note) must declare 'verified'"


def test_okf_internal_markdown_links_resolve() -> None:
    """All relative markdown links in docs/ must point to existing files."""
    for md_file in sorted(DOCS_ROOT.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        for raw_target in MD_LINK_RE.findall(content):
            target = raw_target.strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", maxsplit=1)[0]
            if not path_part:
                continue
            resolved = (md_file.parent / path_part).resolve()
            assert resolved.exists(), (
                f"Broken relative link '{raw_target}' in {md_file.relative_to(REPO_ROOT)}"
            )
