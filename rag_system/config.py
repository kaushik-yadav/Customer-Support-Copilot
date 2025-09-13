import os

from dotenv import load_dotenv

load_dotenv()

# API config
GOOGLE_API_KEY = os.getenv("GEMINI_KEY")

# directory for chroma store (embeddings + indices storing)
PERSIST_DIR = "./chroma_store"

# File mapping to collection
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
