"""Parse GitHub Issue body markdown into structured dict."""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Mapping from Issue markdown headers to output dict keys.
HEADER_MAP: dict[str, str] = {
    "Idea title": "title",
    "Problem statement": "problem",
    "Hypothesis": "hypothesis",
    "Business value": "business_value",
    "Strategic area": "strategic_area",
    "Architectural pattern": "arch_pattern",
    "Current status": "status",
    "Contact name": "contact_name",
    "Contact email": "contact_email",
    "Business stakeholder": "business_stakeholder",
    "Tech components": "tech_components",
    "Source": "source",
    "Additional details": "extra_context",
    "Pitch video URL": "pitch_url",
    "Repository URL": "repo_url",
    "Documentation URL": "docs_url",
}

_NO_RESPONSE = "_No response_"


def _clean_value(raw: str) -> Optional[str]:
    """Strip whitespace and return None for empty or '_No response_' values."""
    value = raw.strip()
    if not value or value == _NO_RESPONSE:
        return None
    return value


def _parse_sections(body: str) -> dict[str, str]:
    """Split a markdown body into {header: raw_content} pairs."""
    sections: dict[str, str] = {}
    # Match ### headers and capture content until next ### or end.
    pattern = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(body))

    for i, match in enumerate(matches):
        header = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[start:end]
        sections[header] = content

    return sections


def parse_issue_body(body: str) -> dict[str, object]:
    """Parse a GitHub Issue body into a structured dict.

    Extracts fields from ``### Header`` sections in the markdown body
    produced by GitHub Issue forms.

    Args:
        body: The raw markdown body of a GitHub Issue.

    Returns:
        A dict with standardised keys. Missing or empty fields are None,
        except ``tech_components`` which defaults to an empty list.
    """
    result: dict[str, object] = {key: None for key in HEADER_MAP.values()}
    result["tech_components"] = []

    if not body or not body.strip():
        logger.debug("Empty issue body, returning defaults")
        return result

    sections = _parse_sections(body)
    logger.debug("Parsed %d sections from issue body", len(sections))

    for header, dict_key in HEADER_MAP.items():
        raw = sections.get(header)
        if raw is None:
            continue

        if dict_key == "tech_components":
            cleaned = _clean_value(raw)
            if cleaned:
                result["tech_components"] = [
                    c.strip() for c in cleaned.split(",") if c.strip()
                ]
        else:
            result[dict_key] = _clean_value(raw)

    return result
