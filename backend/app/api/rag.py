from fastapi import APIRouter
from pydantic import BaseModel

from app.services.rag_service import generate_answer

router = APIRouter()


class Question(BaseModel):
    query: str


@router.post("/ask")
def ask_question(q: Question):
    reply = generate_answer(q.query)
    return {"reply": reply}
