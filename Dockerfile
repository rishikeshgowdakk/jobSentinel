FROM python:3.10-slim

# Install system dependencies for LaTeX and Playwright
RUN apt-get update && apt-get install -y \
    texlive-full \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright dependencies
RUN pip install playwright && playwright install-deps

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

CMD ["python", "src/main.py"]
