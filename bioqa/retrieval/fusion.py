"""Reciprocal Rank Fusion（RRF）。

RRF 只看排名不看分值，避免了 BM25 分数与余弦相似度量纲不一致的问题：
    score(d) = Σ_r 1 / (k + rank_r(d))
"""
from __future__ import annotations

from .text import Chunk


def rrf_fuse(rankings: list[list[tuple[Chunk, float]]], k: int = 60, top_k: int = 20) -> list[tuple[Chunk, float]]:
    scores: dict[str, float] = {}
    by_id: dict[str, Chunk] = {}
    for ranking in rankings:
        for rank, (chunk, _) in enumerate(ranking, start=1):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank)
            by_id[chunk.chunk_id] = chunk
    fused = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
    return [(by_id[cid], s) for cid, s in fused]
