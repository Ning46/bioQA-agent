"""多轮对话记忆与指代消解。

- 消息历史按"轮"保存，窗口裁剪只在用户消息边界切，保证 tool_use / tool_result 成对出现。
- 实体栈记录最近提到的基因、序列和知识主题（来自工具调用参数和结果），
  新问题中的"它 / 这个基因 / 这条序列 / 这个方法"等指代词被替换成对应实体。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# (指代模式, 需要的实体类型；None 表示取最近的任意实体)
_PATTERNS: list[tuple[re.Pattern, str | None]] = [
    (re.compile(r"(这个|该|那个|上面的?|刚才的?)(基因|靶点|蛋白)"), "gene"),
    (re.compile(r"(这条|这段|该|那条|那段|上面的?|刚才的?)序列"), "sequence"),
    (re.compile(r"(这个|该|那个|上面的?|刚才的?)(方法|技术|概念|算法|工具|格式|分析)"), "topic"),
    (re.compile(r"(?<![其])它们?|(?<![a-z])(it|this one)(?![a-z])", re.I), None),
]


@dataclass
class Entity:
    kind: str     # gene | sequence | topic
    value: str
    label: str    # 用于替换进文本的表述


@dataclass
class ConversationMemory:
    max_turns: int = 8
    messages: list[dict] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)

    # ------------------------------------------------------------------ 历史
    def add(self, message: dict) -> None:
        self.messages.append(message)

    def window(self) -> list[dict]:
        starts = [i for i, m in enumerate(self.messages) if m["role"] == "user"]
        if len(starts) <= self.max_turns:
            return list(self.messages)
        return self.messages[starts[-self.max_turns]:]

    def clear(self) -> None:
        self.messages.clear()
        self.entities.clear()

    # ------------------------------------------------------------------ 实体
    def remember(self, kind: str, value: str, label: str | None = None) -> None:
        self.entities = [e for e in self.entities if not (e.kind == kind and e.value == value)]
        self.entities.append(Entity(kind, value, label or value))

    def last(self, kind: str | None = None) -> Entity | None:
        for e in reversed(self.entities):
            if kind is None or e.kind == kind:
                return e
        return None

    def observe_tool(self, name: str, args: dict, result: str, is_error: bool) -> None:
        """从一次成功的工具调用中抽取实体。"""
        if is_error:
            return
        data = json.loads(result)
        if name == "gene_lookup":
            self.remember("gene", data["symbol"])
        elif name == "sequence_analysis":
            seq = re.sub(r"\s", "", args["sequence"]).upper()
            self.remember("sequence", seq, seq)
        elif name == "knowledge_search" and data.get("results"):
            title = data["results"][0]["title"]
            self.remember("topic", title, f"「{title}」")

    # ------------------------------------------------------------------ 指代消解
    def resolve(self, text: str) -> tuple[str, list[tuple[str, str]]]:
        """返回 (消解后的文本, [(原指代词, 替换为)])。没有可用实体时原样返回。"""
        subs: list[tuple[str, str]] = []
        out = text
        for pat, kind in _PATTERNS:
            ent = self.last(kind)
            if ent is None:
                continue

            def repl(m: re.Match, ent=ent) -> str:
                subs.append((m.group(0), ent.label))
                return ent.label

            out = pat.sub(repl, out)
        return out, subs
