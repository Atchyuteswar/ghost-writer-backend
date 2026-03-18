# Ghost-Writer Backend 👻

Your AI digital twin's brain — a FastAPI backend that learns your texting style and speaks like you.

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- Anthropic API key ([get one here](https://console.anthropic.com/))

## Quick Start

### 1. Clone & Configure

```bash
cd ghost-writer-backend
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 2. Run with Docker (Recommended)

```bash
docker-compose up --build
```

### 3. Run without Docker

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
python -m spacy download en_core_web_lg
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check with version info |
| `GET` | `/health` | Detailed health status |
| `POST` | `/upload` | Upload chat export (WhatsApp/Discord/Email) |
| `POST` | `/analyze` | Run NLP analysis on parsed messages |
| `POST` | `/pii/mask` | Mask PII in messages |
| `GET` | `/pii/status` | Check Presidio readiness |
| `POST` | `/generate` | Generate AI response in your voice |
| `GET` | `/generate/prompts` | Get example prompts |
| `POST` | `/style-transfer` | Rewrite text in your voice + style |
| `POST` | `/memories/store` | Store messages as vector memories |
| `POST` | `/memories/search` | Semantic search over memories |
| `GET` | `/memories/count` | Count of stored memories |
| `DELETE` | `/memories/clear` | Clear all memories |
| `POST` | `/battles/generate` | Generate twin battle responses |
| `GET` | `/battles/prompts` | Get battle prompt ideas |

## Run Tests

```bash
pytest tests/ -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic Claude API key |
| `PINECONE_API_KEY` | `""` | Pinecone API key (optional, for cloud vector store) |
| `PINECONE_INDEX_NAME` | `ghost-writer-memories` | Pinecone index name |
| `LOCAL_ONLY_MODE` | `true` | Keep all data local (no cloud calls except AI) |
| `MAX_FILE_SIZE_MB` | `50` | Maximum upload file size |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Allowed CORS origins |
| `PORT` | `8000` | Server port |

## Privacy & Local-Only Mode

When `LOCAL_ONLY_MODE=true` (default):
- All message data stays on your machine
- Vector memories use in-memory storage (no Pinecone)
- Only the Anthropic API is called externally (for AI generation)
- No telemetry, no tracking, no data collection

## Mobile App

The React Native (Expo) frontend lives in `../ghost-writer-app/`. Update the API base URL to connect:

```js
// In your frontend constants
const API_BASE_URL = 'http://<YOUR_LOCAL_IP>:8000';
```

Run `ipconfig` (Windows) or `ifconfig` (Mac/Linux) to find your local IP for physical device testing.
