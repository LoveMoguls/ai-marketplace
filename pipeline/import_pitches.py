"""Batch import MP4 pitch recordings into the marketplace.

Usage:
    python -m pipeline.import_pitches /path/to/pitches/ --source hackathon-010
    python -m pipeline.import_pitches /path/to/pitches/ --source hackathon-010 --create-issues
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests
from dotenv import load_dotenv

from pipeline.transcribe import transcribe
from pipeline.cluster import cluster_ideas

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

EXTRACT_SYSTEM_PROMPT = """You are analyzing a pitch recording transcript from a hackathon or team presentation at SEB (a Nordic bank). The team is presenting an AI idea — a problem they want to solve and their proposed solution.

Extract ALL of the following fields from the transcript. If a field isn't explicitly mentioned, make your best inference from context. Respond with ONLY valid JSON, no markdown fences.

{
  "title": "Short descriptive name for the idea (max 8 words)",
  "problem": "The problem statement — what pain point are they solving?",
  "hypothesis": "Their hypothesis — how would AI help?",
  "business_value": "The business value — what impact would this have?",
  "strategic_area": "One of: Credit, Wealth Management, Payments, Risk & Compliance, Operations, Customer Service, IT & Infrastructure, Other",
  "arch_pattern": "One of: RAG, Inference, Traditional ML, Agentic, Multimodal",
  "tech_components": ["list", "of", "technologies", "mentioned"],
  "summary": "2-3 sentence summary of the full idea",
  "business_value_score": 7,
  "feasibility_score": 5,
  "submitted_by": "Presenter name if mentioned, otherwise null",
  "business_stakeholder": "Division or team if mentioned, otherwise null"
}

Scores: business_value_score 1-10 (how valuable to the bank), feasibility_score 1-10 (how technically feasible).
"""


def extract_from_transcript(transcript: str) -> dict:
    """Send transcript to Claude and extract all idea fields."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=2048,
        system=EXTRACT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Pitch transcript:\n\n{transcript}"}],
    )

    raw = response.content[0].text
    return json.loads(raw)


def create_github_issue(idea: dict, repo: str, token: str) -> int | None:
    """Create a GitHub Issue for an imported idea. Returns issue number."""
    body_parts = [
        f"### Idea title\n\n{idea['title']}",
        f"### Problem statement\n\n{idea.get('problem', 'N/A')}",
        f"### Hypothesis\n\n{idea.get('hypothesis', 'N/A')}",
        f"### Business value\n\n{idea.get('business_value', 'N/A')}",
        f"### Strategic area\n\n{idea.get('strategic_area', 'Other')}",
        f"### Architectural pattern\n\n{idea.get('arch_pattern', 'Not sure')}",
        f"### Current status\n\n{idea.get('status', 'New idea')}",
        f"### Contact name\n\n{idea.get('submitted_by') or '_No response_'}",
        f"### Contact email\n\n{idea.get('contact_email') or '_No response_'}",
        f"### Business stakeholder\n\n{idea.get('business_stakeholder') or '_No response_'}",
        f"### Tech components\n\n{', '.join(idea.get('tech_components', []))}",
        f"### Source\n\n{idea.get('source', 'imported')}",
        f"### Additional details\n\n_Imported from pitch recording. Transcript available in data._",
        f"### Pitch video URL\n\n_No response_",
        f"### Repository URL\n\n_No response_",
        f"### Documentation URL\n\n_No response_",
    ]

    resp = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
        json={
            "title": f"[Idea] {idea['title']}",
            "body": "\n\n".join(body_parts),
            "labels": ["idea"],
        },
    )

    if resp.ok:
        issue_number = resp.json()["number"]
        logger.info("  Created Issue #%d", issue_number)
        return issue_number
    else:
        logger.error("  Failed to create Issue: %s", resp.text)
        return None


def main():
    parser = argparse.ArgumentParser(description="Batch import MP4 pitch recordings")
    parser.add_argument("folder", help="Path to folder containing MP4 files")
    parser.add_argument("--source", default="imported", help="Source tag (e.g. hackathon-010)")
    parser.add_argument("--create-issues", action="store_true", help="Also create GitHub Issues for each idea")
    args = parser.parse_args()

    load_dotenv()

    folder = Path(args.folder)
    if not folder.is_dir():
        logger.error("Not a directory: %s", folder)
        sys.exit(1)

    mp4_files = sorted(folder.glob("*.mp4"))
    if not mp4_files:
        logger.error("No MP4 files found in %s", folder)
        sys.exit(1)

    logger.info("Found %d MP4 files in %s", len(mp4_files), folder)

    # Load existing ideas
    DATA_DIR.mkdir(exist_ok=True)
    ideas_path = DATA_DIR / "ideas.json"
    if ideas_path.exists():
        with open(ideas_path) as f:
            existing = json.load(f)
    else:
        existing = []

    # Find next ID number
    existing_ids = {idea["id"] for idea in existing}
    next_num = 1
    while f"{args.source}-{next_num:03d}" in existing_ids:
        next_num += 1

    repo = os.environ.get("GITHUB_REPO")
    token = os.environ.get("GITHUB_TOKEN")

    new_ideas = []
    for i, mp4_path in enumerate(mp4_files):
        idea_id = f"{args.source}-{next_num:03d}"
        logger.info("[%d/%d] %s → %s", i + 1, len(mp4_files), mp4_path.name, idea_id)

        # Transcribe
        transcript = transcribe(str(mp4_path))
        if not transcript:
            logger.warning("  Skipping — transcription failed")
            continue

        logger.info("  Transcript: %d chars", len(transcript))

        # Extract fields via Claude
        try:
            extracted = extract_from_transcript(transcript)
        except Exception as e:
            logger.error("  Extraction failed: %s", e)
            continue

        # Build idea
        idea = {
            "id": idea_id,
            "issue_number": None,
            "source": args.source,
            "title": extracted.get("title", mp4_path.stem),
            "submitted_by": extracted.get("submitted_by"),
            "contact_email": None,
            "business_stakeholder": extracted.get("business_stakeholder"),
            "submitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "status": "New idea",
            "summary": extracted.get("summary", ""),
            "problem": extracted.get("problem"),
            "hypothesis": extracted.get("hypothesis"),
            "business_value": extracted.get("business_value"),
            "strategic_area": extracted.get("strategic_area", "Other"),
            "arch_pattern": extracted.get("arch_pattern", "Inference"),
            "tech_components": extracted.get("tech_components", []),
            "cluster_id": None,
            "cluster_label": None,
            "enabler_candidate": False,
            "scores": {
                "business_value": extracted.get("business_value_score", 5),
                "feasibility": extracted.get("feasibility_score", 5),
            },
            "links": {"pitch_url": None, "repo_url": None, "docs_url": None},
            "transcript": transcript,
            "upvotes": 0,
            "issue_url": None,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Optionally create GitHub Issue
        if args.create_issues and repo and token:
            issue_number = create_github_issue(idea, repo, token)
            if issue_number:
                idea["issue_number"] = issue_number
                idea["issue_url"] = f"https://github.com/{repo}/issues/{issue_number}"

        new_ideas.append(idea)
        next_num += 1

        logger.info("  ✓ %s — %s", idea["title"], idea["strategic_area"])

    if not new_ideas:
        logger.info("No ideas extracted.")
        return

    # Merge with existing
    all_ideas = existing + new_ideas

    # Cluster everything
    logger.info("Clustering %d ideas...", len(all_ideas))
    all_ideas, clusters = cluster_ideas(all_ideas)

    # Write output
    with open(DATA_DIR / "ideas.json", "w") as f:
        json.dump(all_ideas, f, indent=2)

    with open(DATA_DIR / "clusters.json", "w") as f:
        json.dump(clusters, f, indent=2)

    enablers = sum(1 for i in all_ideas if i.get("enabler_candidate"))
    logger.info("Done: %d new ideas imported (%d total), %d clusters, %d enablers",
                len(new_ideas), len(all_ideas), len(clusters), enablers)
    logger.info("Next: git add data/ && git commit -m 'import: %s' && git push", args.source)


if __name__ == "__main__":
    main()
