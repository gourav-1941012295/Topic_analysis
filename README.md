# Autonomous Market Intelligence Agent

Fetches data from the web (Hacker News, RSS, optional News API), processes it (dedupe, extract entities/events/signals, trends, contradictions), and produces a **decision-ready report** with citations and a confidence score. This is a research/synthesis pipeline, not a chatbot.

**Pipeline:** Ingest → Dedupe & filter → Extract & tag → Trends & contradictions → Source weighting → Report (with self-critique).

---

## What you need

- **Python 3.10+**
- **OpenAI API key** (required for extraction and report generation)
- Optional: News API key (for extra news articles)

---

## Setup (first time)

### 1. Go to the project folder

```bash
cd Topic_analysis

```

(Use the folder that contains `run.py` — e.g. `agent_ai` or `Agent_AI`.)

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate          # macOS/Linux
# or:  venv\Scripts\activate     # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

You should see packages like `requests`, `feedparser`, `pyyaml`, `python-dotenv`, `openai` being installed.

### 4. Add your `.env` file and OpenAI key

Create a `.env` file from the example and add your OpenAI API key:

```bash
cp .env.example .env
```

Then open `.env` in an editor and set:

```bash
OPENAI_API_KEY=sk-your-actual-key-here
```

- Get a key from [OpenAI API keys](https://platform.openai.com/api-keys) (you need an OpenAI account).
- Put nothing else on that line (no quotes, no spaces around `=`).
- **Do not commit `.env`** — it is in `.gitignore`.

**Optional:** To add news articles from News API, add this line to `.env` (get a key from [newsapi.org](https://newsapi.org)):

```bash
NEWS_API_KEY=your-news-api-key
```

### 5. (Optional) Adjust config

Edit `config/topic_config.yaml` to change:

- **Time window** — how many days of content to keep (default 30).
- **RSS feeds** — which feeds to fetch (default: TechCrunch, Wired).
- **Report sections** — which sections appear in the report.

You do **not** set the topic here; the app asks for it when you run.

---

## How to run

From the **agent_ai** folder (with venv activated if you use it):

```bash
python run.py
```

1. The app will ask: **Which market or area do you want to analyze?**
2. Type a topic (e.g. `AI model providers`, `EV battery supply chain`, `fintech regulation`) and press Enter.
3. Or press Enter with no input to use the default topic: **Market Intelligence**.

You can also pass the topic on the command line and skip the prompt:

```bash
python run.py "EV battery supply chain"
```

The run will:

- Fetch from Hacker News, RSS feeds (and News API if `NEWS_API_KEY` is set).
- Filter by recency, extract entities/events/signals, detect trends and contradictions.
- Build a report with citations and a confidence score.

---

## Where to find the output

| What            | Where |
|-----------------|--------|
| Report (Markdown) | `samples/report_YYYYMMDD_HHMM.md` |
| Report (JSON)     | `samples/report_YYYYMMDD_HHMM.json` |
| Database          | `data/intelligence.db` (SQLite) |
| Run status        | `data/run_status.json` (current step and timing) |

Reports are written into the `samples/` folder each run; the timestamp is in the filename.

---

## Optional environment variables

Add these to `.env` if you want to change behavior:

| Variable | Example | Purpose |
|----------|---------|--------|
| `OPENAI_API_KEY` | `sk-...` | **Required.** OpenAI key for LLM calls. |
| `NEWS_API_KEY`   | `...`    | Optional. Enables News API as a source. |
| `MAX_DOCS_PER_RUN` | `30`  | Cap how many docs are processed (faster, cheaper). |
| `TRACK_PROGRESS`   | `1`   | Log extraction progress every 5 docs. |
| `TRACK_STATUS_FILE` | `0`  | Set to `0` to disable writing `data/run_status.json`. |
| `LOG_LEVEL`        | `DEBUG` | More verbose logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

Example `.env` with options:

```bash
OPENAI_API_KEY=sk-your-key
NEWS_API_KEY=your-news-key
MAX_DOCS_PER_RUN=25
TRACK_PROGRESS=1
```

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| **`ModuleNotFoundError: No module named 'feedparser'`** (or similar) | Run `pip install -r requirements.txt` again. Use the same Python/venv you use for `python run.py`. |
| **`OPENAI_API_KEY not set`** or placeholder extractions | Create `.env` from `.env.example`, add `OPENAI_API_KEY=sk-...` with a valid key, and run from the same folder so the app finds `.env`. |
| **No raw docs / empty report** | Check that RSS URLs in `config/topic_config.yaml` are valid and that your topic matches some content (e.g. "AI" for tech feeds). If you use News API, set `NEWS_API_KEY` in `.env`. |
| **Permission error when installing packages** | Use a virtual environment (steps 2–3 above) and install inside it so you don’t need system or user site-packages. |

---

## Project layout

```
agent_ai/
├── README.md           # This file
├── run.py              # Entry point — run this
├── llm.py              # Shared LLM (OpenAI) helpers
├── tracking.py         # Run status / timing
├── config/
│   ├── topic_config.yaml       # Time window, sources, report sections
│   └── topic_config.example.yaml
├── ingestion/          # Fetch & store (HN, RSS, News API)
├── processing/        # Dedupe, extract, trends
├── reasoning/         # Source weighting, self-critique
├── report/            # Report synthesis
├── samples/           # Generated reports (report_*.md, report_*.json)
├── data/              # intelligence.db, run_status.json (created at run time)
├── .env.example       # Template for .env
├── .env               # Your keys (create from .env.example; do not commit)
├── .gitignore
└── requirements.txt
```

---

## Summary checklist

- [ ] Python 3.10+ installed  
- [ ] In project folder: `cd agent_ai`  
- [ ] Virtual environment created and activated (recommended)  
- [ ] Dependencies installed: `pip install -r requirements.txt`  
- [ ] `.env` created: `cp .env.example .env`  
- [ ] `OPENAI_API_KEY=sk-...` added to `.env`  
- [ ] Run: `python run.py`  
- [ ] Enter a topic when prompted (or pass it: `python run.py "your topic"`)  
- [ ] Check output in `samples/report_*.md` and `data/`
