from openai import OpenAI
from .config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def get_embedding(text: str):
    res = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return res.data[0].embedding