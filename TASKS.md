# TASKS.md — Build order for Claude Code

Work through these tasks in order. Complete each fully before moving to the next.
Mark tasks done by changing `[ ]` to `[x]`.

Read `CLAUDE.md` before starting. It contains the full data model, stack, and constraints.

---

## Phase 0 — Repo scaffold

- [ ] **T01** Create full directory structure as defined in `STRUCTURE.md`
- [ ] **T02** Create `requirements.txt` with all Python dependencies:
  - `anthropic`, `openai-whisper`, `sentence-transformers`, `scikit-learn`, `requests`, `python-dotenv`, `numpy`
- [ ] **T03** Create `.env.example` with placeholder values for `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `GITHUB_REPO`
- [ ] **T04** Create `.gitignore`:
  - ignore `raw/pitches/*.mp4`, `.env`, `__pycache__`, `.DS_Store`, `*.pyc`, `venv/`, `node_modules/`
- [ ] **T05** Copy `idea-submission.yml` into `.github/ISSUE_TEMPLATE/`

---

## Phase 1 — GitHub Actions deploy

- [ ] **T06** Create `.github/workflows/deploy.yml`:
  - Trigger: push to `main` when files in `data/` or `docs/` change
  - Job: deploy `docs/` directory to GitHub Pages using `actions/deploy-pages@v4`
  - Permissions: `pages: write`, `id-token: write`
  - Environment: `github-pages`

---

## Phase 2 — Pipeline

- [ ] **T07** Create `pipeline/parse_issue.py`:
  - Function `parse_issue_body(body: str) -> dict` 
  - Parse GitHub Issue body markdown (field headers + content blocks)
  - Return dict matching Issue field IDs from `CLAUDE.md` field mapping table
  - Handle missing/empty fields gracefully (return None, not raise)

- [ ] **T08** Create `pipeline/transcribe.py`:
  - Function `transcribe(mp4_path: str) -> str`
  - Use `openai-whisper` with model `base` (good speed/accuracy balance)
  - Return full transcript as string
  - Log progress, handle file-not-found gracefully

- [ ] **T09** Create `pipeline/extract.py`:
  - Function `extract_idea(issue_fields: dict, transcript: str | None) -> dict`
  - Call Claude API (`claude-sonnet-4-5`) with structured prompt
  - System prompt: extract summary (2-3 sentences), normalize arch_pattern to one of: `RAG | Inference | Traditional ML | Agentic | Multimodal`, score business_value 1-10 and feasibility 1-10
  - Request JSON output, parse and validate response
  - Return enriched fields dict

- [ ] **T10** Create `pipeline/cluster.py`:
  - Function `cluster_ideas(ideas: list[dict]) -> tuple[list[dict], list[dict]]`
  - Generate embeddings using `sentence-transformers` (`all-MiniLM-L6-v2`)
  - Run KMeans (k = max(2, len(ideas) // 5), min 2 max 10 clusters)
  - Assign `cluster_id` to each idea
  - Call Claude to generate a short slug label and one-sentence description per cluster
  - Detect enabler candidates: tech_components appearing in ≥2 ideas → set `enabler_candidate: true`
  - Return updated ideas list + clusters list

- [ ] **T11** Create `pipeline/run.py` — main entrypoint:
  - Load `.env`
  - Fetch Issues with label `idea` from GitHub API (handle pagination)
  - Load existing `data/ideas.json` (empty list if not exists)
  - For each Issue not already in ideas.json (match by `issue_number`):
    - Parse Issue body
    - Check for MP4 at `raw/pitches/{issue_number}.mp4` → transcribe if exists
    - Extract via Claude
    - Append to ideas list
  - Run clustering on full ideas list
  - Write `data/ideas.json` and `data/clusters.json`
  - Print summary to stdout

---

## Phase 3 — Frontend

- [ ] **T12** Create `docs/style.css`:
  - CSS custom properties for all colors (light mode, clean neutral palette)
  - Card styles: two-column grid, responsive (single column below 700px)
  - Badge styles: status colors (green/amber/purple/blue), domain, pattern
  - Filter bar: horizontal pill filters, active state
  - Link chips: pitch (orange tint), repo (purple tint), docs (blue tint), empty (gray)
  - Score bars: pip system (10 pips for value, 6 for feasibility)
  - Enabler badge: green
  - Footer: avatar initials circle, contact info, cluster tag
  - Cluster view: grouped sections with cluster header

- [ ] **T13** Create `docs/app.js`:
  - On load: `fetch('../data/ideas.json')` + `fetch('../data/clusters.json')`
  - State: `allIdeas`, `activeFilers`, `searchQuery`, `sortBy`, `viewMode` (grid | cluster)
  - Filter logic: strategic_area, arch_pattern, status, has_pitch, enabler_candidate
  - Search: filter by title + summary + problem (case-insensitive)
  - Sort: business_value score desc, date desc, alphabetical
  - Render card: build DOM from idea object, attach all fields
  - Render cluster view: group by cluster_id, show cluster header with label + shared components
  - Filter bar: render pills from unique values in data, click to toggle active
  - Empty state: show message when 0 results
  - No external dependencies — vanilla JS only

- [ ] **T14** Create `docs/index.html`:
  - Clean semantic HTML structure
  - Header: project title + tagline
  - Stats bar: total ideas, in prod count, enabler count
  - Filter bar: placeholder, rendered by `app.js`
  - View toggle: Grid / Cluster
  - Sort dropdown
  - Cards container: rendered by `app.js`
  - Links to `style.css` and `app.js`
  - No external CDN dependencies

---

## Phase 4 — Data seed

- [ ] **T15** Create `data/ideas.json` with seed data from the AI Factory use cases spreadsheet:
  - Include all 19 rows from `Business use cases` sheet
  - Map columns to data model fields (see `CLAUDE.md` field mapping)
  - Normalize `Architectural pattern` values to clean enum
  - Assign placeholder cluster labels based on obvious groupings
  - Use `"source": "ai-factory-2026"` for source field
  - Set `"issue_number": null` for seed data (not from GitHub Issues)

- [ ] **T16** Create `data/clusters.json` seed data matching the clusters assigned in T15

---

## Phase 5 — Validation

- [ ] **T17** Test pipeline dry run:
  - Run `python pipeline/run.py --dry-run` (add dry-run flag that skips Claude API calls, uses mock data)
  - Verify JSON output is valid and matches schema

- [ ] **T18** Test frontend locally:
  - `cd docs && python -m http.server 8000`
  - Verify cards render with seed data
  - Verify all filters work
  - Verify cluster view works
  - Verify search works
  - Verify on mobile width (resize to 375px)

- [ ] **T19** Test GitHub Actions:
  - Push a change to `data/ideas.json`
  - Verify Pages deploy succeeds in Actions tab
  - Verify live site renders correctly

---

## Backlog (phase 2+)

- [ ] **B01** Detail view — click a card to expand full idea with all fields
- [ ] **B02** Cluster map — visual 2D scatter plot of ideas using UMAP dimensionality reduction
- [ ] **B03** Export — download filtered ideas as CSV
- [ ] **B04** Status workflow — allow updating status via GitHub Issue label changes
- [ ] **B05** GCP integration — move pipeline to Cloud Run job triggered by webhook
- [ ] **B06** Scoring UI — allow maintainers to override AI scores via GitHub comment

---

## Notes for Claude Code

- Never hardcode API keys. Always read from `os.environ` via `python-dotenv`.
- The frontend must work with `file://` protocol (no `fetch` of relative paths that break locally). Use a base URL constant at top of `app.js` that can be switched between local and production.
- Keep all Python modules importable standalone for testing.
- When writing `extract.py`, use Claude's structured output — ask for JSON explicitly in the system prompt and parse `response.content[0].text`.
