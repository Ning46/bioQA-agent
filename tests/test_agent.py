from pathlib import Path

import pytest

from bioqa.agent import Agent, ConversationMemory
from bioqa.llm import LLMResponse, RuleBasedLLM, ToolCall
from bioqa.llm.anthropic_llm import AnthropicLLM
from bioqa.retrieval import HybridIndex
from bioqa.tools import default_tools

KB = Path(__file__).resolve().parents[1] / "data" / "kb"


@pytest.fixture(scope="module")
def tools():
    idx = HybridIndex(KB)
    idx.build()
    return default_tools(idx)


def test_memory_resolves_by_entity_type():
    m = ConversationMemory()
    m.remember("gene", "EGFR")
    m.remember("sequence", "ATGC")
    assert m.resolve("这个基因有什么药")[0] == "EGFR有什么药"
    assert m.resolve("这条序列的GC含量")[0] == "ATGC的GC含量"
    assert m.resolve("它的长度")[0] == "ATGC的长度"  # "它"取最近的实体


def test_memory_without_entities_is_noop():
    assert ConversationMemory().resolve("它是什么")[0] == "它是什么"


def test_window_keeps_tool_pairs():
    m = ConversationMemory(max_turns=2)
    for i in range(4):
        m.add({"role": "user", "content": f"q{i}"})
        m.add({"role": "assistant", "content": "", "tool_calls": [ToolCall(f"c{i}", "t", {})]})
        m.add({"role": "tool", "tool_call_id": f"c{i}", "name": "t", "content": "{}", "is_error": False})
    w = m.window()
    assert w[0]["content"] == "q2" and len(w) == 6


def test_self_correction_loop(tools):
    agent = Agent(RuleBasedLLM(), tools)
    res = agent.run("EGRF的靶向药有哪些")
    assert [s.is_error for s in res.tool_calls] == [True, False]
    assert "奥希替尼" in res.answer


class _AlwaysBadLLM:
    """一直传错参数的模型，用来测试错误上限和步数上限。"""

    def chat(self, system, messages, tools):
        return LLMResponse(tool_calls=[ToolCall("x", "sequence_analysis", {"sequence": "ATGC"})])


def test_error_budget_and_step_limit(tools):
    agent = Agent(_AlwaysBadLLM(), tools, max_steps=5, max_tool_errors=2)
    res = agent.run("随便")
    assert len(res.tool_calls) == 5 and all(s.is_error for s in res.tool_calls)
    assert "已连续失败" in res.tool_calls[-1].output
    assert "最大推理步数" in res.answer


def test_unknown_tool_is_reported(tools):
    class LLM:
        def __init__(self):
            self.n = 0

        def chat(self, system, messages, tools):
            self.n += 1
            if self.n == 1:
                return LLMResponse(tool_calls=[ToolCall("1", "pubmed_search", {})])
            return LLMResponse(text=messages[-1]["content"])

    res = Agent(LLM(), tools).run("q")
    assert "不存在名为" in res.answer


def test_anthropic_message_conversion():
    msgs = [
        {"role": "user", "content": "它的药", "resolved": "EGFR的药"},
        {"role": "assistant", "content": "", "tool_calls": [ToolCall("a", "gene_lookup", {"gene": "EGFR"}),
                                                             ToolCall("b", "gene_lookup", {"gene": "TP53"})]},
        {"role": "tool", "tool_call_id": "a", "name": "gene_lookup", "content": "{}", "is_error": False},
        {"role": "tool", "tool_call_id": "b", "name": "gene_lookup", "content": "err", "is_error": True},
    ]
    api = AnthropicLLM.to_api_messages(msgs)
    assert "EGFR的药" in api[0]["content"]
    assert [b["type"] for b in api[1]["content"]] == ["tool_use", "tool_use"]
    assert len(api) == 3 and [b["tool_use_id"] for b in api[2]["content"]] == ["a", "b"]
    assert api[2]["content"][1]["is_error"] is True
