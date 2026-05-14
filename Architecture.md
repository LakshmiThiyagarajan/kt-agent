
---

# ✅ 2. `ARCHITECTURE.md`

```markdown
# KT-Agent Architecture

KT-Agent follows a production-style RAG architecture.

## Upload Flow

1. File uploaded
2. SHA256 hash computed
3. If hash exists → skip
4. If new → chunk → embed → store in Pinecone
5. Upload logged in upload_logs.db

## Question Answer Flow

1. User asks question
2. Question embedding created
3. Pinecone similarity search
4. If similarity low → no retrieval
5. If similarity high → retrieve top chunks
6. GPT generates answer from context
7. GPT evaluates the answer
8. Evaluation logged

## Why Conditional Retrieval?

Avoids:
- Wasting Pinecone calls on greetings
- Polluting evaluation logs
- Unnecessary token usage

## Why Evaluation?

Most RAG systems stop at answering.

KT-Agent measures quality of answers automatically.