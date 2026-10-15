"""Claude 适配器：把中立消息格式转换为 Anthropic Messages API 的 tool use 格式。"""
from __future__ import annotations

import os

from .base import LLMResponse, ToolCall


class AnthropicLLM:
    def __init__(self, model: str | None = None, max_tokens: int = 1024, client=None):
        import anthropic
        self.client = client or anthropic.Anthropic()
        self.model = model or os.environ.get("BIOQA_MODEL", "claude-sonnet-5-5")
        self.max_tokens = max_tokens

    @staticmethod
    def to_api_messages(messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            if m["role"] == "user":
                text = m["content"]
                if m.get("resolved") and m["resolved"] != m["content"]:
                    text += f"\n\n（上下文指代消解：{m['resolved']}）"
                out.append({"role": "user", "content": text})
            elif m["role"] == "assistant":
                blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
                blocks += [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.input}
                           for c in m.get("tool_calls", [])]
                out.append({"role": "assistant", "content": blocks})
            elif m["role"] == "tool":
                block = {"type": "tool_result", "tool_use_id": m["tool_call_id"],
                         "content": m["content"], "is_error": m["is_error"]}
                # 同一轮多个工具结果合并到一条 user 消息里
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
        return out

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        resp = self.client.messages.create(model=self.model, max_tokens=self.max_tokens, system=system,
                                           tools=tools, messages=self.to_api_messages(messages))
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"]
        return LLMResponse(text=text, tool_calls=calls)
