FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m spacy download en_core_web_sm || true
RUN python -m nltk.downloader stopwords punkt punkt_tab averaged_perceptron_tagger

COPY . .

RUN mkdir -p data/uploads data/processed

EXPOSE 8000

CMD ["sh", "-c", "gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} main:app"]
