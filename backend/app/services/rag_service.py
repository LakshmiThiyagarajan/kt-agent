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

    # 2. Query Pinecone with the vector
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        namespace=NAMESPACE,
    )

    # 3. Build context from matches
    context = ""
    for match in results["matches"]:
        context += match["metadata"]["text"] + "\n\n"

    return context


def generate_answer(query: str) -> str:
    context = retrieve_context(query)

    prompt = f"""
You are KT Assistant. You help users using ONLY the project documents.

STEP 1 — Greetings:
If the user says hi/hello/hey → greet politely.
If the user says thanks → reply politely.

STEP 2 — Check the knowledge:
If the knowledge below is EMPTY or does NOT contain the answer, say:
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
    return response.content.strip()