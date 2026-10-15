"""把评测接入 pytest：端到端用例全部通过，且检索指标不低于基线。"""
import json

from eval.metrics import EVAL, run_ablation, run_e2e
from eval.run_eval import summarize


def test_e2e_and_baseline():
    ablation, e2e = run_ablation(), run_e2e("rule")
    failed = [c for c in e2e["cases"] if not c["passed"]]
    assert not failed, failed
    base = json.loads((EVAL / "baseline.json").read_text(encoding="utf-8"))
    now = summarize(ablation, e2e)
    drops = {k: (v, now[k]) for k, v in base.items() if now[k] < v}
    assert not drops, f"指标低于基线: {drops}"
