"""模型接口。

Agent 内部使用一种中立的消息格式，由各个适配器转换成具体厂商的 API 格式：
    {"role": "user", "content": str, "resolved": str}           # resolved 为指代消解后的文本
    {"role": "assistant", "content": str, "tool_calls": [ToolCall]}
    {"role": "tool", "tool_call_id": str, "name": str, "content": str, "is_error": bool}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLM(Protocol):
    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse: ...
