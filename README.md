# KT-Agent 

KT-Agent is a Retrieval Augmented Generation (RAG) assistant built to answer questions **strictly from project Knowledge Transfer (KT) documents**.

It allows team members to upload project documents and ask questions about architecture, flows, deployment, services, datasets, and implementation — without hallucination.

---

## What Problem This Solves

During KT, project knowledge is scattered across:
- PDFs
- Docs
- Notes
- Emails

KT-Agent converts all of that into a searchable knowledge base where answers are generated **only from uploaded documents**.

---

## Tech Stack

- **Backend**: FastAPI
- **Frontend**: React
- **Vector DB**: Pinecone
- **LLM**: OpenAI GPT
- **Embeddings**: OpenAI Embeddings
- **Evaluation**: GPT-based RAG evaluator
- **Logging**: Upload log + Evaluation log

---

## How It Works (Flow)

1. User uploads project documents
2. Documents are chunked → embedded → stored in Pinecone
3. User asks a question
4. System checks if question is project-related (via vector similarity)
5. Relevant chunks are retrieved
6. GPT generates answer **only from context**
7. Answer is automatically evaluated and logged

---

##  Features

- Duplicate file upload prevention (SHA256 hash check)
- Conditional retrieval (no waste Pinecone calls)
- GPT evaluation of every answer
- Evaluation logs for RAG quality tracking
- Strict anti-hallucination prompting
- Modular backend architecture

---

##  Project Structure



---

## Evaluation

Every answer generated is scored on:
- Context Relevance
- Faithfulness (no hallucination)
- Completeness
- Overall quality

See: `evaluation_logs.json`

---

## Run Locally

### backend

pip install -r requirements.txt
uvicorn backend.app:app --reload

### frontend

cd frontend
npm install
npm start

## Futhur details 

See Future_Improvements.md
See Architecture.md