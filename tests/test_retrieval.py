import shutil
from pathlib import Path

import pytest

from bioqa.retrieval import HybridIndex, tokenize
from bioqa.retrieval.fusion import rrf_fuse
from bioqa.retrieval.text import Chunk

KB = Path(__file__).resolve().parents[1] / "data" / "kb"


@pytest.fixture(scope="module")
def index():
    idx = HybridIndex(KB)
    idx.build()
    return idx


def test_tokenize_mixed():
    toks = tokenize("EGFR 突变的靶向药")
    assert "egfr" in toks and "突变" in toks and "靶向" in toks
    assert "的" not in toks


def test_rrf_rewards_agreement():
    a, b, c = (Chunk(x, x, x, x) for x in "abc")
    fused = rrf_fuse([[(a, 9), (b, 5)], [(b, 0.9), (c, 0.8)]])
    assert fused[0][0].chunk_id == "b"  # 两路都召回的文档排第一


@pytest.mark.parametrize("mode", ["bm25", "vector", "hybrid", "hybrid_rerank"])
def test_exact_term_queries(index, mode):
    assert index.search_docs("CRISPR-Cas9 基因编辑 PAM", mode=mode)[0] == "crispr"


def test_rerank_beats_hybrid_on_colloquial(index):
    q = "处理组和对照组比，哪些基因上调了，用什么包算"
    assert index.search_docs(q, mode="hybrid")[0] != "rna_seq"
    assert index.search_docs(q, mode="hybrid_rerank")[0] == "rna_seq"


def test_incremental_update(tmp_path):
    kb = tmp_path / "kb"
    shutil.copytree(KB, kb)
    idx = HybridIndex(kb, refit_ratio=0.5)
    first = idx.build()
    assert len(first.added) == len(list(kb.glob("*.md")))

    assert not idx.update().changed  # 无变化：什么都不做

    (kb / "new_topic.md").write_text(
        "# 宏基因组测序\n宏基因组学直接对环境样本中的全部微生物 DNA 测序，用 Kraken2 做物种分类。", encoding="utf-8")
    (kb / "pcr.md").write_text(
        (kb / "pcr.md").read_text(encoding="utf-8") + "\n\n数字 PCR（dPCR）可以绝对定量。", encoding="utf-8")
    (kb / "hmm.md").unlink()

    rep = idx.update()
    assert rep.added == ["new_topic"] and rep.modified == ["pcr"] and rep.deleted == ["hmm"]
    assert not rep.vector_refit  # 变化比例低于阈值：向量侧只做增量折入
    assert idx.search_docs("环境样本微生物 Kraken2 物种分类")[0] == "new_topic"
    assert idx.search_docs("数字PCR 绝对定量")[0] == "pcr"
    assert all(c.doc_id != "hmm" for c in idx.vector.chunks + idx.bm25.chunks)


def test_large_change_triggers_refit(tmp_path):
    kb = tmp_path / "kb"
    shutil.copytree(KB, kb)
    idx = HybridIndex(kb, refit_ratio=0.1)
    idx.build()
    for p in list(kb.glob("*.md"))[:5]:
        p.write_text(p.read_text(encoding="utf-8") + "\n\n补充。", encoding="utf-8")
    assert idx.update().vector_refit


def test_save_load(index, tmp_path):
    p = tmp_path / "idx.pkl"
    index.save(p)
    again = HybridIndex.load(p)
    assert again.search_docs("GWAS 显著性阈值") == index.search_docs("GWAS 显著性阈值")
