import os
import sys
from functools import lru_cache
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sentence_transformers import SentenceTransformer
from langchain_groq import ChatGroq

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    print("❌ ERROR: GROQ_API_KEY is missing! Please check your .env file.")
    sys.exit(1)

if not os.getenv("DATABASE_URL"):
    print("❌ ERROR: DATABASE_URL is missing!")
    sys.exit(1)

# Cache DB Engine using standard Python caching
@lru_cache(maxsize=1)
def get_db_engine():
    DATABASE_URL = os.getenv("DATABASE_URL")
    return create_engine(DATABASE_URL, pool_pre_ping=True)

# Cache Embedder using standard Python caching
@lru_cache(maxsize=1)
def get_embedder():
    return SentenceTransformer('multi-qa-distilbert-cos-v1')

# Load LLMs
def get_llms():
    extractor_llm = ChatGroq(
        model="llama-3.1-8b-instant", 
        temperature=0, 
        model_kwargs={"response_format": {"type": "json_object"}}
    )
    chat_llm = ChatGroq(
        model="llama-3.1-8b-instant", 
        temperature=0.3
    )
    return extractor_llm, chat_llm