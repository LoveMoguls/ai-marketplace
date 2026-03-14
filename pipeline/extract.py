"""Extract and enrich idea fields using Claude API."""
import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI idea analyst. Given an idea submission, produce a JSON object with:
- "summary": 2-3 sentence summary of the idea
- "arch_pattern": normalized to exactly one of: RAG, Inference, Traditional ML, Agentic, Multimodal
- "business_value_score": integer 1-10 rating of business value
- "feasibility_score": integer 1-10 rating of technical feasibility

Respond with ONLY valid JSON, no markdown fences."""


def extract_idea(issue_fields: dict, transcript: str | None) -> dict:
    """Call Claude API to extract enriched fields from an idea submission.

    Returns dict with summary, normalized arch_pattern, and scores.
    """
    parts = []
    for key in ("title", "problem", "hypothesis", "business_value", "strategic_area", "arch_pattern"):
        val = issue_fields.get(key)
        if val:
            parts.append(f"{key}: {val}")

    tech = issue_fields.get("tech_components", [])
    if tech:
        parts.append(f"tech_components: {', '.join(tech)}")

    if transcript:
        parts.append(f"\nPitch transcript:\n{transcript}")

    user_content = "\n".join(parts)

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = response.content[0].text
    data = json.loads(raw)

    return {
        "summary": data["summary"],
        "arch_pattern": data["arch_pattern"],
        "scores": {
            "business_value": data["business_value_score"],
            "feasibility": data["feasibility_score"],
        },
    }
