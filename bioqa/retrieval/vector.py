"""稠密向量检索。

默认使用 LSA 嵌入（字符 n-gram TF-IDF + TruncatedSVD），完全离线、无需下载模型，
能捕捉 BM25 抓不到的近义和部分匹配。Embedder 是可替换接口，
接入 sentence-transformers / bge 等真实嵌入模型时只需实现 fit/encode。
"""
from __future__ import annotations

from typing import Protocol

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from .text import Chunk


class Embedder(Protocol):
    def fit(self, texts: list[str]) -> None: ...
    def encode(self, texts: list[str]) -> np.ndarray: ...


class LSAEmbedder:
    def __init__(self, dim: int = 96, seed: int = 0):
        self.dim, self.seed = dim, seed
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 3), sublinear_tf=True, lowercase=True)
        self.svd: TruncatedSVD | None = None

    def fit(self, texts: list[str]) -> None:
        x = self.vec.fit_transform(texts)
        dim = min(self.dim, x.shape[0] - 1, x.shape[1] - 1)
        self.svd = TruncatedSVD(n_components=max(dim, 2), random_state=self.seed).fit(x)

    def encode(self, texts: list[str]) -> np.ndarray:
        assert self.svd is not None, "call fit() first"
        z = self.svd.transform(self.vec.transform(texts))
        norms = np.linalg.norm(z, axis=1, keepdims=True)
        return z / np.clip(norms, 1e-12, None)


class VectorRetriever:
    def __init__(self, embedder: Embedder | None = None):
        self.embedder = embedder or LSAEmbedder()
        self.chunks: list[Chunk] = []
        self.matrix: np.ndarray | None = None
        self._fitted = False

    def build(self, chunks: list[Chunk], refit: bool = True) -> None:
        """refit=False 时复用已训练的嵌入空间，只对块做编码（增量更新用）。"""
        self.chunks = list(chunks)
        texts = [c.text for c in self.chunks]
        if refit or not self._fitted:
            self.embedder.fit(texts)
            self._fitted = True
        self.matrix = self.embedder.encode(texts) if texts else np.zeros((0, 1))

    def add(self, chunks: list[Chunk]) -> None:
        """在已有嵌入空间中折入（fold-in）新块，不重新训练。"""
        if not chunks:
            return
        new = self.embedder.encode([c.text for c in chunks])
        self.chunks.extend(chunks)
        self.matrix = new if self.matrix is None or len(self.matrix) == 0 else np.vstack([self.matrix, new])

    def remove_docs(self, doc_ids: set[str]) -> None:
        keep = [i for i, c in enumerate(self.chunks) if c.doc_id not in doc_ids]
        self.chunks = [self.chunks[i] for i in keep]
        self.matrix = self.matrix[keep] if self.matrix is not None else None

    def search(self, query: str, top_k: int = 10) -> list[tuple[Chunk, float]]:
        if not self.chunks:
            return []
        q = self.embedder.encode([query])[0]
        sims = self.matrix @ q
        idx = np.argsort(-sims)[:top_k]
        return [(self.chunks[i], float(sims[i])) for i in idx]
