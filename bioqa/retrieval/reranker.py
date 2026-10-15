"""重排器。

召回阶段（BM25 + 向量 + RRF）追求"找得全"，重排阶段对少量候选做更细的 (query, doc) 成对打分，
追求"排得准"。提供两种实现：

- FeatureReranker（默认，离线）：类 cross-encoder 的成对特征打分，
  特征包括领域概念匹配（口语说法 -> 规范术语）、查询词覆盖率、标题匹配和召回阶段先验。
- LLMReranker（可选）：让大模型对候选做列表式重排，需要 ANTHROPIC_API_KEY。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol

from .text import Chunk, tokenize

DEFAULT_GLOSSARY = Path(__file__).resolve().parents[2] / "data" / "glossary.json"


class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[tuple[Chunk, float]], top_k: int) -> list[tuple[Chunk, float]]: ...


def load_glossary(path: Path = DEFAULT_GLOSSARY) -> dict[str, list[str]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: [a.lower() for a in v] for k, v in data.items() if not k.startswith("_")}


def _contains(text: str, alias: str) -> bool:
    # 纯英文短别名按词边界匹配，避免 "go" 命中 "algorithm" 之类的误报
    if re.fullmatch(r"[a-z0-9]{1,4}", alias):
        return re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text) is not None
    return alias in text


class FeatureReranker:
    def __init__(self, glossary: dict[str, list[str]] | None = None,
                 w_concept: float = 0.45, w_cover: float = 0.25, w_title: float = 0.15, w_prior: float = 0.15):
        self.glossary = glossary if glossary is not None else load_glossary()
        self.w = (w_concept, w_cover, w_title, w_prior)

    def concepts(self, text: str) -> dict[str, int]:
        """返回文本触发的概念及命中的别名数。"""
        low = text.lower()
        hits = {}
        for concept, aliases in self.glossary.items():
            n = sum(_contains(low, a) for a in aliases)
            if n:
                hits[concept] = n
        return hits

    def score(self, query: str, chunk: Chunk, prior: float) -> float:
        q_concepts = self.concepts(query)
        if q_concepts:
            d_concepts = self.concepts(chunk.text)
            d_mass = sum(d_concepts.values()) or 1
            total = sum(q_concepts.values())
            # 概念"主导度"：该概念在文档全部概念命中中的占比。
            # 只顺带提到某概念的文档（如单细胞文档提到"转录组"）得分低于以它为主题的文档。
            # 开平方做阻尼：主导度 0 和 0.3 之间的差异比 0.7 和 1.0 之间更重要，
            # 否则覆盖面广的长文档会因为分母大而被过度惩罚。
            concept = sum(n * (d_concepts.get(c, 0) / d_mass) ** 0.5 for c, n in q_concepts.items()) / total
        else:
            concept = 0.0

        q_tok = set(tokenize(query))
        d_tok = set(chunk.tokens)
        title_tok = set(tokenize(chunk.title))
        cover = len(q_tok & d_tok) / len(q_tok) if q_tok else 0.0
        title = len(q_tok & title_tok) / len(q_tok) if q_tok else 0.0

        wc, wv, wt, wp = self.w
        return wc * concept + wv * cover + wt * title + wp * prior

    def rerank(self, query: str, candidates: list[tuple[Chunk, float]], top_k: int = 5) -> list[tuple[Chunk, float]]:
        n = len(candidates)
        scored = []
        for rank, (chunk, _) in enumerate(candidates):
            prior = 1.0 - rank / n if n else 0.0  # 召回排名作为先验，0~1
            scored.append((chunk, self.score(query, chunk, prior)))
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]


class LLMReranker:
    """用 Claude 做列表式重排。只在设置了 ANTHROPIC_API_KEY 时使用。"""

    def __init__(self, model: str = "claude-haiku-5-5", client=None):
        import anthropic  # 延迟导入，离线环境不需要
        self.client = client or anthropic.Anthropic()
        self.model = model

    def rerank(self, query: str, candidates: list[tuple[Chunk, float]], top_k: int = 5) -> list[tuple[Chunk, float]]:
        listing = "\n\n".join(f"[{i}] {c.title}\n{c.text[:300]}" for i, (c, _) in enumerate(candidates))
        prompt = (f"问题：{query}\n\n候选段落：\n{listing}\n\n"
                  "按与问题的相关度从高到低输出候选编号，只输出 JSON 数组，例如 [3,0,5]。")
        resp = self.client.messages.create(model=self.model, max_tokens=200,
                                           messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        try:
            order = [int(i) for i in json.loads(re.search(r"\[.*?\]", text, re.S).group(0))]
        except Exception:
            return candidates[:top_k]
        seen, out = set(), []
        for i in order + list(range(len(candidates))):
            if 0 <= i < len(candidates) and i not in seen:
                seen.add(i)
                out.append((candidates[i][0], 1.0 / (1 + len(out))))
        return out[:top_k]
