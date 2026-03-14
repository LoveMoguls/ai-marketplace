"""Main pipeline entrypoint — fetch Issues, process, cluster, write output."""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from pipeline.parse_issue import parse_issue_body
from pipeline.transcribe import transcribe
from pipeline.extract import extract_idea
from pipeline.cluster import cluster_ideas

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = Path(__file__).parent.parent / "raw" / "pitches"


def fetch_issues(repo: str, token: str) -> list[dict]:
    """Fetch all Issues with label 'idea' from GitHub API."""
    issues = []
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/issues",
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
            params={"labels": "idea", "state": "all", "per_page": 100, "page": page},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        issues.extend(batch)
        page += 1
    logger.info("Fetched %d issues from GitHub", len(issues))
    return issues


def load_existing_ideas() -> list[dict]:
    """Load existing ideas.json or return empty list."""
    path = DATA_DIR / "ideas.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def process_issue(issue: dict, source: str, dry_run: bool = False) -> dict:
    """Process a single GitHub Issue into an idea dict."""
    issue_number = issue["number"]
    body = issue.get("body", "") or ""
    fields = parse_issue_body(body)

    # Transcription
    mp4_path = RAW_DIR / f"{issue_number}.mp4"
    transcript = None
    if not dry_run:
        transcript = transcribe(str(mp4_path))

    # Extraction
    if dry_run:
        enriched = {
            "summary": f"[DRY RUN] {fields.get('title', 'Untitled')}",
            "arch_pattern": fields.get("arch_pattern", "Inference"),
            "scores": {"business_value": 5, "feasibility": 5},
        }
    else:
        enriched = extract_idea(fields, transcript)

    idea_id = f"{source}-{issue_number:03d}" if source else f"issue-{issue_number:03d}"

    return {
        "id": idea_id,
        "issue_number": issue_number,
        "source": fields.get("source") or source or "github",
        "title": fields.get("title") or issue.get("title", "").replace("[Idea] ", ""),
        "submitted_by": fields.get("contact_name"),
        "contact_email": fields.get("contact_email"),
        "business_stakeholder": fields.get("business_stakeholder"),
        "submitted_at": issue.get("created_at", "")[:10],
        "status": fields.get("status", "New idea"),
        "summary": enriched["summary"],
        "problem": fields.get("problem"),
        "hypothesis": fields.get("hypothesis"),
        "business_value": fields.get("business_value"),
        "strategic_area": fields.get("strategic_area"),
        "arch_pattern": enriched["arch_pattern"],
        "tech_components": fields.get("tech_components", []),
        "cluster_id": None,
        "cluster_label": None,
        "enabler_candidate": False,
        "scores": enriched["scores"],
        "links": {
            "pitch_url": fields.get("pitch_url"),
            "repo_url": fields.get("repo_url"),
            "docs_url": fields.get("docs_url"),
        },
        "transcript": transcript,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Process AI idea submissions")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls, use mock data")
    args = parser.parse_args()

    load_dotenv()

    repo = os.environ.get("GITHUB_REPO")
    token = os.environ.get("GITHUB_TOKEN")

    if not repo or not token:
        logger.error("GITHUB_REPO and GITHUB_TOKEN must be set in .env")
        sys.exit(1)

    DATA_DIR.mkdir(exist_ok=True)

    issues = fetch_issues(repo, token)
    existing = load_existing_ideas()
    existing_numbers = {idea["issue_number"] for idea in existing}

    new_count = 0
    for issue in issues:
        if issue["number"] in existing_numbers:
            continue
        idea = process_issue(issue, source="github", dry_run=args.dry_run)
        existing.append(idea)
        new_count += 1
        logger.info("Processed: %s", idea["title"])

    if not existing:
        logger.info("No ideas to process.")
        return

    # Cluster all ideas
    if args.dry_run:
        for idea in existing:
            idea["cluster_id"] = 0
            idea["cluster_label"] = "unclustered"
        clusters = [{"id": 0, "label": "unclustered", "idea_ids": [i["id"] for i in existing], "shared_components": [], "description": "All ideas (dry run)."}]
    else:
        existing, clusters = cluster_ideas(existing)

    # Write output
    with open(DATA_DIR / "ideas.json", "w") as f:
        json.dump(existing, f, indent=2)

    with open(DATA_DIR / "clusters.json", "w") as f:
        json.dump(clusters, f, indent=2)

    enabler_count = sum(1 for i in existing if i.get("enabler_candidate"))
    logger.info("Done: %d total ideas (%d new), %d clusters, %d enabler candidates",
                len(existing), new_count, len(clusters), enabler_count)


if __name__ == "__main__":
    main()
