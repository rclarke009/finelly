# Re-ranker: second-stage retrieval using a local cross-encoder.
# Scores (query, passage) pairs and returns chunks sorted by relevance.

import logging
from typing import TYPE_CHECKING

from app.config import RERANK_MODEL
from app.models import RetrievedChunk

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

_cross_encoder: "CrossEncoder | None" = None


def _get_cross_encoder() -> "CrossEncoder":
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder

        logger.info("Loading re-ranker model: %s", RERANK_MODEL)
        _cross_encoder = CrossEncoder(RERANK_MODEL)
    return _cross_encoder


def rerank(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    """Re-rank chunks by relevance to the query using a cross-encoder. Returns top_k chunks with updated scores."""
    if not chunks:
        return []
    if top_k <= 0:
        return []

    model = _get_cross_encoder()
    pairs = [(query, c.content_snippet) for c in chunks]
    scores = model.predict(pairs)

    scored = list(zip(scores, chunks))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    return [
        RetrievedChunk(
            chunk_id=c.chunk_id,
            doc_id=c.doc_id,
            score=float(score),
            content_snippet=c.content_snippet,
        )
        for score, c in top
    ]
