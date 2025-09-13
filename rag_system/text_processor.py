import json
import uuid

from langchain.text_splitter import RecursiveCharacterTextSplitter


# load the files and convert into chunks
def load_json_file(file, chunk_size=500, overlap=50):
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