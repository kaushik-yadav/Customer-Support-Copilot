import json
import os
import uuid
from typing import Dict, List

import google.generativeai as genai
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Directories
PERSIST_DIR = "./chroma_store"

# Embedding model
embedding_function = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

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

# Helper: load + chunk JSON
def load_json_file(file: str, chunk_size: int = 500, overlap: int = 50):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=overlap
    )
    all_chunks = []

    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    for obj in data:
        url = obj.get("url", "N/A")
        content = obj.get("content") or obj.get("text") or ""
        if not content.strip():
            continue
        chunks = splitter.split_text(content)
        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            all_chunks.append(
                {
                    "doc_id": chunk_id,
                    "content": chunk,
                    "url": url,
                }
            )
    print(f"[debug] Extracted {len(all_chunks)} chunks from {file}")
    return all_chunks

def index_exists(vectorstore) -> bool:
    try:
        count = vectorstore._collection.count()  # low-level Chroma API
        return count > 0
    except Exception:
        return False

# Build index for one collection
def build_index(collection_name: str, file: str, batch_size: int = 1000):
    store_dir = os.path.join(PERSIST_DIR, collection_name)
    vectorstore = Chroma(
        collection_name=collection_name,
        persist_directory=store_dir,
        embedding_function=embedding_function,
    )

    # Skip if already built
    if index_exists(vectorstore):
        print(f"Skipping build for {collection_name}, already exists.")
        return

    print("-- Started chunking")
    chunks = load_json_file(file)
    print("-- Chunking done")
    texts = [c["content"] for c in chunks]
    metadatas = [{"url": c["url"], "doc_id": c["doc_id"]} for c in chunks]
    ids = [c["doc_id"] for c in chunks]
    print("-- Batch indexing started")
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_meta = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        vectorstore.add_texts(texts=batch_texts, metadatas=batch_meta, ids=batch_ids)
    print("-- Indexing done")
    print(f"✅ Indexed {len(chunks)} chunks into {collection_name}.")


# RAG search
def rag(query: str, collection_key: str, k: int = 5, fetch_k: int = 75) -> List[Dict]:
    col = COLLECTIONS[collection_key]
    store_dir = os.path.join(PERSIST_DIR, col["name"])
    vectorstore = Chroma(
        collection_name=col["name"],
        persist_directory=store_dir,
        embedding_function=embedding_function,
    )
    docs = vectorstore.max_marginal_relevance_search(query, k=k, fetch_k=fetch_k)

    return [{"content": d.page_content, "url": d.metadata.get("url")} for d in docs]

if __name__ == "__main__":
    # Build indices (only first run)
    print("-- Building indices")
    for key, val in COLLECTIONS.items():
        build_index(val["name"], val["file"])
    print("-- Indices built")
    # Example query
    q = """I've just had a new user, 'test.user@company.com', log in via our newly configured SSO. They were authenticated successfully, but they were not added to the 'Data Analysts' group as expected based on our SAML assertions. This is preventing them from accessing any assets. What could be the reason for this mis-assignment?."""
    results = rag(q, "developer")
    print(results)
    print("-- Retrieval done")
