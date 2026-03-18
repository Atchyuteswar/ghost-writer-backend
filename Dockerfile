FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m spacy download en_core_web_lg || true
RUN python -m nltk.downloader stopwords punkt punkt_tab averaged_perceptron_tagger

COPY . .

RUN mkdir -p data/uploads data/processed

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
