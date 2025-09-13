import google.generativeai as genai

from rag_system.config import get_rag_key

from .config import get_rag_key

# Configure Gemini
genai.configure(api_key=get_rag_key())

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