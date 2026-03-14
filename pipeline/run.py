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
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.full+json"},
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

    # Transcription + document reading (lazy imports, only when files exist)
    mp4_path = RAW_DIR / f"{issue_number}.mp4"
    transcript = None
    doc_text = None
    if not dry_run and mp4_path.exists():
        from pipeline.transcribe import transcribe
        transcript = transcribe(str(mp4_path))
    if not dry_run:
        # Check for documents (PDF, DOCX, PPTX)
        from pipeline.read_doc import SUPPORTED_EXTENSIONS, read_document
        for ext in SUPPORTED_EXTENSIONS:
            doc_path = RAW_DIR / f"{issue_number}{ext}"
            if doc_path.exists():
                doc_text = read_document(str(doc_path))
                if doc_text:
                    break

    # Combine all extra context: transcript, document, pasted text
    context_parts = []
    if transcript:
        context_parts.append(f"--- Pitch transcript ---\n\n{transcript}")
    if doc_text:
        context_parts.append(f"--- Document content ---\n\n{doc_text}")
    pasted_text = fields.get("extra_context")
    if pasted_text:
        context_parts.append(f"--- Additional details ---\n\n{pasted_text}")
    extra_context = "\n\n".join(context_parts) if context_parts else None

    # Extraction
    if dry_run:
        enriched = {
            "summary": f"[DRY RUN] {fields.get('title', 'Untitled')}",
            "arch_pattern": fields.get("arch_pattern", "Inference"),
            "scores": {"business_value": 5, "feasibility": 5},
        }
    else:
        from pipeline.extract import extract_idea
        enriched = extract_idea(fields, extra_context)

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
        "transcript": extra_context,
        "upvotes": issue.get("reactions", {}).get("+1", 0),
        "issue_url": issue.get("html_url"),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }


def sync_issue(issue: dict, existing_idea: dict) -> dict:
    """Update human-editable fields from Issue without calling Claude.

    Preserves AI-generated fields (summary, scores, cluster, transcript).
    """
    body = issue.get("body", "") or ""
    fields = parse_issue_body(body)

    existing_idea["title"] = fields.get("title") or issue.get("title", "").replace("[Idea] ", "")
    existing_idea["submitted_by"] = fields.get("contact_name") or existing_idea.get("submitted_by")
    existing_idea["contact_email"] = fields.get("contact_email") or existing_idea.get("contact_email")
    existing_idea["business_stakeholder"] = fields.get("business_stakeholder") or existing_idea.get("business_stakeholder")
    existing_idea["status"] = fields.get("status") or existing_idea.get("status", "New idea")
    existing_idea["problem"] = fields.get("problem") or existing_idea.get("problem")
    existing_idea["hypothesis"] = fields.get("hypothesis") or existing_idea.get("hypothesis")
    existing_idea["business_value"] = fields.get("business_value") or existing_idea.get("business_value")
    existing_idea["strategic_area"] = fields.get("strategic_area") or existing_idea.get("strategic_area")
    existing_idea["tech_components"] = fields.get("tech_components") or existing_idea.get("tech_components", [])
    existing_idea["links"] = {
        "pitch_url": fields.get("pitch_url") or existing_idea.get("links", {}).get("pitch_url"),
        "repo_url": fields.get("repo_url") or existing_idea.get("links", {}).get("repo_url"),
        "docs_url": fields.get("docs_url") or existing_idea.get("links", {}).get("docs_url"),
    }
    existing_idea["upvotes"] = issue.get("reactions", {}).get("+1", 0)
    existing_idea["issue_url"] = issue.get("html_url") or existing_idea.get("issue_url")
    existing_idea["processed_at"] = datetime.now(timezone.utc).isoformat()

    return existing_idea


def main():
    parser = argparse.ArgumentParser(description="Process AI idea submissions")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls, use mock data")
    parser.add_argument("--sync", action="store_true", help="Sync human-editable fields from Issues without calling Claude")
    parser.add_argument("--issue", type=int, help="Process or sync only this issue number")
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
    existing_map = {idea["issue_number"]: idea for idea in existing}

    # Filter to specific issue if requested
    if args.issue:
        issues = [i for i in issues if i["number"] == args.issue]
        if not issues:
            logger.error("Issue #%d not found", args.issue)
            sys.exit(1)

    new_count = 0
    sync_count = 0

    for issue in issues:
        num = issue["number"]

        if num in existing_map:
            if args.sync or args.issue:
                # Update human-editable fields from Issue
                sync_issue(issue, existing_map[num])
                sync_count += 1
                logger.info("Synced: %s", existing_map[num]["title"])
            continue

        # New issue — full pipeline
        idea = process_issue(issue, source="github", dry_run=args.dry_run)
        existing.append(idea)
        existing_map[idea["issue_number"]] = idea
        new_count += 1
        logger.info("Processed: %s", idea["title"])

    if not existing:
        logger.info("No ideas to process.")
        return

    # Cluster all ideas (skip for sync-only to avoid heavy deps)
    clusters_path = DATA_DIR / "clusters.json"
    if args.sync and new_count == 0:
        # Sync-only: just write updated ideas, keep existing clusters
        clusters = []
        if clusters_path.exists():
            with open(clusters_path) as f:
                clusters = json.load(f)
    elif args.dry_run:
        for idea in existing:
            idea["cluster_id"] = 0
            idea["cluster_label"] = "unclustered"
        clusters = [{"id": 0, "label": "unclustered", "idea_ids": [i["id"] for i in existing], "shared_components": [], "description": "All ideas (dry run)."}]
    else:
        from pipeline.cluster import cluster_ideas
        existing, clusters = cluster_ideas(existing)

    # Write output
    with open(DATA_DIR / "ideas.json", "w") as f:
        json.dump(existing, f, indent=2)

    with open(DATA_DIR / "clusters.json", "w") as f:
        json.dump(clusters, f, indent=2)

    enabler_count = sum(1 for i in existing if i.get("enabler_candidate"))
    logger.info("Done: %d total ideas (%d new, %d synced), %d clusters, %d enabler candidates",
                len(existing), new_count, sync_count, len(clusters), enabler_count)


if __name__ == "__main__":
    main()
