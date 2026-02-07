# How to Run Quorum Phase 2 Triage System

## What This Is

**Quorum Phase 2 — Intelligent RFP Triage MVP** for TPGI CPA LLC.

An AI-powered system that fetches pre-processed government solicitations from the partner Quorum platform API, scores each one against the firm's capabilities, and produces GO / CONDITIONAL / NO-GO recommendations.

**Key Features:**
- API-powered ingestion — pulls structured solicitation data from the partner platform (no manual PDF handling)
- 2-node LangGraph workflow: Fetcher -> Scorer
- Programmatic NAICS / set-aside / clearance knockout checks
- LLM-powered technical fit analysis (Claude Haiku)
- Professional Streamlit dashboard for reviewing results
- Direct SAM.gov links on each result

---

## Prerequisites

- **Python 3.9+** (tested with 3.11)
- **pip** (or conda)
- An **Anthropic API key** — get one at https://console.anthropic.com/

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/jabarkle/QuorumTest.git
cd QuorumTest
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example env file and fill in your Anthropic API key:

```bash
cp .env.example .env
```

Then open `.env` and replace the placeholder:

```
ANTHROPIC_API_KEY=sk-ant-...your-real-key-here...
```

The `QUORUM_API_URL` is pre-configured to point to the partner Lambda endpoint. Change it only if the endpoint moves.

---

## Running

### Option A: CLI (triage only)

```bash
python src/triage_check.py
```

This will:
1. Fetch solicitations from the partner API
2. Score each against `Input/My Firm/Firm Data.json`
3. Save individual reports to `output_reports/triage_report_*.json`
4. Save a summary to `output_reports/triage_summary.json`

### Option B: Streamlit Dashboard (recommended)

```bash
streamlit run src/dashboard.py
```

Then open **http://localhost:8501** in your browser.

The dashboard lets you:
- Click **"Fetch & Score from API"** in the sidebar to pull and score solicitations
- View all results with scores and recommendations
- Filter by recommendation (GO / CONDITIONAL / NO-GO)
- Sort by score
- See knockouts, matches, gaps, recommended personnel
- Link out to SAM.gov for each solicitation

---

## Project Structure

```
QuorumTest/
├── src/
│   ├── api_client.py        # Partner API client — fetch & map solicitations
│   ├── triage_check.py      # LangGraph triage engine (Fetcher -> Scorer)
│   └── dashboard.py         # Streamlit UI
├── Input/
│   └── My Firm/
│       └── Firm Data.json   # Firm capabilities, NAICS, past performance, personnel
├── output_reports/           # Generated triage reports (git-ignored)
├── .env.example              # Template for environment variables
├── requirements.txt          # Python dependencies
├── README.md                 # Project mission & architecture overview
├── HOW_TO_RUN.md             # This file
└── message.txt               # Partner platform infrastructure notes
```

---

## How It Works

### Data Flow

```
Partner Platform (SAM.gov scraper + PDF extractor + "The Guillotine")
        |
        |  GET /  →  structured JSON
        v
api_client.py
        |  fetch_solicitations() → map_to_aggregated_rfp()
        v
triage_check.py
        |  Programmatic checks (NAICS, set-aside, clearance)
        |  LLM analysis (Claude Haiku)
        |  Score calculation + recommendation
        v
output_reports/*.json  →  dashboard.py (Streamlit)
```

### Scoring

| Factor | Impact |
|--------|--------|
| Base Score | 70 |
| Each Knockout | -30 points |
| Each Match | +5 points (max +25) |
| Each Gap | -5 points (max -15) |
| LLM Technical Adjustment | -20 to +20 |

**Recommendations:**
- **GO** (score >= 70, no knockouts): Strong fit — pursue with capture plan
- **CONDITIONAL** (score 45–69, no knockouts): Moderate fit — assess teaming strategy
- **NO-GO** (score < 45 or knockouts present): Do not pursue

---

## Customization

### Change LLM Model

In `src/triage_check.py`, find:
```python
llm = ChatAnthropic(
    model="claude-3-haiku-20240307",
    ...
)
```
Change to `claude-3-5-sonnet-latest` for better reasoning (higher cost).

### Adjust Scoring Weights

In `node_scorer()`:
```python
base_score = 70
knockout_penalty = len(knockouts) * 30
match_bonus = min(len(matches) * 5, 25)
gap_penalty = min(len(gaps) * 5, 15)
```

### Update Firm Profile

Edit `Input/My Firm/Firm Data.json` to update:
- NAICS codes
- Business types (WOSB, SDB, etc.)
- Certifications & clearance level
- Core competencies & specialized expertise
- Past performance references
- Key personnel

### Change API Endpoint

Update `QUORUM_API_URL` in your `.env` file.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "No solicitations found from API" | Verify `QUORUM_API_URL` in `.env`. Try the URL in a browser. Lambda cold starts can take a few seconds — retry. |
| API 500/502 errors | Lambda cold start — wait a few seconds and retry. Check with partner if infra is up. |
| `ANTHROPIC_API_KEY` errors | Make sure `.env` exists and contains a valid key. Run `cp .env.example .env` if missing. |
| Dashboard won't start | Ensure streamlit is installed: `pip install streamlit`. Run from the project root. |
| Import errors | Run `pip install -r requirements.txt` to install all dependencies. |

---

Built for TPGI CPA LLC | Quorum Phase 2: Intelligent Triage MVP
