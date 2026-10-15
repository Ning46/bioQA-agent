from ..retrieval import HybridIndex
from .base import Tool, ToolError, validate
from .gene import GeneDB, make_gene_tool
from .knowledge import make_knowledge_tool
from .sequence import SEQUENCE_TOOL


def default_tools(index: HybridIndex, gene_db: GeneDB | None = None) -> list[Tool]:
    return [make_knowledge_tool(index), SEQUENCE_TOOL, make_gene_tool(gene_db)]


__all__ = ["Tool", "ToolError", "validate", "GeneDB", "default_tools"]
