# JobSentinel: AI Job Intelligence & Opportunity Agent

JobSentinel is a production-grade autonomous agent that monitors newly posted software engineering jobs across public platforms, performs semantic profile evaluations, and serves career advancement recommendations to candidates.

## 🚀 Key Features

*   **Autonomous Resume Parsing:** Ingests resume PDFs, extracting 23 parsed metadata dimensions (identity, frameworks, AI/ML tools, databases, projects, seniority) using the Gemini API.
*   **Semantic Similarity Engine:** Performs dense vector similarity matching (`text-embedding-004`) combined with LLM context checks to calculate job compatibility scores (0–100%).
*   **WAF-Resilient Scraper:** Uses headful Playwright browsers with custom user agents and webdriver overrides to aggregate jobs posted within the last 24 hours from LinkedIn and Naukri.
*   **Career Growth Pathing:** Analyzes aggregate market demands to generate up-skilling roadmaps (recommending courses, certifications, and portfolio projects) and resume improvements.
*   **Responsive HTML Alerts:** Notifies candidates immediately via styled HTML emails when match compatibility exceeds 80%.
*   **Glassmorphic React Dashboard:** Hosts tabs for live discoveries, custom skill paths, resume critiques, parsed profile fields, and system telemetry streams.

---

## 📋 Prerequisites

*   Python 3.10+
*   Node.js & npm
*   Google Gemini API Key (stored in `.env`)
*   SMTP credentials (optional, for email alerts)

---

## 🛠️ Quick Start

### 1. Backend API & Scanner Setup
1. Clone the repository and install requirements:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
2. Configure your environment variables:
   ```bash
   cp .env.example .env
   # Add your GEMINI_API_KEY and SMTP credentials
   ```
3. Run the FastAPI backend:
   ```bash
   python -m src.api
   ```
   The backend will connect to SQLite (`jobsentinel.db`), start the scanner, and expose endpoints at [http://localhost:8000](http://localhost:8000).

### 2. Frontend Dashboard Setup
1. Navigate to the `frontend/` directory and install assets:
   ```bash
   cd frontend
   npm install
   ```
2. Launch the React server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:5173/](http://localhost:5173/) to view the agent dashboard.

---

## 📂 Project Structure

*   `src/api.py`: FastAPI backend routing (resume upload, analytics, critiques, market insights).
*   `src/main.py`: Scanner coordinating scrapers, vector similarity scoring, and email notifications.
*   `src/scraper/engine.py`: Playwright web scrapers for LinkedIn and Naukri, and mock job injector.
*   `src/intelligence/gemini.py`: Gemini client operations (resume parameters, embeddings, semantic matches, up-skill plan).
*   `src/core/db.py`: SQLite database models and auto-migration pipelines.
*   `src/notify/email_client.py`: HTML opportunity notifier.
*   `frontend/src/App.jsx`: Dark glassmorphic user dashboard.
