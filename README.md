# KT-Agent — Agentic Knowledge Transfer System

A production-style multi-agent system for employee onboarding and knowledge retrieval, built with **FastAPI**, **LangGraph**, **OpenAI**, and **Pinecone**.

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)

---

## What It Does

KT-Agent answers employee questions about company projects, generates onboarding roadmaps, and surfaces relevant documents — all via a conversational chat interface powered by a multi-agent LangGraph pipeline.

| Capability | Details |
|---|---|
| Chat | Intent-aware Q&A with conversation memory |
| Document Ingestion | PDF, DOCX, TXT, MD, images (OCR), audio (Whisper) |
| Onboarding Plans | Personalised roadmaps via Planning Agent |
| PII Protection | Presidio-based detection with regex fallback |
| Duplicate Detection | SHA-256 hash check before ingestion |
| Groundedness Scoring | Evaluation Agent checks answer quality |

---

## Architecture

```
User Message
     │
     ▼
Orchestrator Agent  ──► Conversation Memory (SQLite)
     │                   User Profile Memory (SQLite)
     ├── [greeting / chat / security]
     │         └── Direct Response Node ──► END
     │
     └── [question / summary / onboarding / planner …]
               │
               ▼
         Retrieval Node  ──► Pinecone (vector search)
               │
               ├── [question / summary]
               │         └── Evaluation Agent ──► END
               │
               └── [onboarding / planner / checklist]
                         └── Planning Agent
                                   └── Evaluation Agent ──► END
```

---

## Agents

| Agent | File | Responsibility |
|---|---|---|
| Ingestion Agent | `agents/ingestion_agent.py` | Parse → PII check → Chunk → Embed → Store |
| Orchestrator Agent | `agents/orchestrator_agent.py` | Intent classification, memory loading, routing |
| Planning Agent | `agents/planning_agent.py` | Roadmaps, checklists, personalised recommendations |
| Evaluation Agent | `agents/evaluation_agent.py` | Groundedness verification of generated answers |

---

## Project Structure

```
kt-agent/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── requirements.txt
│   ├── agents/                  # Multi-agent logic
│   ├── graph/                   # LangGraph pipeline
│   ├── routes/                  # API endpoints (auth, chat, ingest, profile)
│   ├── services/                # OpenAI + Pinecone wrappers
│   ├── tools/                   # Chunker, PII detector, duplicate detector, parser
│   ├── memory/                  # SQLite CRUD (conversations, profiles, progress)
│   └── core/                    # Config, logger, Pydantic schemas
└── frontend/
    ├── index.html
    ├── css/style.css
    └── js/app.js
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key (`gpt-4o` + `text-embedding-3-small`)
- Pinecone account with an index (dimension: 1536, metric: cosine)

### 1. Clone & install

```bash
git clone <your-repo-url>
cd kt-agent
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env   # then fill in your keys
```

Required variables:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI secret key |
| `PINECONE_API_KEY` | Your Pinecone API key |
| `PINECONE_INDEX_NAME` | Name of your Pinecone index |
| `PINECONE_ENVIRONMENT` | e.g. `us-east-1-aws` |
| `SQLITE_DB_PATH` | Path for the SQLite database file |
| `APP_SECRET_KEY` | Random secret for session signing |

### 3. Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. Open the frontend

Open `frontend/index.html` directly in a browser, or serve it:

```bash
python -m http.server 5500 --directory frontend
```

Then visit `http://localhost:5500`.

**Demo credentials**

| Username | Password | Role |
|---|---|---|
| `alex` | `kt2024` | New Joiner |
| `sarah` | `kt2024` | Senior Backend Engineer |
| `demo` | `kt2024` | Software Engineer |


---

## Supported File Types for Ingestion

| Type | Format |
|---|---|
| Documents | PDF, DOCX, TXT, Markdown |
| Images (OCR) | PNG, JPEG, WebP, GIF |
| Audio (Whisper) | MP3, MP4, M4A, WAV, WebM, OGG |

Maximum file size: **50 MB**

---

## License

This project is licensed under the [MIT License](LICENSE).
