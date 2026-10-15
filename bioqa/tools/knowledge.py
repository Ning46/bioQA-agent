"""知识检索工具：封装混合检索索引。"""
from __future__ import annotations

from ..retrieval import HybridIndex
from .base import Tool, ToolError


def make_knowledge_tool(index: HybridIndex) -> Tool:
    def knowledge_search(query: str, top_k: int = 3) -> dict:
        hits = index.search(query, top_k=top_k)
        if not hits:
            raise ToolError("知识库中没有找到相关内容", "换一种说法，或使用更具体的术语")
        return {"results": [{"doc_id": c.doc_id, "title": c.title, "text": c.text, "score": round(s, 4)}
                            for c, s in hits]}

    return Tool(
        name="knowledge_search",
        description="在生物信息学知识库中检索与问题相关的段落（BM25+向量混合检索并重排）。概念、方法、原理类问题使用。",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索问题，尽量完整"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        fn=knowledge_search,
    )
