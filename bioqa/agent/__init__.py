from pathlib import Path

from ..llm import get_llm
from ..retrieval import HybridIndex
from ..tools import default_tools
from .loop import SYSTEM_PROMPT, Agent, AgentResult, Step
from .memory import ConversationMemory

KB_DIR = Path(__file__).resolve().parents[2] / "data" / "kb"


def build_agent(llm_name: str | None = None, kb_dir: str | Path = KB_DIR) -> Agent:
    index = HybridIndex(kb_dir)
    index.build()
    return Agent(get_llm(llm_name), default_tools(index))


__all__ = ["Agent", "AgentResult", "Step", "ConversationMemory", "SYSTEM_PROMPT", "build_agent"]
