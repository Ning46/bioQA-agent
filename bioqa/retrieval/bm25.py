"""Okapi BM25 稀疏检索。"""
from __future__ import annotations

import math
from collections import Counter

from .text import Chunk, tokenize


class BM25Retriever:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.chunks: list[Chunk] = []
        self.tf: list[Counter] = []
        self.df: Counter = Counter()
        self.avgdl = 0.0

    def build(self, chunks: list[Chunk]) -> None:
        self.chunks = list(chunks)
        self.tf = [Counter(c.tokens) for c in self.chunks]
        self.df = Counter()
        for tf in self.tf:
            self.df.update(tf.keys())
        self.avgdl = sum(len(c.tokens) for c in self.chunks) / max(len(self.chunks), 1)

    def _idf(self, term: str) -> float:
        n, df = len(self.chunks), self.df.get(term, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int = 10) -> list[tuple[Chunk, float]]:
        q_terms = tokenize(query)
        scores = []
        for chunk, tf in zip(self.chunks, self.tf, strict=True):
            dl = len(chunk.tokens)
            s = 0.0
            for t in q_terms:
                f = tf.get(t, 0)
                if f:
                    s += self._idf(t) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if s > 0:
                scores.append((chunk, s))
        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]
