import os

# Local dev
from dotenv import load_dotenv

load_dotenv()

def get_classification_key():
    """Return API key for classification pipeline"""
    try:
        import streamlit as st
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY")
