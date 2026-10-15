import os

from .base import LLM, LLMResponse, ToolCall
from .rule_based import RuleBasedLLM


def get_llm(name: str | None = None) -> LLM:
    """name: 'rule' | 'claude'。默认有 ANTHROPIC_API_KEY 时用 Claude，否则用离线规则模型。"""
    name = name or ("claude" if os.environ.get("ANTHROPIC_API_KEY") else "rule")
    if name == "claude":
        from .anthropic_llm import AnthropicLLM
        return AnthropicLLM()
    return RuleBasedLLM()


__all__ = ["LLM", "LLMResponse", "ToolCall", "RuleBasedLLM", "get_llm"]
