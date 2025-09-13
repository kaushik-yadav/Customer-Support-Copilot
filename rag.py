import json
import os
import uuid
from time import time

import google.generativeai as genai
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_KEY")
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
def load_json_file(file, chunk_size = 500, overlap = 50):
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

# checking if the indices exist or not in vectorstore
def index_exists(vectorstore):
    try:
        count = vectorstore._collection.count()
        return count > 0
    except Exception:
        return False

# Build index for one collection
def build_index(collection_name, file, batch_size = 1000):
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

    chunks = load_json_file(file)

    texts = [c["content"] for c in chunks]
    metadatas = [{"url": c["url"], "doc_id": c["doc_id"]} for c in chunks]
    ids = [c["doc_id"] for c in chunks]
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_meta = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        vectorstore.add_texts(texts=batch_texts, metadatas=batch_meta, ids=batch_ids)
    print(f"Indexed {len(chunks)} chunks into {collection_name}.")


# RAG search
def rag(query, collection_key, k = 4, fetch_k = 75):
    col = COLLECTIONS[collection_key]
    store_dir = os.path.join(PERSIST_DIR, col["name"])
    vectorstore = Chroma(
        collection_name=col["name"],
        persist_directory=store_dir,
        embedding_function=embedding_function,
    )
    # using MMR for better coverage and diversity
    docs = vectorstore.max_marginal_relevance_search(query, k=k, fetch_k=fetch_k)

    return [{"content": d.page_content, "url": d.metadata.get("url")} for d in docs]

# Answer based on context (using gemini flash model)
def answer_with_context(query, docs):
    context = "\n\n".join([f"Source: {d['url']}\nContent: {d['content']}" for d in docs])
    prompt = f"""
    You are a customer support assistant. Use the provided context to answer the user's query but dont mention about any context/documentation in the answer. NO greetings needed just provide the answer trhough context given. Include proper URLs for citations where relevant.

    Query: {query}

    Context:
    {context}

    NOTE: Do NOT mention context, documentation, or technical sources.
    - If the context fully answers, give a concise, friendly response with citations.
    - **STRICTLY** : ALWAYS PROVIDE CITATIONS.
    - If not, politely say you don’t have the answer and assure: "Your ticket is recorded and will be sent to the appropriate team."
    """

    model = genai.GenerativeModel("models/gemini-2.5-flash-lite-preview-06-17")
    resp = model.generate_content(prompt)
    return resp.text.strip()

# Classify query into developer, documentation to better classify for RAG
def classify_query(query: str) -> str:
    prompt = f"""
        Given the user query, decide whether it should be answered using the developer knowledge base (technical API / SDK / code-focused content) or the documentation knowledge base (user guides, best practices, feature overviews).
        If the query involves implementation details, dev errors, or code usage, choose developer.
        If it involves product usage, configuration, or administrative guidance, choose documentation.
        Query: {query}
        Answer with one word: developer, documentation.
    """
    model = genai.GenerativeModel("models/gemini-2.5-flash-lite-preview-06-17")
    resp = model.generate_content(prompt)
    label = resp.text.strip().lower()
    if "dev" in label:
        return "developer"
    else:
        return "documentation"

def rag_answer(q):
    start = time()
    # Build indices (only first run)
    for key, val in COLLECTIONS.items():
        build_index(val["name"], val["file"])

    
    # adding a label on it for better classification
    label = classify_query(q)
    print(f"\nClassified as: {label}")
    results = rag(q, label)
    print(results)
    try:
        results = rag(q, label)
        # answering based on retrieved context
        final_answer = answer_with_context(q, results)
        print("\n--- FINAL ANSWER ---")
        print(final_answer)
        end = time()
        print(end-start)
        return final_answer
    except Exception as e:
        print("Exception occured :",e)
        return
