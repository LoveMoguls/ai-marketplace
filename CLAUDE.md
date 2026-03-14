# CLAUDE.md — AI Opportunities & Enablers

This file is the source of truth for Claude Code working in this repository.
Read it fully before starting any task.

---

## Project purpose

A two-sided system for capturing and showcasing AI ideas at SEB:

1. **Intake** — GitHub Issue form where anyone at SEB submits an AI idea or use case
2. **Pipeline** — a local Python script that reads Issues + MP4 pitches, calls Claude API for extraction, clusters ideas, and writes structured JSON
3. **Marketplace** — a GitHub Pages static site that renders the JSON as filterable idea cards

No backend. No hosting costs. No GCP dependency in phase 1.

---

## Stack

| Layer | Technology | Notes |
|---|---|---|
| Intake form | GitHub Issue template (YAML) | `.github/ISSUE_TEMPLATE/idea-submission.yml` |
| Pipeline runtime | Python 3.11+ | Runs locally on developer machine |
| Transcription | OpenAI Whisper (`openai-whisper`) | Local model, no API call needed |
| AI extraction | Anthropic Claude API (`claude-sonnet-4-5`) | Structured JSON output |
| Embeddings | `sentence-transformers` | Local, no API cost |
| Clustering | `scikit-learn` KMeans | On embeddings |
| Output | `data/ideas.json` + `data/clusters.json` | Committed to repo |
| Frontend | Vanilla HTML + CSS + JS | No framework, no build step |
| Hosting | GitHub Pages | Served from `docs/` folder |
| Deploy | GitHub Actions | Auto-deploys on push to main |

---

## Key constraints

- **No framework in frontend** — plain HTML/CSS/JS only. Must work by opening `docs/index.html` directly in a browser without a dev server.
- **No secrets in repo** — API keys via `.env` file (gitignored). Provide `.env.example`.
- **MP4 files are gitignored** — only processed JSON output is committed.
- **GitHub Pages serves from `docs/`** — all frontend files go there.
- **Pipeline is idempotent** — running it twice should produce the same output. Use Issue number as stable ID.
- **Ideas.json is the single source of truth** for the frontend — no other data fetch.

---

## Data model

Each idea in `data/ideas.json` has this shape:

```json
{
  "id": "h010-023",
  "issue_number": 23,
  "source": "hackathon-010",
  "title": "Automated loan document summarizer",
  "submitted_by": "Anna Svensson",
  "contact_email": "anna.svensson@seb.se",
  "business_stakeholder": "WAM / CIB",
  "submitted_at": "2026-03-08",
  "status": "In development",
  "summary": "One paragraph AI-generated summary of the idea.",
  "problem": "Raw problem statement from Issue.",
  "hypothesis": "Raw hypothesis from Issue.",
  "business_value": "Raw business value text from Issue.",
  "strategic_area": "Credit",
  "arch_pattern": "Inference",
  "tech_components": ["pdf-extraction", "claude-api", "structured-output"],
  "cluster_id": 2,
  "cluster_label": "document-intelligence",
  "enabler_candidate": true,
  "scores": {
    "business_value": 7,
    "feasibility": 5
  },
  "links": {
    "pitch_url": "https://...",
    "repo_url": null,
    "docs_url": null
  },
  "transcript": "Full transcript text if MP4 was processed.",
  "processed_at": "2026-03-14T12:00:00Z"
}
```

`clusters.json` shape:

```json
[
  {
    "id": 2,
    "label": "document-intelligence",
    "idea_ids": ["h010-004", "h010-007", "h010-023"],
    "shared_components": ["pdf-extraction", "structured-output"],
    "description": "AI-generated cluster description."
  }
]
```

---

## GitHub Issue field mapping

The Issue template (`idea-submission.yml`) uses these field IDs.
Pipeline reads them by parsing the Issue body markdown.

| Issue field ID | maps to JSON field |
|---|---|
| `title` | `title` |
| `problem` | `problem` |
| `hypothesis` | `hypothesis` |
| `business_value` | `business_value` |
| `strategic_area` | `strategic_area` |
| `arch_pattern` | `arch_pattern` |
| `status` | `status` |
| `contact_name` | `submitted_by` |
| `contact_email` | `contact_email` |
| `business_stakeholder` | `business_stakeholder` |
| `pitch_url` | `links.pitch_url` |
| `repo_url` | `links.repo_url` |
| `docs_url` | `links.docs_url` |
| `tech_components` | `tech_components` (split by comma) |
| `source` | `source` |

---

## Environment variables

Required in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
GITHUB_REPO=your-org/ai-opportunities-enablers
```

---

## Pipeline flow (`pipeline/run.py`)

1. Load `.env`
2. Fetch all open + closed Issues with label `idea` from GitHub API
3. Parse each Issue body to extract structured fields
4. For each unprocessed Issue (not in existing `ideas.json`):
   a. If MP4 exists in `raw/pitches/{issue_number}.mp4` → transcribe with Whisper
   b. Call Claude API with Issue content (+ transcript if available) → get structured extraction
   c. Add to ideas list
5. Generate embeddings for all idea summaries
6. Run KMeans clustering → assign `cluster_id` and `cluster_label` to each idea
7. Ask Claude to generate a label and description for each cluster
8. Detect enabler candidates (components appearing in ≥2 ideas)
9. Write `data/ideas.json` and `data/clusters.json`
10. Print summary: N ideas processed, N clusters, N enabler candidates

---

## Frontend features (`docs/index.html`)

The marketplace must support:

- **Card grid** — one card per idea, responsive 2-column layout
- **Filter bar** — filter by: strategic area, arch pattern, status, has pitch video, enabler candidate
- **Search** — full-text search across title, summary, problem
- **Sort** — by business value score, date, status
- **Cluster view toggle** — group cards by cluster instead of flat list
- **Card design** — two sections per card: Business view (value, stakeholder, domain) and Engineering view (pattern, feasibility, components). Links section for pitch/repo/docs. Footer with contact + cluster tag.
- **Enabler badge** — green badge on cards where `enabler_candidate: true`
- **Empty state** — friendly message when filters return no results
- **No build step** — reads `../data/ideas.json` via `fetch()` on load

Card status color coding:
- In prod → green badge
- In dev → amber badge
- Under review → purple badge
- New idea → blue badge

---

## File ownership

| File | Who owns it | Notes |
|---|---|---|
| `.github/ISSUE_TEMPLATE/idea-submission.yml` | Pipeline | Source of intake data |
| `pipeline/run.py` | Pipeline | Main entrypoint |
| `pipeline/transcribe.py` | Pipeline | Whisper wrapper |
| `pipeline/extract.py` | Pipeline | Claude API extraction |
| `pipeline/cluster.py` | Pipeline | Embeddings + clustering |
| `pipeline/parse_issue.py` | Pipeline | GitHub Issue body parser |
| `data/ideas.json` | Pipeline output | Read by frontend |
| `data/clusters.json` | Pipeline output | Read by frontend |
| `docs/index.html` | Frontend | Main marketplace page |
| `docs/app.js` | Frontend | All JS logic |
| `docs/style.css` | Frontend | All styles |
| `.github/workflows/deploy.yml` | DevOps | GH Pages deploy |

---

## Running the project

```bash
# Setup
pip install -r requirements.txt
cp .env.example .env
# → fill in API keys

# Place MP4 files
cp /path/to/pitches/*.mp4 raw/pitches/

# Run pipeline
python pipeline/run.py

# Preview site locally
cd docs && python -m http.server 8000

# Deploy (automatic after push)
git add data/
git commit -m "process: hackathon-010 batch 1"
git push
```

---

## Code style

- Python: type hints on all functions, docstrings on public functions, no print statements (use `logging`)
- JS: vanilla ES6+, no frameworks, no build tools
- CSS: CSS custom properties for all colors and spacing
- All user-facing text in English
- Comments in English
