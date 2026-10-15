"""Agent 主循环（function calling）。

    用户输入 → 指代消解 → [模型决策 → 参数校验 → 执行工具 → 结果/错误回传] × N → 最终回答

- 每轮最多 max_steps 次模型调用，防止死循环；
- 参数校验和执行错误都以 tool_result(is_error=True) 回传，由模型自行修正后重试；
- 同一工具连续出错超过 max_tool_errors 次后不再执行，直接要求模型给出回答。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from ..llm import LLM
from ..tools import Tool, ToolError
from .memory import ConversationMemory

SYSTEM_PROMPT = """你是一个生物信息学问答助手。
- 概念、方法、原理类问题，先调用 knowledge_search 检索知识库，基于检索结果回答，并注明参考的文档标题；
- 涉及具体 DNA/RNA 序列的计算，调用 sequence_analysis，不要自己心算；
- 查询基因功能和靶向药，调用 gene_lookup；
- 工具返回错误时，阅读错误信息和建议，修正参数后重试；
- 知识库和工具都没有依据时，明确说不知道，不要编造。"""


@dataclass
class Step:
    kind: str            # model | tool
    name: str = ""
    input: dict | None = None
    output: str = ""
    is_error: bool = False
    ms: float = 0.0


@dataclass
class AgentResult:
    answer: str
    resolved_query: str
    substitutions: list[tuple[str, str]]
    steps: list[Step] = field(default_factory=list)

    @property
    def tool_calls(self) -> list[Step]:
        return [s for s in self.steps if s.kind == "tool"]

    @property
    def n_errors(self) -> int:
        return sum(s.is_error for s in self.tool_calls)


class Agent:
    def __init__(self, llm: LLM, tools: list[Tool], memory: ConversationMemory | None = None,
                 system: str = SYSTEM_PROMPT, max_steps: int = 6, max_tool_errors: int = 3):
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.memory = memory or ConversationMemory()
        self.system = system
        self.max_steps = max_steps
        self.max_tool_errors = max_tool_errors

    def _execute(self, name: str, args: dict) -> tuple[str, bool]:
        tool = self.tools.get(name)
        if tool is None:
            return ToolError(f"不存在名为 '{name}' 的工具", f"可用工具：{sorted(self.tools)}").to_text(), True
        try:
            return json.dumps(tool(args), ensure_ascii=False), False
        except ToolError as e:
            return e.to_text(), True
        except Exception as e:  # 工具内部的意外错误也回传给模型，而不是让整个 Agent 崩溃
            return f"错误：工具执行异常 {type(e).__name__}: {e}", True

    def run(self, user_input: str) -> AgentResult:
        resolved, subs = self.memory.resolve(user_input)
        self.memory.add({"role": "user", "content": user_input, "resolved": resolved})
        result = AgentResult(answer="", resolved_query=resolved, substitutions=subs)
        specs = [t.spec() for t in self.tools.values()]
        errors: dict[str, int] = {}

        for _ in range(self.max_steps):
            t0 = time.perf_counter()
            resp = self.llm.chat(self.system, self.memory.window(), specs)
            result.steps.append(Step("model", output=resp.text, ms=(time.perf_counter() - t0) * 1000))
            self.memory.add({"role": "assistant", "content": resp.text, "tool_calls": resp.tool_calls})

            if not resp.tool_calls:
                result.answer = resp.text
                return result

            for call in resp.tool_calls:
                t0 = time.perf_counter()
                if errors.get(call.name, 0) >= self.max_tool_errors:
                    out = f"错误：工具 {call.name} 已连续失败 {self.max_tool_errors} 次，停止调用，请直接回答用户"
                    is_err = True
                else:
                    out, is_err = self._execute(call.name, call.input)
                errors[call.name] = errors.get(call.name, 0) + 1 if is_err else 0
                result.steps.append(Step("tool", call.name, call.input, out, is_err, (time.perf_counter() - t0) * 1000))
                self.memory.add({"role": "tool", "tool_call_id": call.id, "name": call.name,
                                 "content": out, "is_error": is_err})
                self.memory.observe_tool(call.name, call.input, out, is_err)

        result.answer = "抱歉，达到最大推理步数仍未得到答案。"
        self.memory.add({"role": "assistant", "content": result.answer, "tool_calls": []})
        return result
