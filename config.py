import os
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sentence_transformers import SentenceTransformer
from langchain_groq import ChatGroq


load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    st.error("❌ ERROR: GROQ_API_KEY is missing! Please check your .env file.")
    st.stop()

if not os.getenv("DATABASE_URL"):
    st.error("❌ ERROR: DATABASE_URL is missing!")
    st.stop()

# Cache DB Engine
@st.cache_resource
def get_db_engine():
    DATABASE_URL = os.getenv(DATABASE_URL);
    return create_engine(DATABASE_URL, pool_pre_ping=True)

# Cache Embedder
@st.cache_resource
def get_embedder():
    return SentenceTransformer('all-mpnet-base-v2')

# Load LLMs
def get_llms():
    extractor_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, model_kwargs={"response_format": {"type": "json_object"}})
    chat_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.3)
    return extractor_llm, chat_llm