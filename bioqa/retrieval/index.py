"""混合检索索引：BM25 + 向量双路召回 → RRF 融合 → 重排，以及基于文件哈希的增量更新。

增量更新流程（update()）：
1. 对知识库目录中每个文件计算 SHA-256，与上次的 manifest 比较，得到新增 / 修改 / 删除集合；
2. 只对新增和修改的文件重新切块、分词；未变化文件的块直接复用；
3. BM25 统计量重算（只是计数，代价低）；
4. 向量侧把新块折入已训练的嵌入空间，变化比例超过阈值时才整体重训。
"""
from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import dataclass, field
from pathlib import Path

from .bm25 import BM25Retriever
from .fusion import rrf_fuse
from .reranker import FeatureReranker, Reranker
from .text import Chunk, chunk_document
from .vector import VectorRetriever

SUPPORTED = {".md", ".txt"}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class UpdateReport:
    added: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    unchanged: int = 0
    vector_refit: bool = False

    @property
    def changed(self) -> bool:
        return bool(self.added or self.modified or self.deleted)

    def __str__(self) -> str:
        return (f"新增 {len(self.added)}，修改 {len(self.modified)}，删除 {len(self.deleted)}，"
                f"未变 {self.unchanged}，向量重训={self.vector_refit}")


class HybridIndex:
    def __init__(self, kb_dir: str | Path, reranker: Reranker | None = None,
                 refit_ratio: float = 0.3, rrf_k: int = 60):
        self.kb_dir = Path(kb_dir)
        self.bm25 = BM25Retriever()
        self.vector = VectorRetriever()
        self.reranker = reranker or FeatureReranker()
        self.refit_ratio = refit_ratio
        self.rrf_k = rrf_k
        self.manifest: dict[str, str] = {}          # doc_id -> sha256
        self.doc_chunks: dict[str, list[Chunk]] = {}  # doc_id -> chunks

    # ------------------------------------------------------------------ 构建与更新
    def _scan(self) -> dict[str, Path]:
        return {p.stem: p for p in sorted(self.kb_dir.iterdir()) if p.suffix in SUPPORTED}

    def build(self) -> UpdateReport:
        self.manifest, self.doc_chunks = {}, {}
        report = self.update(force_refit=True)
        return report

    def update(self, force_refit: bool = False) -> UpdateReport:
        files = self._scan()
        report = UpdateReport()
        new_hashes = {doc_id: file_hash(p) for doc_id, p in files.items()}

        for doc_id, h in new_hashes.items():
            old = self.manifest.get(doc_id)
            if old is None:
                report.added.append(doc_id)
            elif old != h:
                report.modified.append(doc_id)
            else:
                report.unchanged += 1
        report.deleted = [d for d in self.manifest if d not in new_hashes]

        if not report.changed and not force_refit:
            return report

        stale = set(report.modified) | set(report.deleted)
        for doc_id in stale:
            self.doc_chunks.pop(doc_id, None)
        fresh: list[Chunk] = []
        for doc_id in report.added + report.modified:
            chunks = chunk_document(doc_id, files[doc_id].read_text(encoding="utf-8"))
            self.doc_chunks[doc_id] = chunks
            fresh.extend(chunks)

        all_chunks = [c for d in sorted(self.doc_chunks) for c in self.doc_chunks[d]]
        self.bm25.build(all_chunks)

        n_changed = len(report.added) + len(report.modified) + len(report.deleted)
        need_refit = force_refit or not self.vector._fitted or n_changed / max(len(new_hashes), 1) > self.refit_ratio
        if need_refit:
            self.vector.build(all_chunks, refit=True)
        else:
            self.vector.remove_docs(stale)
            self.vector.add(fresh)
        report.vector_refit = need_refit

        self.manifest = new_hashes
        return report

    # ------------------------------------------------------------------ 检索
    def search(self, query: str, top_k: int = 5, mode: str = "hybrid_rerank",
               recall_k: int = 20) -> list[tuple[Chunk, float]]:
        """mode: bm25 | vector | hybrid | hybrid_rerank"""
        if mode == "bm25":
            return self.bm25.search(query, top_k)
        if mode == "vector":
            return self.vector.search(query, top_k)
        fused = rrf_fuse([self.bm25.search(query, recall_k), self.vector.search(query, recall_k)],
                         k=self.rrf_k, top_k=recall_k)
        if mode == "hybrid":
            return fused[:top_k]
        if mode == "hybrid_rerank":
            return self.reranker.rerank(query, fused, top_k)
        raise ValueError(f"unknown mode: {mode}")

    def search_docs(self, query: str, top_k: int = 5, **kw) -> list[str]:
        """块级结果按出现顺序去重为文档级结果。"""
        out: list[str] = []
        for chunk, _ in self.search(query, top_k=top_k * 3, **kw):
            if chunk.doc_id not in out:
                out.append(chunk.doc_id)
        return out[:top_k]

    # ------------------------------------------------------------------ 持久化
    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        Path(path).with_suffix(".manifest.json").write_text(json.dumps(self.manifest, indent=2), encoding="utf-8")

    @staticmethod
    def load(path: str | Path) -> HybridIndex:
        with open(path, "rb") as f:
            return pickle.load(f)
