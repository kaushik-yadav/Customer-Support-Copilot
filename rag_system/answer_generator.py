import google.generativeai as genai

from rag_system.config import get_rag_key

from .config import get_rag_key

# Configure Gemini
genai.configure(api_key=get_rag_key())

def answer_with_context(query, docs):
    context = "\n\n".join([f"Source: {d['url']}\nContent: {d['content']}" for d in docs])
    prompt = f"""
        You are a customer support assistant. Use the provided context to answer the user's query but dont mention about any context/documentation in the answer. NO greetings needed just provide the answer through context given. **ALWAYS and MUST** Include proper URLs for citations where relevant.
    
        Query: {query}
    
        Context:
        {context}
    
        NOTE: Do NOT mention context, documentation, or technical sources.
        - If the context fully answers, give a concise, friendly response with citations.
        - **STRICTLY** : ALWAYS PROVIDE CITATIONS.
        - If not, politely say you don't have the answer and assure: "Your ticket is recorded and will be sent to the appropriate team."
    """

    model = genai.GenerativeModel("models/gemini-2.5-flash-lite-preview-06-17")
    resp = model.generate_content(prompt)
    return resp.text.strip()