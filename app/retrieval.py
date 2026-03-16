# Prompt D2 — Retrieval function
# Create retrieval.py:
# def retrieve_top_k(db, query_vec, top_k, doc_id=None) -> list[RetrievedChunk]

# comparing the question vector to each chunk vector; higher cosine similarity 
# means that chunk is more relevant to the question.
# Load candidate embeddings (all chunks, or only for doc_id).
# Compute cosine similarity in Python.
# Sort by score descending.
# Return top top_k results with chunk content.



from app.models import RetrievedChunk
from app.db import get_embeddings_for_retrieval
from app.similarity import cosine_similarity


def retrieve_top_k(db, query_vec, top_k, doc_id=None, doc_ids=None) -> list[RetrievedChunk]:
    all_candidates = get_embeddings_for_retrieval(db, doc_id=doc_id, doc_ids=doc_ids)
    candidates = all_candidates[:5000]                                  # in case there are too many, just work on the top 5000
    
    scored: list[tuple[float, str, str, str]] = []

    # Build a list of scored candidates in the loop
    for chunk_id, doc_id, vector, content in candidates:        # Vector here is already a list of floats, not raw Json
        score = cosine_similarity(query_vec, vector)            # query_vec is the vector from the user's inquiry and vector_json is from the contextual data that we put in the db?
        # we should be updating a list that we will later sort? or adding the score to a tuple or dict?
        scored.append((score, chunk_id, doc_id, content))

    # Sort by score descending and take top_k
    scored.sort(key=lambda x: x[0], reverse = True)
    top = scored[:top_k]

    return [
        RetrievedChunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            score=score,
            content_snippet=content[:500] if len(content) > 500 else content,
        )
        for score, chunk_id, doc_id, content in top
    ]