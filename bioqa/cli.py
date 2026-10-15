"""命令行入口：python -m bioqa [--llm rule|claude] [--trace]"""
from __future__ import annotations

import argparse

from .agent import build_agent


def main() -> None:
    ap = argparse.ArgumentParser(description="BioQA Agent 交互式问答")
    ap.add_argument("--llm", choices=["rule", "claude"], default=None,
                    help="默认：有 ANTHROPIC_API_KEY 用 claude，否则 rule")
    ap.add_argument("--trace", action="store_true", help="打印每一步工具调用")
    args = ap.parse_args()

    agent = build_agent(args.llm)
    print(f"BioQA Agent 已启动（模型：{type(agent.llm).__name__}）。输入问题，/reset 清空记忆，/quit 退出。")
    while True:
        try:
            q = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q == "/quit":
            break
        if q == "/reset":
            agent.memory.clear()
            print("记忆已清空。")
            continue
        res = agent.run(q)
        if args.trace:
            if res.substitutions:
                print(f"  [指代消解] {res.resolved_query}")
            for s in res.tool_calls:
                flag = "✗" if s.is_error else "✓"
                print(f"  [{flag} {s.name}] {s.input}" + (f"\n      {s.output}" if s.is_error else ""))
        print(f"\nAgent> {res.answer}")


if __name__ == "__main__":
    main()
