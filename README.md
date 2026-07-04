# Sentinel-Apply

Production-grade automated job hunting and application system.

## Features
- Real-time Monitoring: Scrapes LinkedIn for new job postings with 60s latency.
- Gemini Analysis: Uses Google Gemini 1.5 Flash to analyze Job Descriptions against your Master Resume.
- ATS Scoring: Automatically calculates ATS compatibility.
- Tailored Resumes: Generates high-quality LaTeX resumes for high-match jobs.
- Instant Notifications: Sends tailored resumes via email and creates Google Calendar events.
- Persistence: Tracks processed jobs in PostgreSQL to avoid duplicates.

## Prerequisites
- Python 3.10+
- PostgreSQL
- TeX Live (for pdflatex)
- Google Gemini API Key
- Google Cloud Project (for Calendar API)
- SMTP Credentials (e.g., Gmail App Password)

## Setup

1. Install Dependencies:
   pip install -r requirements.txt
   playwright install chromium

2. Configure Environment:
   Copy .env.example to .env and fill in your credentials.

3. Prepare Master Resume:
   Create a master_resume.md in the root directory.

4. Google Calendar API:
   Download your credentials.json and place it in the root directory.

5. Run the System:
   python src/main.py
