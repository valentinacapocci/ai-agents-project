from functools import cached_property

from labs.week06_memory_mcp_a2a.starter.memory import MemoryStore as Week6MemoryStore

from .chunking import load_chunks
from .retrieval import DenseIndex


class MemoryStore(Week6MemoryStore):
    @cached_property
    def corpus_index(self) -> DenseIndex:
        return DenseIndex(load_chunks(size=600, overlap=80))

    def search(self, subject: str, query: str, k: int = 3) -> list[str]:
        """Return matching resident facts, then fill remaining slots from the corpus."""
        if k <= 0:
            return []

        facts = super().search(subject, query, k)
        remaining = k - len(facts)
        if remaining == 0:
            return facts

        passages = self.corpus_index.search(query, k=remaining)
        return facts + [
            f"{chunk.doc_id} | {chunk.section}\n{chunk.text}"
            for chunk in passages
        ]