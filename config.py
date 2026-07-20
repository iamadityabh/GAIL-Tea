import os
import sys
from functools import lru_cache
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sentence_transformers import SentenceTransformer
from langchain_ollama import ChatOllama

load_dotenv()

# 1. ❌ GROQ_API_KEY ka check hata diya kyunki ab hum offline Ollama use kar rahe hain
if not os.getenv("DATABASE_URL"):
    print("❌ ERROR: DATABASE_URL is missing!")
    sys.exit(1)

# 2. 🔥 SMART URL: Agar Docker mein hai toh ENV wala URL lega, warna local PC ka localhost lega
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Cache DB Engine
@lru_cache(maxsize=1)
def get_db_engine():
    DATABASE_URL = os.getenv("DATABASE_URL")
    return create_engine(DATABASE_URL, pool_pre_ping=True)

# Cache Embedder (100% Offline, 768-dim)
@lru_cache(maxsize=1)
def get_embedder():
    return SentenceTransformer('all-mpnet-base-v2')

# Load LLMs (Completely Offline using Ollama)
def get_llms():
    # Extractor: Uses Ollama with forced JSON output mode
    extractor_llm = ChatOllama(
        model="llama3.1:latest", # Agar aapne 3.2:8b download kiya hai toh yahan naam change kar lena
        temperature=0, 
        format="json",       # Groq ke response_format ki jagah Ollama mein 'format="json"' use hota hai
        base_url=OLLAMA_URL  
    )
    
    # Chat LLM: Standard conversational flow
    chat_llm = ChatOllama(
        model="llama3.1:latest", 
        temperature=0.3,
        base_url=OLLAMA_URL
    )
    
    return extractor_llm, chat_llm