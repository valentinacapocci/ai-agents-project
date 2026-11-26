"""Week 7: build a dense index and compare it with keyword search."""

from __future__ import annotations

import json
import re
import time
import urllib.request
from uuid import uuid4

from chunking import Chunk
from project.models import EMBED, OLLAMA_URL

EMBED_MODEL = EMBED.name


def embed(texts: list[str], batch: int = 32) -> list[list[float]]:
    """Embed texts in batches, preserving their order."""
    if batch < 1:
        raise ValueError("Batch size must be positive.")

    vectors = []
    for start in range(0, len(texts), batch):
        group = texts[start:start + batch]
        request = urllib.request.Request(
            f"{OLLAMA_URL}/api/embed",
            data=json.dumps({"model": EMBED_MODEL, "input": group}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            embeddings = json.load(response)["embeddings"]

        if len(embeddings) != len(group):
            raise ValueError("Ollama returned a different number of embeddings than requested.")
        vectors.extend(embeddings)

    return vectors


class DenseIndex:
    def __init__(self, chunks: list[Chunk], name: str = "run_a"):
        import chromadb
        if not chunks:
            raise ValueError("Cannot build an index without chunks.")

        started = time.perf_counter()
        self.chunks = {chunk.chunk_id: chunk for chunk in chunks}
        vectors = embed([chunk.text for chunk in chunks])
        self.dim = len(vectors[0])

        self.client = chromadb.EphemeralClient()
        self.collection = self.client.create_collection(
            name=f"{name}-{uuid4().hex[:8]}",
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
        )
        self.collection.add(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=vectors,
            metadatas=[
                {"doc_id": chunk.doc_id, "section": chunk.section}
                for chunk in chunks
            ],
        )

        seconds = time.perf_counter() - started
        print(f"Index built with {EMBED_MODEL} in {seconds:.2f} seconds")

    def search(self, query: str, k: int = 20) -> list[Chunk]:
        if k <= 0:
            return []

        result = self.collection.query(
            query_embeddings=embed([query]),
            n_results=min(k, len(self.chunks)),
            include=[],
        )
        return [self.chunks[chunk_id] for chunk_id in result["ids"][0]]


def keyword_search(chunks: list[Chunk], query: str, k: int = 20) -> list[Chunk]:
    """Rank by shared query terms, breaking ties by chunk ID."""
    if k <= 0:
        return []

    query_terms = set(re.findall(r"\w+", query.casefold()))
    scored = []
    for chunk in chunks:
        chunk_terms = set(re.findall(r"\w+", chunk.text.casefold()))
        overlap = len(query_terms & chunk_terms)
        scored.append((overlap, chunk))

    scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
    return [chunk for _, chunk in scored[:k]]