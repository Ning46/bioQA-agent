"""离线规则模型。

不调用任何 API，用确定性规则模拟一个会做 function calling 的模型，
用来在没有 API key 的情况下跑通并测试 Agent 全链路（工具选择、参数校验、错误自我修正、多轮记忆）。
它的回答只是把工具结果组织成文字，语言能力远不如真实大模型；接入 Claude 见 anthropic_llm.py。
"""
from __future__ import annotations

import itertools
import re

from ..retrieval.text import tokenize
from .base import LLMResponse, ToolCall

_SEQ_CANDIDATE = re.compile(r"[A-Za-z0-9>\-_|\s]{8,}")
_GENE_TOKEN = re.compile(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9-]{1,9})(?![A-Za-z0-9])")
_GENE_INTENT = re.compile(r"靶向|药|抑制剂|功能|作用|别名|全名|哪个基因|什么基因|这个基因|基因.*(是什么|干嘛)")
_SEQ_OPS = [
    (re.compile(r"反向互补|reverse", re.I), "reverse_complement"),
    (re.compile(r"orf|阅读框", re.I), "find_orfs"),
    (re.compile(r"翻译|蛋白|氨基酸|translate", re.I), "translate"),
    (re.compile(r"转录|rna|transcribe", re.I), "transcribe"),
    (re.compile(r"gc", re.I), "gc_content"),
]
_NOT_GENES = {"DNA", "RNA", "PCR", "SNP", "GWAS", "BLAST", "ORF", "GC", "VCF", "TPM", "FPKM", "CRISPR", "QQ", "ATG"}


def _looks_like_sequence(s: str) -> bool:
    letters = re.sub(r"[\s]", "", s)
    if len(letters) < 8:
        return False
    nuc = sum(c in "ACGTUNacgtun" for c in letters)
    return nuc / len(letters) >= 0.8


class RuleBasedLLM:
    def __init__(self):
        self._ids = itertools.count(1)

    # ------------------------------------------------------------------ 入口
    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        tool_names = {t["name"] for t in tools}
        last_user = max(i for i, m in enumerate(messages) if m["role"] == "user")
        user = messages[last_user]
        query = user.get("resolved") or user["content"]
        turn = messages[last_user + 1:]
        results = [m for m in turn if m["role"] == "tool"]

        if not results:
            return self._plan(query, tool_names)
        last = results[-1]
        if last["is_error"]:
            return self._correct(query, turn, last)
        return LLMResponse(text=self._answer(query, results))

    def _call(self, name: str, args: dict) -> LLMResponse:
        return LLMResponse(tool_calls=[ToolCall(f"call_{next(self._ids)}", name, args)])

    # ------------------------------------------------------------------ 规划：选工具、填参数
    def _plan(self, query: str, tool_names: set[str]) -> LLMResponse:
        seq = self._extract_sequence(query)
        if seq and "sequence_analysis" in tool_names:
            op = next((op for pat, op in _SEQ_OPS if pat.search(query)), "stats")
            return self._call("sequence_analysis", {"sequence": seq, "operation": op})

        gene = self._extract_gene(query)
        if gene and _GENE_INTENT.search(query) and "gene_lookup" in tool_names:
            return self._call("gene_lookup", {"gene": gene})

        return self._call("knowledge_search", {"query": query})

    @staticmethod
    def _extract_sequence(text: str) -> str | None:
        cands = [c.strip() for c in _SEQ_CANDIDATE.findall(text)]
        # 模型"看到"的是一段像序列的文本，可能夹带 FASTA 标题、数字等杂质，原样传入，交给参数校验把关
        cands = [c for c in cands
                 if _looks_like_sequence(c) or (len(c) > 20 and _looks_like_sequence(c[c.find(" ") + 1:]))]
        return max(cands, key=len) if cands else None

    @staticmethod
    def _extract_gene(text: str) -> str | None:
        for tok in _GENE_TOKEN.findall(text):
            if tok.upper() in _NOT_GENES:
                continue
            # 基因符号通常含大写字母+数字，或全大写
            if (tok.isupper() and len(tok) >= 3) or re.search(r"[A-Za-z]\d", tok):
                return tok
        return None

    # ------------------------------------------------------------------ 错误自我修正
    def _correct(self, query: str, turn: list[dict], err: dict) -> LLMResponse:
        name = err["name"]
        attempts = sum(1 for m in turn if m["role"] == "tool" and m["name"] == name and m["is_error"])
        prev_args = next(c.input for m in reversed(turn) if m["role"] == "assistant"
                         for c in m.get("tool_calls", []) if c.id == err["tool_call_id"])
        msg = err["content"]

        if attempts <= 2:
            if name == "gene_lookup" and (m := re.search(r"你是不是想查：([A-Za-z0-9-]+)", msg)):
                return self._call(name, {**prev_args, "gene": m.group(1)})
            if name == "sequence_analysis" and "格式不正确" in msg:
                seq = prev_args["sequence"]
                seq = re.sub(r">\S*", "", seq)  # 去掉 FASTA 标题（可能和序列在同一行）
                cleaned = re.sub(r"[^ACGTUNacgtun]", "", seq)
                if cleaned and cleaned != seq:
                    return self._call(name, {**prev_args, "sequence": cleaned})
            if name == "sequence_analysis" and "不在允许值中" in msg:
                return self._call(name, {**prev_args, "operation": "stats"})
            if name == "knowledge_search" and "没有找到" in msg:
                kws = " ".join(t for t in tokenize(query) if len(t) > 1)
                if kws and kws != prev_args.get("query"):
                    return self._call(name, {"query": kws})
        return LLMResponse(text=f"抱歉，工具调用多次失败，无法完成这个请求。最后的错误信息：\n{msg}")

    # ------------------------------------------------------------------ 组织回答
    def _answer(self, query: str, results: list[dict]) -> str:
        import json
        last = results[-1]
        data = json.loads(last["content"])
        if last["name"] == "knowledge_search":
            return self._answer_knowledge(query, data["results"])
        if last["name"] == "gene_lookup":
            lines = [f"**{data['symbol']}**（{data['name']}）", f"功能：{data['function']}"]
            if data.get("aliases"):
                lines.append(f"别名：{', '.join(data['aliases'])}")
            if "drugs" in data:
                if data["drugs"]:
                    lines.append("相关靶向药：")
                    lines += [f"- {d['name']}：{d['mechanism']}（{'已获批' if d['status'] == 'approved' else '在研'}）"
                              for d in data["drugs"]]
                else:
                    lines.append(data.get("note", "暂无靶向药记录"))
            return "\n".join(lines)
        if last["name"] == "sequence_analysis":
            return "序列分析结果：\n" + "\n".join(f"- {k}: {v}" for k, v in data.items())
        return json.dumps(data, ensure_ascii=False)

    @staticmethod
    def _answer_knowledge(query: str, hits: list[dict]) -> str:
        top = hits[0]
        # 句子排序时去掉主题本身的词，让"局限""阈值"这类真正的问点主导
        q = set(tokenize(query)) - set(tokenize(top["title"])) or set(tokenize(query))
        body = top["text"].split("\n", 1)[-1]
        sents = [s for s in re.split(r"(?<=[。！？])", body.replace("\n", "")) if s.strip()]
        ranked = sorted(sents, key=lambda s: -len(q & set(tokenize(s))))
        keep = [s for s in sents if s in ranked[:2]]  # 保持原文顺序
        refs = "、".join(dict.fromkeys(h["title"] for h in hits))
        return "".join(keep).strip() + f"\n\n参考：{refs}"
