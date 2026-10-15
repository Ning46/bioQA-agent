"""工具定义与参数校验。

每个工具用 JSON Schema 描述参数，Agent 在执行前先校验。校验失败或执行出错时抛出 ToolError，
错误信息会作为 tool_result(is_error=True) 回传给模型，让模型据此修正参数再调用（错误自我修正）。
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class ToolError(Exception):
    """可回传给模型的工具错误。hint 字段给出修正建议。"""

    def __init__(self, message: str, hint: str | None = None):
        super().__init__(message)
        self.hint = hint

    def to_text(self) -> str:
        return f"错误：{self}" + (f"\n建议：{self.hint}" if self.hint else "")


_TYPES = {
    "string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict,
}


def validate(args: Any, schema: dict, path: str = "") -> dict:
    """轻量 JSON Schema 校验（type/required/enum/pattern/min/max/additionalProperties）。
    返回填入默认值后的参数；校验失败抛 ToolError。"""
    if not isinstance(args, dict):
        raise ToolError("参数必须是 JSON 对象", "请按工具的 input_schema 传入键值对")
    props = schema.get("properties", {})
    out = dict(args)

    for name in schema.get("required", []):
        if name not in out or out[name] in (None, ""):
            raise ToolError(f"缺少必填参数 '{path}{name}'", f"'{name}': {props.get(name, {}).get('description', '')}")

    if schema.get("additionalProperties") is False:
        extra = set(out) - set(props)
        if extra:
            raise ToolError(f"未知参数 {sorted(extra)}", f"可用参数：{sorted(props)}")

    for name, spec in props.items():
        if name not in out:
            if "default" in spec:
                out[name] = spec["default"]
            continue
        v = out[name]
        typ = spec.get("type")
        if typ == "integer" and isinstance(v, str) and v.strip().lstrip("-").isdigit():
            v = out[name] = int(v)  # 宽容处理模型常见的"数字写成字符串"
        if typ and (not isinstance(v, _TYPES[typ]) or (typ in ("integer", "number") and isinstance(v, bool))):
            raise ToolError(f"参数 '{name}' 应为 {typ}，实际为 {type(v).__name__}")
        if "enum" in spec and v not in spec["enum"]:
            raise ToolError(f"参数 '{name}'={v!r} 不在允许值中", f"可选值：{spec['enum']}")
        if "pattern" in spec and not re.fullmatch(spec["pattern"], v):
            raise ToolError(f"参数 '{name}' 格式不正确", spec.get("pattern_hint"))
        if "minimum" in spec and v < spec["minimum"]:
            raise ToolError(f"参数 '{name}' 不能小于 {spec['minimum']}")
        if "maximum" in spec and v > spec["maximum"]:
            raise ToolError(f"参数 '{name}' 不能大于 {spec['maximum']}")
    return out


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    fn: Callable[..., Any]

    def __call__(self, args: dict) -> Any:
        clean = validate(args, self.input_schema)
        return self.fn(**clean)

    def spec(self) -> dict:
        """Anthropic / OpenAI function calling 通用的工具描述。"""
        schema = {k: v for k, v in self.input_schema.items()}
        schema["properties"] = {k: {kk: vv for kk, vv in p.items() if kk != "pattern_hint"}
                                for k, p in schema.get("properties", {}).items()}
        return {"name": self.name, "description": self.description, "input_schema": schema}
