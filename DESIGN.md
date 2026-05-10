# Sentinel-Apply Architecture Design

## Overview
Sentinel-Apply is a real-time automated job application system designed to monitor job boards, analyze descriptions using Gemini AI, tailor resumes in LaTeX, and notify the user via email and Google Calendar.

## Technical Stack
- **Language:** Python 3.10+
- **Database:** PostgreSQL (for tracking processed jobs)
- **AI Engine:** Google Gemini (1.5 Pro/Flash)
- **Scraper:** Playwright (with stealth)
- **Resume Gen:** Jinja2 + LaTeX (`pdflatex`)
- **Notifications:** SMTP (Email), Google Calendar API
- **Scheduling:** Python loop with 60s sleep

## Project Structure
```text
.
├── src/
│   ├── core/
│   │   ├── config.py       # Configuration and Env variables
│   │   ├── db.py           # PostgreSQL interactions
│   │   └── logger.py       # Centralized logging
│   ├── scraper/
│   │   └── engine.py       # Playwright scraper logic
│   ├── intelligence/
│   │   └── gemini.py       # Gemini API integration
│   ├── generator/
│   │   ├── resume.py       # LaTeX generation logic
│   │   └── templates/      # LaTeX .tex templates
│   ├── notify/
│   │   ├── email_client.py # SMTP integration
│   │   └── calendar.py     # Google Calendar integration
│   └── main.py             # Orchestrator
├── requirements.txt        # Dependencies
├── .env.example            # Environment template
└── Dockerfile              # Deployment container
```

## Data Schema (PostgreSQL)
### Table: `processed_jobs`
- `id`: UUID (Primary Key)
- `job_id`: VARCHAR (External job board ID, Unique)
- `title`: TEXT
- `company`: TEXT
- `url`: TEXT
- `ats_score`: INTEGER
- `processed_at`: TIMESTAMP
- `status`: VARCHAR (e.g., 'tailored', 'notified', 'ignored')

## Modules Detail

### 1. Scraper (`src/scraper/engine.py`)
- Navigates to job boards (LinkedIn, Indeed).
- Sorts by "Most Recent".
- Extracts `job_id`, `title`, `company`, `link`, and full `description`.
- Implements random delays and stealth to avoid detection.

### 2. Intelligence (`src/intelligence/gemini.py`)
- Prompts Gemini with `master_resume` and `job_description`.
- Requests structured JSON output:
  - `ats_score`: 0-100
  - `tailored_experience`: List of updated bullet points.
  - `summary`: Tailored professional summary.
  - `skills`: Top keywords found in JD.

### 3. Generator (`src/generator/resume.py`)
- Uses Jinja2 to inject tailored content into a `.tex` template.
- Runs `pdflatex` to produce a PDF.
- Cleans up temporary LaTeX files.

### 4. Notifier (`src/notify/`)
- **Email:** Sends high-priority email with the PDF attached.
- **Calendar:** Authenticates with Google API, creates an event for the application, and sets aggressive reminders.

## Security & Reliability
- **Rate Limiting:** Scraper will include exponential backoff and randomized intervals.
- **Secrets:** All credentials stored in `.env`.
- **Error Handling:** Try-except blocks for each module to ensure the main loop doesn't crash.
