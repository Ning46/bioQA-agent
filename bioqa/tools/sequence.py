"""序列分析工具：GC 含量、反向互补、转录、翻译、ORF 查找、基本统计。"""
from __future__ import annotations

from collections import Counter

from .base import Tool, ToolError

_BASES = "ACGTTGCA"
COMPLEMENT = str.maketrans("ACGTUNacgtun", "TGCAANtgcaan")

_AA = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
CODON_TABLE = {a + b + c: _AA[16 * i + 4 * j + k]
               for i, a in enumerate("TCAG") for j, b in enumerate("TCAG") for k, c in enumerate("TCAG")}
STOP = {"TAA", "TAG", "TGA"}


def clean_seq(seq: str) -> str:
    return "".join(seq.split()).upper()


def gc_content(seq: str) -> float:
    s = clean_seq(seq)
    acgt = sum(s.count(b) for b in "ACGTU")
    return (s.count("G") + s.count("C")) / acgt if acgt else 0.0


def reverse_complement(seq: str) -> str:
    return clean_seq(seq).replace("U", "T").translate(COMPLEMENT)[::-1]


def translate(seq: str, frame: int = 0, to_stop: bool = False) -> str:
    s = clean_seq(seq).replace("U", "T")[frame:]
    protein = []
    for i in range(0, len(s) - 2, 3):
        aa = CODON_TABLE.get(s[i:i + 3], "X")
        if to_stop and aa == "*":
            break
        protein.append(aa)
    return "".join(protein)


def find_orfs(seq: str, min_aa: int = 30) -> list[dict]:
    """在六个阅读框中查找 ATG 起始、终止密码子结束的 ORF。坐标为正链 1-based。"""
    s = clean_seq(seq).replace("U", "T")
    n = len(s)
    orfs = []
    for strand, text in (("+", s), ("-", reverse_complement(s))):
        for frame in range(3):
            i = frame
            while i + 3 <= n:
                if text[i:i + 3] == "ATG":
                    j = i
                    while j + 3 <= n and text[j:j + 3] not in STOP:
                        j += 3
                    if j + 3 <= n:  # 找到终止密码子才算完整 ORF
                        aa_len = (j - i) // 3
                        if aa_len >= min_aa:
                            start, end = (i + 1, j + 3) if strand == "+" else (n - j - 2, n - i)
                            orfs.append({"strand": strand, "frame": frame + 1, "start": start, "end": end,
                                         "length_aa": aa_len, "protein": translate(text[i:j])})
                        i = j + 3
                        continue
                i += 3
    return sorted(orfs, key=lambda o: -o["length_aa"])


OPERATIONS = ["gc_content", "reverse_complement", "transcribe", "translate", "find_orfs", "stats"]


def sequence_analysis(sequence: str, operation: str, min_orf_aa: int = 30) -> dict:
    s = clean_seq(sequence)
    if len(s) < 3:
        raise ToolError("序列太短（少于 3 个碱基）")
    if "U" in s and "T" in s:
        raise ToolError("序列同时包含 T 和 U，无法判断是 DNA 还是 RNA", "请确认序列类型后统一碱基")

    if operation == "gc_content":
        return {"length": len(s), "gc_content": round(gc_content(s), 4)}
    if operation == "reverse_complement":
        return {"reverse_complement": reverse_complement(s)}
    if operation == "transcribe":
        return {"rna": s.replace("T", "U")}
    if operation == "translate":
        return {"protein": translate(s), "note": "* 表示终止密码子；从第 1 个碱基开始按第 1 阅读框翻译"}
    if operation == "find_orfs":
        orfs = find_orfs(s, min_orf_aa)
        return {"n_orfs": len(orfs), "orfs": orfs[:5]}
    if operation == "stats":
        counts = Counter(s)
        return {"length": len(s), "composition": dict(sorted(counts.items())), "gc_content": round(gc_content(s), 4)}
    raise ToolError(f"未知操作 {operation}", f"可选：{OPERATIONS}")


SEQUENCE_TOOL = Tool(
    name="sequence_analysis",
    description="对 DNA/RNA 序列做基本分析：GC 含量、反向互补、转录、翻译成蛋白、六框 ORF 查找、碱基组成统计。",
    input_schema={
        "type": "object",
        "properties": {
            "sequence": {"type": "string", "description": "核酸序列，只含 A/C/G/T/U/N，可含空白",
                         "pattern": r"[ACGTUNacgtun\s]+",
                         "pattern_hint": "序列只能包含 A/C/G/T/U/N，请去掉数字、标点和 FASTA 标题行"},
            "operation": {"type": "string", "enum": OPERATIONS, "description": "要执行的分析"},
            "min_orf_aa": {"type": "integer", "minimum": 1, "maximum": 10000, "default": 30,
                           "description": "find_orfs 时 ORF 的最小氨基酸长度"},
        },
        "required": ["sequence", "operation"],
        "additionalProperties": False,
    },
    fn=sequence_analysis,
)
