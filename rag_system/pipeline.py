from time import time

from rag_system.answer_generator import answer_with_context
from rag_system.config import COLLECTIONS
from rag_system.query_classifier import classify_query
from rag_system.vector_store import build_index, rag_search


def rag_answer(q):
    start = time()
    # Build indices (only first run)
    for key, val in COLLECTIONS.items():
        build_index(val["name"], val["file"])
    
    # adding a label on it for better classification
    label = classify_query(q)
    print(f"\nClassified as: {label}")
    
    try:
        results = rag_search(q, label)
        print(results)
        # answering based on retrieved context
        final_answer = answer_with_context(q, results)
        print("\n--- FINAL ANSWER ---")
        print(final_answer)
        end = time()
        print(end-start)
        return final_answer
    except Exception as e:
        print("Exception occured :", e)
        return None