# JobSentinel

An AI-powered job search agent that parses your resume, scrapes real-time job listings from LinkedIn, Naukri, and ATS platforms, and ranks them by compatibility using Gemini AI semantic matching.

Upload your resume → AI extracts your skills → Background agent scrapes the web → Jobs ranked by match score → Real-time updates via WebSocket.

---

## Features

- **Resume Parsing** — Upload a PDF or paste raw text. Gemini AI extracts skills, experience, education, and preferences into structured data.
- **Live Job Scraping** — Autonomous scraper searches LinkedIn, Naukri, and DuckDuckGo X-Ray (Greenhouse/Lever ATS boards) on a configurable interval.
- **Semantic Matching** — Each job is scored 0–100 using a weighted combination of cosine embedding similarity (25%) and Gemini semantic analysis (75%).
- **ATS Filtering** — Strict zero-tolerance filtering for job type (intern/full-time) and seniority level mismatches.
- **Skills Gap Analysis** — AI identifies missing skills from job requirements and recommends courses, projects, and certifications.
- **Resume Critique** — ATS optimization suggestions: missing keywords, formatting improvements, project enhancements.
- **Real-Time Updates** — WebSocket pushes new job discoveries and scanner logs to the browser instantly.
- **Multi-User** — Each browser session gets a unique ID with isolated profiles, preferences, and match results.
- **Dark/Light Mode** — Full theme support with a monochrome glassmorphic design system.
- **Email Alerts** — Optional SMTP notifications when a job scores ≥ 80% match.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                 │
│  Upload CV → Dashboard → Job Feed → Skills → Profile    │
└──────────────────────┬──────────────────────────────────┘
                       │ REST + WebSocket
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend                        │
│  Resume Parser · Job API · Preferences · Analytics      │
├─────────────────────────────────────────────────────────┤
│  Scanner Loop (async)         │  Gemini AI Engine       │
│  LinkedIn · Naukri · X-Ray    │  Embeddings · Matching  │
├─────────────────────────────────────────────────────────┤
│              SQLite / PostgreSQL Database                │
│  Users · Jobs · Matches · Applications · Settings       │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- A [Gemini API Key](https://aistudio.google.com/apikey)

### 1. Clone and setup

```bash
git clone https://github.com/rishikeshgowdakk/jobSentinel.git
cd jobSentinel

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Build the frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Run

```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000) — the frontend is served as static files from the API.

---

## Development

For frontend hot-reload during development:

```bash
# Terminal 1 — Backend
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend dev server (proxies API to :8000)
cd frontend
npm run dev
```

The Vite dev server proxies `/api` requests to the backend automatically.

---

## Docker

```bash
# Build the frontend first
cd frontend && npm install && npm run build && cd ..

# Build and run
docker build -t jobsentinel .
docker run -p 8000:8000 --env-file .env jobsentinel
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite, Tailwind CSS |
| Backend | FastAPI, Uvicorn |
| AI | Gemini 2.0 Flash, Gemini Embeddings |
| Scraping | Playwright (headless Chromium) |
| Database | SQLite (default) / PostgreSQL |
| PDF Parsing | PyMuPDF |

---

## How It Works

1. **Upload** — Your resume (PDF/TXT/MD) is parsed by Gemini AI into structured fields: name, skills, experience, education, target role, etc.

2. **Configure** — Set job keywords, preferred locations, job type (intern/full-time), and seniority level. Or let the AI auto-tune keywords from your resume.

3. **Scan** — The background scanner runs on a loop, searching across platforms using your preferences. Jobs are deduplicated and stored globally.

4. **Match** — Each job is evaluated against your profile using both vector embeddings (cosine similarity) and LLM semantic analysis. A combined score of 0–100 is calculated.

5. **Filter** — ATS-style strict filtering removes mismatches (e.g., senior roles when you selected intern-level).

6. **Display** — Jobs appear in your feed sorted by match score. Real-time WebSocket pushes new discoveries as they're found.

---

## License

MIT

---

Built by [Rishikesh Gowda KK](https://github.com/rishikeshgowdakk)
