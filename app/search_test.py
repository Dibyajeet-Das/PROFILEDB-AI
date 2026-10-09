import logging
from app.embedding import EmbeddingService
from app.chroma import ChromaService

logging.basicConfig(level=logging.WARNING)

embedder = EmbeddingService()
chroma = ChromaService()

queries = [
    "Why did user creation fail?",
    "Exception while creating user",
    "authentication error",
    "token expired or invalid",
    "database connection problem",
    "sync failed",
]

for q in queries:
    res = chroma.search(embedder.create_query_embedding(q), top_k=3)
    print(f"\n=== {q}")
    for doc, dist in zip(res["documents"][0], res["distances"][0]):
        print(f"[{dist:.3f}] {doc[:250]}")