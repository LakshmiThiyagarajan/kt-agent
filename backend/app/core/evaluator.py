import json
from datetime import datetime
from pathlib import Path

from langchain_openai import ChatOpenAI
import os


llm_judge = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",
    temperature=0
)


LOG_FILE = Path("evaluation_logs.json")


def evaluate_answer(question: str, context: str, answer: str) -> dict:
    prompt = f"""
You are an evaluator for a RAG (Retrieval Augmented Generation) system.

You must score the assistant's answer from 1 to 5 on the following:

1. Context Relevance:
Are the retrieved context chunks relevant to the question?

2. Faithfulness:
Is the answer strictly based on the provided context without hallucination?

3. Completeness:
Does the answer fully address the question?

4. Overall Quality:
Is the answer clear, correct, and helpful?

Return ONLY a JSON like this:
{{
    "relevance": number,
    "faithfulness": number,
    "completeness": number,
    "overall": number
}}

Question:
{question}

Context:
{context}

Answer:
{answer}
"""

    response = llm_judge.invoke(prompt).content.strip()

    try:
        scores = json.loads(response)
    except:
        scores = {
            "relevance": 0,
            "faithfulness": 0,
            "completeness": 0,
            "overall": 0
        }

    log_evaluation(question, context, answer, scores)

    return scores


def log_evaluation(question, context, answer, scores):
    entry = {
        "timestamp": str(datetime.now()),
        "question": question,
        "answer": answer,
        "context": context[:2000],  # prevent huge logs
        "scores": scores
    }

    logs = []
    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)

    logs.append(entry)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)