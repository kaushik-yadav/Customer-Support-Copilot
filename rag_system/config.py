import os

from dotenv import load_dotenv

load_dotenv()

def get_rag_key():
    """Return API key for RAG pipeline"""
    try:
        import streamlit as st
        return st.secrets["GEMINI_KEY"]
    except Exception:
        return os.getenv("GEMINI_KEY")


# directory for chroma store (embeddings + indices storing)
PERSIST_DIR = "./chroma_store"

COLLECTIONS = {
    "developer": {
        "name": "atlan_developer",
        "file": "knowledge_base/atlan_developer.json"
    },
    "documentation": {
        "name": "atlan_documentation",
        "file": "knowledge_base/atlan_documentation.json"
    },
}

