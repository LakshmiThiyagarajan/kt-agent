from pinecone import Pinecone
from app.core.config import PINECONE_API_KEY, INDEX_NAME

pc = Pinecone(api_key=PINECONE_API_KEY)

def get_index():
    return pc.Index(INDEX_NAME)