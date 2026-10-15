"""基因 / 靶向药查询工具。"""
from __future__ import annotations

import difflib
import json
from pathlib import Path

from .base import Tool, ToolError

GENES_PATH = Path(__file__).resolve().parents[2] / "data" / "genes.json"


class GeneDB:
    def __init__(self, path: Path = GENES_PATH):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self.genes = {k: v for k, v in raw.items() if not k.startswith("_")}
        self.alias = {}
        for sym, info in self.genes.items():
            self.alias[sym.upper()] = sym
            for a in info.get("aliases", []):
                self.alias[a.upper()] = sym

    def resolve(self, name: str) -> str | None:
        return self.alias.get(name.strip().upper())

    def suggest(self, name: str) -> list[str]:
        cands = difflib.get_close_matches(name.strip().upper(), list(self.alias), n=3, cutoff=0.5)
        return sorted({self.alias[c] for c in cands})

    def lookup(self, gene: str, include_drugs: bool = True) -> dict:
        sym = self.resolve(gene)
        if sym is None:
            sugg = self.suggest(gene)
            raise ToolError(f"未找到基因 '{gene}'",
                            f"你是不是想查：{', '.join(sugg)}" if sugg else "请使用 HGNC 官方基因符号，如 EGFR、TP53")
        info = dict(self.genes[sym])
        out = {"symbol": sym, "name": info["name"], "aliases": info.get("aliases", []), "function": info["function"]}
        if include_drugs:
            out["drugs"] = info.get("drugs", [])
            if not out["drugs"]:
                out["note"] = "目前没有针对该基因获批或在研的直接靶向药物记录"
        return out


def make_gene_tool(db: GeneDB | None = None) -> Tool:
    db = db or GeneDB()
    return Tool(
        name="gene_lookup",
        description="查询基因的全名、别名、功能，以及相关靶向药物（药名、机制、获批状态）。输入基因符号或常见别名。",
        input_schema={
            "type": "object",
            "properties": {
                "gene": {"type": "string", "description": "基因符号或别名，如 EGFR、HER2、p53"},
                "include_drugs": {"type": "boolean", "default": True, "description": "是否返回靶向药"},
            },
            "required": ["gene"],
            "additionalProperties": False,
        },
        fn=db.lookup,
    )
