# AI Opportunities & Enablers

A two-sided system for capturing and showcasing AI ideas at SEB. Ideas are submitted as GitHub Issues, processed by an AI pipeline, and displayed on a filterable marketplace.

**Live site:** https://trollstaven.github.io/ai-marketplace/

---

## How it works

```
GitHub Issue (idea form)
        |
        v
  pipeline/run.py
        |
        ├── Parses Issue fields
        ├── Transcribes MP4 pitch (if exists)
        ├── Claude API scores + summarizes
        └── Clusters ideas + detects enablers
        |
        v
  data/ideas.json + data/clusters.json
        |
        v (git push)
  GitHub Pages auto-deploys the marketplace
```

---

## First-time setup

```bash
# 1. Clone the repo
git clone https://github.com/trollstaven/ai-marketplace.git
cd ai-marketplace

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Create your .env file
cp .env.example .env
```

Then edit `.env` and fill in your keys:

```
ANTHROPIC_API_KEY=sk-ant-...       # Get from console.anthropic.com
GITHUB_TOKEN=ghp_...               # Needs 'repo' scope
GITHUB_REPO=trollstaven/ai-marketplace
```

---

## Submitting an idea

1. Go to the repo on GitHub
2. Click **Issues** > **New Issue**
3. Select **"AI Idea Submission"** template
4. Fill in all fields and submit

The idea is now stored as a GitHub Issue. It won't appear on the marketplace until the pipeline runs.

---

## Running the pipeline

The pipeline fetches all GitHub Issues labeled `idea`, processes new ones, and writes the output JSON.

```bash
# Process all new ideas
python pipeline/run.py

# Dry run (no API calls, uses mock data — good for testing)
python pipeline/run.py --dry-run
```

**What it does:**
1. Fetches all Issues with label `idea` from GitHub
2. Skips ideas already in `data/ideas.json` (matched by issue number)
3. For each new idea:
   - Parses the Issue body into structured fields
   - If `raw/pitches/{issue_number}.mp4` exists, transcribes it with Whisper
   - If `raw/pitches/{issue_number}.pdf/.docx/.pptx` exists, extracts text from it
   - Calls Claude API with all available context to generate a summary, normalize the arch pattern, and score business value + feasibility
4. Clusters all ideas using embeddings (sentence-transformers)
5. Detects enabler candidates (tech components shared by 2+ ideas)
6. Writes `data/ideas.json` and `data/clusters.json`

### Processing pitch materials

Drop files into `raw/pitches/` named by issue number. The pipeline auto-detects them.

```bash
# Videos — transcribed with Whisper
cp /path/to/pitches/42.mp4 raw/pitches/

# Documents — text extracted automatically
cp /path/to/docs/42.pdf raw/pitches/
cp /path/to/docs/42.docx raw/pitches/
cp /path/to/docs/42.pptx raw/pitches/

# Run pipeline
python pipeline/run.py
```

Supported formats: **MP4** (video), **PDF**, **DOCX**, **PPTX**. If both a video and a document exist for the same issue, both are used as context for Claude.

---

## Batch importing pitch recordings

Have a folder of MP4 pitch recordings? Import them all at once:

```bash
# Basic import — transcribe + extract + cluster
python -m pipeline.import_pitches /path/to/pitches/ --source hackathon-010

# Also create GitHub Issues for each (so they're editable later)
python -m pipeline.import_pitches /path/to/pitches/ --source hackathon-010 --create-issues

# Then push to deploy
git add data/
git commit -m "import: hackathon-010 pitches"
git push
```

**What it does for each MP4:**
1. Transcribes with Whisper
2. Sends transcript to Claude which extracts: title, problem, hypothesis, business value, strategic area, arch pattern, tech components, scores
3. Adds to ideas.json with a unique ID (e.g. `hackathon-010-001`)
4. After all files: clusters everything and detects enablers

**With `--create-issues`:** Also creates a GitHub Issue for each idea, so you can edit fields, change status, and collect upvotes later. The auto-pipeline will keep them in sync.

Files can be named anything (e.g. `team-alpha-pitch.mp4`, `idea-003.mp4`). They're processed alphabetically.

---

## Deploying to the live site

After running the pipeline, push the updated data:

```bash
git add data/ideas.json data/clusters.json
git commit -m "process: new batch of ideas"
git push
```

GitHub Actions will automatically deploy. The site updates within ~1 minute.

---

## Editing an idea

Ideas live as GitHub Issues — to edit one:

1. Find the Issue on GitHub (each idea card will show its issue number)
2. Edit the Issue body — change status, update fields, etc.
3. Re-run the pipeline to pick up changes:

```bash
python pipeline/run.py
git add data/
git commit -m "update: re-processed ideas"
git push
```

**Note:** The pipeline only processes *new* ideas (not already in ideas.json). To re-process an edited idea, remove its entry from `data/ideas.json` first, then re-run.

### Changing an idea's status

To move an idea to "In prod", "In development", etc.:
1. Edit the GitHub Issue
2. Change the **Current status** dropdown
3. Re-run pipeline + push

### Seed data (no Issue)

The 19 seed ideas (`af26-*`) have `issue_number: null` — they were added directly to `data/ideas.json`. To edit them, modify the JSON file directly.

---

## Previewing locally

```bash
# Copy data into docs (mimics what GitHub Actions does)
cp -r data/ docs/data/

# Start a local server
cd docs && python -m http.server 8000
```

Then open http://localhost:8000

---

## Project structure

```
ai-marketplace/
├── .github/
│   ├── ISSUE_TEMPLATE/idea-submission.yml   # Intake form
│   └── workflows/deploy.yml                 # Auto-deploy to Pages
├── pipeline/
│   ├── run.py              # Main entrypoint
│   ├── parse_issue.py      # Issue body → structured dict
│   ├── transcribe.py       # Whisper MP4 → text
│   ├── extract.py          # Claude API → enriched fields
│   └── cluster.py          # Embeddings + KMeans + enablers
├── docs/                   # GitHub Pages source
│   ├── index.html
│   ├── app.js
│   └── style.css
├── data/                   # Pipeline output (committed)
│   ├── ideas.json
│   └── clusters.json
├── raw/pitches/            # MP4 files (gitignored)
├── pitch.html              # Project pitch page
└── requirements.txt
```
