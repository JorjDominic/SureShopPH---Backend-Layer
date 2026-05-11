FROM python:3.12-slim

# Install build tools needed by some packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies (requirements.txt already lists spacy + calamanCy)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code
COPY . .

# calamanCy model is downloaded automatically on first request via calamancy.load()
# Use Railway-injected $PORT, fallback to 8000 for local docker runs
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
