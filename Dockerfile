FROM python:3.10-slim

# Install system dependencies for Playwright browsers
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser deps and Chromium
RUN playwright install-deps && playwright install chromium

# Copy application source
COPY src/ src/
COPY frontend/dist/ frontend/dist/
COPY .env.example .env.example

EXPOSE 8000

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
