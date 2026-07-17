# Multi-Agent Research Assistant

A production-grade research pipeline powered by three AI agents (planner, researcher, summarizer) orchestrated via **LangGraph**, with async job processing through **Celery + Redis**, human-in-the-loop approval, output guardrails, and full observability.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  React Frontend (Netlify)                                    │
│  Submit queries → Poll status → Review & approve → View     │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────────┐
│  FastAPI Backend                                              │
│  POST /jobs/submit  → Celery task dispatch                   │
│  GET  /jobs/:id/status → Redis state polling                 │
│  POST /jobs/:id/approve → Resume pipeline                    │
│  GET  /jobs/:id/result  → Full result + guardrails           │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  Celery Worker                                                │
│  ┌──────────┐   ┌────────────┐   ┌─────────────┐            │
│  │ Planner  │──▶│ Researcher │──▶│ Summarizer  │            │
│  │ (Gemini) │   │ (Search +  │   │ (Gemini)    │            │
│  └──────────┘   │  Gemini)   │   └──────┬──────┘            │
│                  └─────┬──────┘          │                   │
│                        │          ┌──────▼──────┐            │
│                   Human-in-the   │ Guardrails  │            │
│                   -loop gate     └─────────────┘            │
└──────────────────────────────────────────────────────────────┘
         │                    │
    ┌────▼────┐         ┌────▼────┐
    │  Redis  │         │ MongoDB │
    │ (state, │         │ (logs)  │
    │  broker)│         └─────────┘
    └─────────┘
```

## Features

- **Multi-agent workflow** — Planner decomposes queries, Researcher gathers sources, Summarizer produces reports
- **LangGraph orchestration** — Typed state graph with conditional edges and checkpoints
- **Async task queue** — Celery + Redis for non-blocking job execution with status polling
- **Human-in-the-loop** — Review research findings before summary generation (auto-skipped for "quick" depth)
- **Guardrails** — Output length validation, hallucination detection (keyword grounding), source coverage, confidence scoring, content safety
- **Full observability** — Per-agent tracing with duration, token usage, and structured logging
- **Streaming status** — Real-time progress updates via polling

## Quick Start

### Prerequisites

- Docker & Docker Compose
- A [Google AI Studio](https://aistudio.google.com/apikey) API key (free tier works)

### 1. Clone & configure

```bash
git clone https://github.com/ravishu5/multi-agent-research-assistant.git
cd multi-agent-research-assistant
cp backend/.env.example backend/.env
# Edit backend/.env and add your GOOGLE_API_KEY
```

### 2. Start the backend

```bash
docker compose up --build
```

This starts: Redis, MongoDB, FastAPI (port 8000), and Celery worker.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Deployment

### Backend → Render (free tier)

1. Push to GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Point to the `backend/` directory
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add env vars: `GOOGLE_API_KEY`, `REDIS_URL` (use Render Redis or Upstash)
7. Create a separate **Background Worker** for Celery:
   - Start command: `celery -A app.worker.celery_app worker --loglevel=info`

### Frontend → Netlify

```bash
cd frontend

# Create .env with your backend URL
echo "VITE_API_URL=https://your-backend.onrender.com/api/v1" > .env

# Deploy
npx netlify-cli deploy --prod --dir=dist
```

Or connect the GitHub repo to Netlify:
- Build command: `npm run build`
- Publish directory: `frontend/dist`
- Environment variable: `VITE_API_URL=https://your-backend.onrender.com/api/v1`

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/jobs/submit` | Submit a research job |
| `GET` | `/api/v1/jobs/{id}/status` | Poll job status |
| `GET` | `/api/v1/jobs/{id}/result` | Get full result |
| `POST` | `/api/v1/jobs/{id}/approve` | Approve/reject findings |
| `GET` | `/api/v1/jobs/` | List all jobs |
| `GET` | `/api/v1/health` | Health check |

### Submit a job

```bash
curl -X POST http://localhost:8000/api/v1/jobs/submit \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest advances in quantum computing?", "depth": "standard", "max_sources": 5}'
```

## Tech Stack

- **Backend**: Python, FastAPI, LangGraph, Celery, Redis, MongoDB
- **LLM**: Google Gemini (via google-generativeai)
- **Frontend**: React, Vite, Lucide icons
- **Infra**: Docker, GitHub Actions CI
- **Deployment**: Netlify (frontend), Render (backend)

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Pydantic settings
│   │   ├── models.py            # Request/response/state models
│   │   ├── guardrails.py        # Output validation & safety
│   │   ├── tracing.py           # Observability & metrics
│   │   ├── worker.py            # Celery task definitions
│   │   ├── agents/
│   │   │   ├── graph.py         # LangGraph workflow
│   │   │   ├── planner.py       # Query decomposition
│   │   │   ├── researcher.py    # Source gathering
│   │   │   ├── summarizer.py    # Report generation
│   │   │   └── tools.py         # Search tools
│   │   └── routes/
│   │       ├── jobs.py          # Job CRUD endpoints
│   │       └── health.py        # Health check
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main app
│   │   ├── api/client.js        # API client
│   │   ├── hooks/useJobPoller.js # Polling hook
│   │   └── components/
│   │       ├── SearchForm.jsx
│   │       ├── AgentTimeline.jsx
│   │       ├── ApprovalPanel.jsx
│   │       ├── ResultView.jsx
│   │       └── JobHistory.jsx
│   ├── netlify.toml
│   └── package.json
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## License

MIT
