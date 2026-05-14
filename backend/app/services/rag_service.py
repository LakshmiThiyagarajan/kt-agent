from app.core.pinecone_client import get_index
from app.core.config import NAMESPACE
from app.core.embeddings import get_embedding

from langchain_openai import ChatOpenAI
import os

llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini"
)


def retrieve_context(query: str, top_k: int = 3) -> str:
    index = get_index()

    # 1. Convert question to embedding
    query_embedding = get_embedding(query)

    # 2. Search Pinecone
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        namespace=NAMESPACE,
    )

    matches = results.get("matches", [])

    # ❗ If nothing matches, it's NOT a project question
    if not matches:
        return ""

    # 🔥 IMPORTANT — check similarity score of best match
    top_score = matches[0]["score"]

    # This number is the MAGIC
    # You can tune later: 0.40 / 0.45 / 0.50
    if top_score < 0.45:
        return ""

    # 3. Build context only if score is good
    context = ""
    for match in matches:
        context += match["metadata"]["text"] + "\n\n"

    return context


# ================= ANSWER GENERATION =================
def generate_answer(query: str) -> str:
    context = retrieve_context(query)

    prompt = f"""
You are KT Assistant. You help users using ONLY the project documents.

STEP 1 — Greetings:
If the user says hi/hello/hey → greet politely.
If the user says thanks → reply politely.

STEP 2 — Check the knowledge:
If the knowledge below is EMPTY, say:
"This information is not available in the project documents."

STEP 3 — If knowledge contains the answer:
Answer using ONLY the knowledge. Give a clear, direct answer.

STEP 4 — If unrelated to project:
Say: "I am here to help only with KT and project-related questions."

Knowledge:
{context}

Question:
{query}
"""

    response = llm.invoke(prompt)
    answer = response.content.strip()

    try:
        from app.core.evaluator import evaluate_answer
        evaluate_answer(query, context, answer)
    except Exception as e:
        print("Evaluation error:", e)

    # Step 5 — Return answer to API → React UI
    return answer