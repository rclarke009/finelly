## 6. Embedder interface and a first implementation

# Define a small abstraction for “turn a list of strings into a list 
# of vectors”: e.g. an `Embedder` with something like `embed_many(texts: 
# list[str]) -> list[list[float]]`, plus `model` and `dim` so the rest of 
# the app knows the embedding model and dimension. Implement a first 
# version: either a **stub** that returns deterministic same-dimension 
# vectors (e.g. from a simple hash of the text) so you can run the full 
# pipeline without an API, or a real client that calls an embedding API. 
# Prefer starting with the stub so you can finish ingest and ask 
# end-to-end, then swap in the real embedder.

from dataclasses import dataclass
from app.embeddings_client import embed_texts
from app.config import EMBED_MODEL

DIM_FOR_MODEL = {"nomic-embed-text": 768}    #old settings for chatgpt {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072}


@dataclass
class Embedder():
    '''Defines the attributes of the embedding that will take place'''
    model: str
    dim: int

class HttpEmbedder(Embedder):
    '''HttpEmbedder is the concrete embedder that uses the local model for embedding ###HTTP API (OpenAI):'''
    def __init__(self, model: str | None = None, dim: int | None = None):
        model = model or EMBED_MODEL
        dim = dim or DIM_FOR_MODEL.get(model, 768)          # old settings for chatgpt 1536)
        super().__init__(model=model, dim=dim)
        
    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return await embed_texts(texts)     # the embed_texts is async so if you forget await, you don't get the list of vectors back, you get the coroutine

