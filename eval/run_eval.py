"""运行全部评测并做基线回归检查。

    python -m eval.run_eval                 # 消融 + 端到端 + 与基线对比，回退则以非零码退出
    python -m eval.run_eval --update-baseline
    python -m eval.run_eval --llm claude    # 端到端用例改用真实 Claude（需要 ANTHROPIC_API_KEY）
"""
from __future__ import annotations

import argparse
import json
import sys

from .metrics import EVAL, MODES, _build_index, run_ablation, run_e2e

BASELINE = EVAL / "baseline.json"
RESULTS = EVAL / "results"
TOLERANCE = 0.0  # 允许的指标下降幅度；评测是确定性的，任何下降都算回退


def summarize(ablation: dict, e2e: dict) -> dict:
    s = {f"{qs}/{mode}/{m}": ablation[qs][mode][m]
         for qs in ablation for mode in MODES for m in ("hit@1", "hit@3", "mrr")}
    s["e2e/pass_rate"] = e2e["pass_rate"]
    return s


def render(ablation: dict, e2e: dict) -> str:
    names = {"bm25": "BM25", "vector": "向量", "hybrid": "BM25+向量 (RRF)", "hybrid_rerank": "RRF + 重排"}
    lines = []
    for qs, title in (("dev", "开发集（调参用）"), ("heldout", "留出集（冻结后评测）")):
        lines += [f"\n### 检索消融 · {title}，20 条口语化查询\n", "| 方法 | Hit@1 | Hit@3 | MRR |", "|---|---|---|---|"]
        for mode in MODES:
            r = ablation[qs][mode]
            lines.append(f"| {names[mode]} | {r['hit@1']:.0%} | {r['hit@3']:.0%} | {r['mrr']:.3f} |")
    lines += [f"\n### 端到端用例：{e2e['passed']}/{e2e['total']} 通过\n"]
    for c in e2e["cases"]:
        lines.append(f"- {'✅' if c['passed'] else '❌'} `{c['id']}` {c['desc']}" +
                     "".join(f"\n  - {f}" for f in c["failures"]))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--llm", default="rule", choices=["rule", "claude"])
    args = ap.parse_args()

    index = _build_index()
    ablation, e2e = run_ablation(index), run_e2e(args.llm, index)
    summary = summarize(ablation, e2e)

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "ablation.json").write_text(json.dumps(ablation, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "e2e.json").write_text(json.dumps(e2e, ensure_ascii=False, indent=2), encoding="utf-8")
    report = render(ablation, e2e)
    (RESULTS / "report.md").write_text(report + "\n", encoding="utf-8")
    print(report)

    if args.update_baseline:
        BASELINE.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\n基线已更新：{BASELINE.name}")
        return 0
    if args.llm != "rule":
        return 0  # 真实模型有随机性，不与离线基线比较
    if not BASELINE.exists():
        print("\n尚无基线，使用 --update-baseline 生成。")
        return 0

    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    regressions = [(k, base[k], summary.get(k)) for k in base if summary.get(k, -1) < base[k] - TOLERANCE]
    if regressions:
        print("\n❌ 基线回归检查失败：")
        for k, old, new in regressions:
            print(f"  {k}: {old} -> {new}")
        return 1
    print("\n✅ 基线回归检查通过（所有指标不低于基线）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
