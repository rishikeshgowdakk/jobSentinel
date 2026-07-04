# Workspace Rules: JobSentinel Agent

This workspace houses the **JobSentinel AI Job Intelligence & Opportunity Agent**. Any Antigravity agent or IDE assistant operating within this codebase must respect the rules and architectural designs specified below.

---

## 🏗️ Project Architecture

JobSentinel is built as a split-pane full-stack system:
1.  **Backend (FastAPI):** Orchestrates database actions, AI matching, up-skilling pathing, and scraper execution. Started via `python -m src.api`.
2.  **Frontend (React + Vite + Tailwind):** Displays dashboards, discovery job feeds, analytics, and resume critiques. Started via `npm run dev` in `frontend/`.
3.  **Database (SQLite):** Locally stores profiles, listings, matches, and application pipelines under `jobsentinel.db`.

---

## ⚠️ Core Development Constraints

When making edits or adding features, ensure the following constraints are maintained:

### 1. Scraper & WAF Bypasses
*   Both LinkedIn and Naukri actively block headless browsers.
*   **Playwright Launch Configuration:** Always ensure Playwright launches Chromium with `headless=False` (headful) by default or respects the `SCRAPE_HEADLESS` variable in config.
*   **Automation Stealth:** Maintain overrides for `navigator.webdriver` and utilize `playwright-stealth` in browser contexts to avoid triggering WAF/Akamai blocks.
*   **Mock Fallbacks:** Scrapers must fallback to generating realistic mock jobs (using `generate_mock_jobs`) if live scraping yields 0 results. This guarantees a populated feed for testing.

### 2. Semantic Matching Rules
*   Do not replace dense vector matching with keyword searches.
*   Compute cosine similarity on `text-embedding-004` vectors using pure-Python magnitude calculations in [calculate_cosine_similarity](file:///home/rishikesh/Desktop/rgkk/jobSentinel/src/main.py#L10) (no external vector database is needed for local development).
*   Combine vector similarity (25%) with Gemini's detailed recruiter matching (75%) to calculate overall match scores.

### 3. Graceful Key Fallbacks
*   Gemini client operations in [GeminiAnalyzer](file:///home/rishikesh/Desktop/rgkk/jobSentinel/src/intelligence/gemini.py) must verify if `GEMINI_API_KEY` is present.
*   If the key is missing, utilize fallback parsers/mock summaries instead of crashing, ensuring the core loops and dashboard page can load smoothly out of the box.

### 4. Database Schema Integrity
*   Always define new tables or columns in [Database._create_table](file:///home/rishikesh/Desktop/rgkk/jobSentinel/src/core/db.py#L40).
*   Ensure the startup schema check detects column mismatches and runs auto-migration/drop sequences seamlessly to prevent SQLite exceptions.
