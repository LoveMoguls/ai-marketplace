# STRUCTURE.md — Repository layout

```
ai-opportunities-enablers/
│
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   └── idea-submission.yml       # Intake form — GitHub Issue template
│   └── workflows/
│       └── deploy.yml                # Auto-deploy docs/ to GitHub Pages on push
│
├── pipeline/                         # Local AI processing scripts
│   ├── run.py                        # Main entrypoint — run this to process ideas
│   ├── parse_issue.py                # Parse GitHub Issue body → structured dict
│   ├── transcribe.py                 # Whisper MP4 → transcript text
│   ├── extract.py                    # Claude API → enriched idea fields + scores
│   └── cluster.py                    # Embeddings + KMeans + enabler detection
│
├── docs/                             # GitHub Pages source — everything served here
│   ├── index.html                    # Main marketplace page
│   ├── app.js                        # All JS: fetch, filter, render, search
│   └── style.css                     # All styles: cards, filters, badges, layout
│
├── data/                             # Pipeline output — committed to repo
│   ├── ideas.json                    # All processed ideas
│   └── clusters.json                 # Cluster metadata + shared components
│
├── raw/                              # Local only — gitignored
│   └── pitches/                      # Drop MP4 files here before running pipeline
│       └── .gitkeep
│
├── CLAUDE.md                         # ← Claude Code reads this first
├── TASKS.md                          # ← Build tasks in order
├── STRUCTURE.md                      # ← This file
├── README.md                         # Public-facing project description
├── requirements.txt                  # Python dependencies
├── .env.example                      # Env var template (safe to commit)
├── .env                              # Real secrets (gitignored)
└── .gitignore
```

---

## Key relationships

```
GitHub Issues (label: idea)
        │
        ▼
pipeline/run.py
        │
        ├── parse_issue.py     reads Issue body
        ├── transcribe.py      reads raw/pitches/{n}.mp4
        ├── extract.py         calls Claude API
        └── cluster.py         generates embeddings, clusters, enablers
        │
        ▼
data/ideas.json
data/clusters.json
        │
        ▼ (git push)
GitHub Actions (deploy.yml)
        │
        ▼
docs/ → GitHub Pages
        │
        ├── index.html
        ├── app.js             fetches data/ideas.json
        └── style.css
```

---

## What lives where

| Concern | Location |
|---|---|
| Intake form definition | `.github/ISSUE_TEMPLATE/idea-submission.yml` |
| Raw pitch recordings | `raw/pitches/` (local, gitignored) |
| Pipeline logic | `pipeline/*.py` |
| Processed idea data | `data/ideas.json` |
| Cluster metadata | `data/clusters.json` |
| Marketplace UI | `docs/` |
| Deploy automation | `.github/workflows/deploy.yml` |
| Project context for Claude Code | `CLAUDE.md` |
| Build tasks | `TASKS.md` |

---

## Branch strategy

| Branch | Purpose |
|---|---|
| `main` | Production — GH Actions deploys from here |
| `pipeline/...` | Pipeline improvements |
| `frontend/...` | Marketplace UI changes |
| `data/...` | Data processing runs (can merge directly to main) |
