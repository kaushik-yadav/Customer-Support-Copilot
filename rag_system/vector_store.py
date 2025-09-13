import os

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from rag_system.config import PERSIST_DIR
from rag_system.text_processor import load_json_file

# Embedding model
embedding_function = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

def index_exists(vectorstore):
    try:
        count = vectorstore._collection.count()
        return count > 0
    except Exception:
        return False

def build_index(collection_name, file, batch_size=1000):
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

def rag_search(query, collection_key, k=4, fetch_k=75):
    from rag_system.config import COLLECTIONS, PERSIST_DIR
    
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