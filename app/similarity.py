## 7. Cosine similarity and retrieval

# Implement a function that computes cosine similarity between two vectors 
# (same length), and handle the case where a vector has zero length so you don’t 
# divide by zero. Then implement retrieval: given a query vector, load the 
# stored chunk embeddings (optionally filtered by `doc_id`), compute similarity 
# of the query to each, sort by score descending, and return the top-k chunks 
# with their content and scores. Return structures that match what your ask r
# esponse needs (e.g. chunk_id, doc_id, score, content_snippet). Cap the number 
# of candidates (e.g. 5k) if you’re loading all into memory so you don’t blow up 
# on huge DBs.

# **Why now:** Ask will “embed question → retrieve top-k → send to LLM.” Retrieval is the bridge between the query vector and the chunks you’ll put in the prompt.

# **Check:** With a few chunks and embeddings in the DB, you can call your retrieval function with a query vector and get back the expected top-k (e.g. by embedding a sentence and checking that the chunk containing that sentence ranks high).

# Part D — Similarity search (query vector ↔ chunk vectors)
# This is the Retrieval step in the RAG pipeline

# The user’s question is turned into a vector (same embedding model as your chunks).
# You need to compare that query vector to every chunk vector to see which chunks are most similar.
# Cosine similarity is the usual measure: it’s the cosine of the angle between two vectors, in the range -1 to 1 (1 = same direction, 0 = orthogonal, -1 = opposite). Higher means more similar.

# a single function that, given two vectors a and b, returns that score. That score will later be used in D2 (retrieve_top_k) to sort chunks and return the top‑k.

# Prompt D1 — Cosine similarity
# Create similarity.py:
# def cosine_similarity(a: list[float], b: list[float]) -> float
# Handle edge cases (zero vector)

from math import sqrt

def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: len(a) is {len(a)} but len(b) is {len(b)} Vectors must have the same length")
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = sqrt(sum(x**2 for x in a))
    norm_b = sqrt(sum(x**2 for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0  # not similar
    return dot / (norm_a * norm_b)

