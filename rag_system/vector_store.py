import os
import sys

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from rag_system.config import COLLECTIONS, PERSIST_DIR
from rag_system.text_processor import load_json_file

# Embedding model
embedding_function = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


def index_exists(collection_name):
    store_dir = os.path.join(PERSIST_DIR, collection_name)
    faiss_index_path = os.path.join(store_dir, "index.faiss")
    return os.path.exists(faiss_index_path)


def build_index(collection_name, file):
    store_dir = os.path.join(PERSIST_DIR, collection_name)
    os.makedirs(store_dir, exist_ok=True)

    if index_exists(collection_name):
        print(f"Skipping build for {collection_name}, already exists.")
        return

    chunks = load_json_file(file)
    texts = [c["content"] for c in chunks]
    metadatas = [{"url": c["url"], "doc_id": c["doc_id"]} for c in chunks]

    # Split into smaller chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.create_documents(texts=texts, metadatas=metadatas)

    # Build FAISS index
    vectorstore = FAISS.from_documents(docs, embedding_function)

    # Save index locally
    faiss_index_path = os.path.join(store_dir, "index.faiss")
    vectorstore.save_local(faiss_index_path)
    print(f"Indexed {len(docs)} chunks into {collection_name}.")


def mmr_rerank(query_embedding, candidate_embeddings, candidate_texts, alpha=0.5, top_k=4):
    """
    Simple Maximal Marginal Relevance (MMR) reranker.
    - candidate_embeddings: embeddings of retrieved documents
    - candidate_texts: original document objects
    """
    import numpy as np

    selected = []
    remaining = list(range(len(candidate_texts)))
    similarity = lambda x, y: np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y))

    while len(selected) < top_k and remaining:
        scores = []
        for i in remaining:
            sim_to_query = similarity(query_embedding, candidate_embeddings[i])
            sim_to_selected = max([similarity(candidate_embeddings[i], candidate_embeddings[j]) for j in selected], default=0)
            score = alpha * sim_to_query - (1 - alpha) * sim_to_selected
            scores.append(score)
        best_idx = remaining[np.argmax(scores)]
        selected.append(best_idx)
        remaining.remove(best_idx)

    return [candidate_texts[i] for i in selected]


def rag_search(query, collection_key, k=4, fetch_k=75, alpha=0.5):
    """
    FAISS-based RAG search with MMR reranking.
    """
    col = COLLECTIONS[collection_key]
    store_dir = os.path.join(PERSIST_DIR, col["name"])
    faiss_index_path = os.path.join(store_dir, "index.faiss")

    # Load FAISS index
    vectorstore = FAISS.load_local(faiss_index_path, embedding_function, allow_dangerous_deserialization=True)

    # Retrieve more than k for reranking
    docs = vectorstore.similarity_search(query, k=fetch_k)

    # Compute embeddings for reranking
    candidate_embeddings = [embedding_function.embed_query(d.page_content) for d in docs]

    # Compute query embedding
    query_embedding = embedding_function.embed_query(query)

    # Apply MMR rerank
    top_docs = mmr_rerank(query_embedding, candidate_embeddings, docs, alpha=alpha, top_k=k)

    return [{"content": d.page_content, "url": d.metadata.get("url")} for d in top_docs]
