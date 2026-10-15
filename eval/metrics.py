"""检索消融与端到端评测的公共逻辑，供命令行脚本和回归检查复用。"""
from __future__ import annotations

import json
from pathlib import Path

from bioqa.agent import Agent
from bioqa.llm import get_llm
from bioqa.retrieval import HybridIndex
from bioqa.tools import default_tools

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
KB = ROOT / "data" / "kb"
MODES = ["bm25", "vector", "hybrid", "hybrid_rerank"]
QUERY_SETS = {"dev": EVAL / "hard_queries.jsonl", "heldout": EVAL / "heldout_queries.jsonl"}


def load_queries(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def retrieval_metrics(index: HybridIndex, queries: list[dict], mode: str, k: int = 3) -> dict:
    hit1 = hitk = rr = 0.0
    misses = []
    for q in queries:
        docs = index.search_docs(q["query"], top_k=10, mode=mode)
        rank = docs.index(q["gold"]) + 1 if q["gold"] in docs else None
        hit1 += rank == 1
        hitk += rank is not None and rank <= k
        rr += 1 / rank if rank else 0
        if rank != 1:
            misses.append({"id": q["id"], "gold": q["gold"], "rank": rank, "top1": docs[0] if docs else None})
    n = len(queries)
    return {"hit@1": round(hit1 / n, 4), f"hit@{k}": round(hitk / n, 4), "mrr": round(rr / n, 4), "misses": misses}


def run_ablation(index: HybridIndex | None = None) -> dict:
    index = index or _build_index()
    return {name: {mode: retrieval_metrics(index, load_queries(path), mode) for mode in MODES}
            for name, path in QUERY_SETS.items()}


def run_e2e(llm_name: str = "rule", index: HybridIndex | None = None) -> dict:
    index = index or _build_index()
    cases = json.loads((EVAL / "e2e_cases.json").read_text(encoding="utf-8"))
    report = []
    for case in cases:
        agent = Agent(get_llm(llm_name), default_tools(index))
        failures = []
        for i, turn in enumerate(case["turns"], 1):
            res = agent.run(turn["user"])
            called = [s.name for s in res.tool_calls]
            if "tools" in turn and called != turn["tools"]:
                failures.append(f"第{i}轮工具序列 {called} ≠ 期望 {turn['tools']}")
            if "n_errors" in turn and res.n_errors < turn["n_errors"]:
                failures.append(f"第{i}轮期望至少 {turn['n_errors']} 次工具报错，实际 {res.n_errors}")
            if "resolved_contains" in turn and turn["resolved_contains"] not in res.resolved_query:
                failures.append(f"第{i}轮指代消解结果 '{res.resolved_query}' 不含 '{turn['resolved_contains']}'")
            for kw in turn.get("answer_contains", []):
                if kw not in res.answer:
                    failures.append(f"第{i}轮回答缺少 '{kw}'")
        report.append({"id": case["id"], "desc": case["desc"], "passed": not failures, "failures": failures})
    passed = sum(r["passed"] for r in report)
    return {"pass_rate": round(passed / len(report), 4), "passed": passed, "total": len(report), "cases": report}


def _build_index() -> HybridIndex:
    idx = HybridIndex(KB)
    idx.build()
    return idx
