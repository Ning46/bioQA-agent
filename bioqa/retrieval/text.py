"""文本处理：中英文混合分词与文档切块。

中文不依赖第三方分词器，使用字 unigram + bigram，英文/数字按词切分。
这种方式对生物信息领域大量中英混写的术语（如"EGFR 突变"、"T790M"）足够稳健。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_CJK = r"一-鿿"
_TOKEN_RE = re.compile(rf"[{_CJK}]+|[a-z0-9]+(?:[-'.][a-z0-9]+)*")

STOPWORDS = {
    # 英文
    "the", "a", "an", "of", "and", "or", "to", "in", "is", "are", "for", "on", "with", "what", "how",
    # 中文常见虚字（单字级别）
    "的", "了", "是", "在", "和", "与", "或", "吗", "呢", "吧", "啊", "么", "个", "这", "那", "我", "你",
    "有", "就", "都", "也", "要", "会", "能", "怎", "什", "啥", "把", "被", "让", "给", "用", "到",
}


def tokenize(text: str) -> list[str]:
    """把文本切成检索用 token。中文输出单字和相邻二字组合，英文输出小写单词。"""
    tokens: list[str] = []
    for piece in _TOKEN_RE.findall(text.lower()):
        if re.match(rf"[{_CJK}]", piece):
            chars = list(piece)
            tokens.extend(c for c in chars if c not in STOPWORDS)
            tokens.extend(a + b for a, b in zip(chars, chars[1:], strict=False))
        elif piece not in STOPWORDS:
            tokens.append(piece)
    return tokens


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    tokens: list[str] = field(default_factory=list, repr=False)


def chunk_document(doc_id: str, raw: str, max_chars: int = 400) -> list[Chunk]:
    """按段落切块；标题拼到每个块前面，保证块脱离上下文后仍可被检索到。"""
    lines = raw.strip().splitlines()
    title = doc_id
    if lines and lines[0].startswith("#"):
        title = lines[0].lstrip("#").strip()
        lines = lines[1:]
    paragraphs = [p.strip() for p in "\n".join(lines).split("\n\n") if p.strip()]

    chunks: list[Chunk] = []
    buf = ""
    for para in paragraphs:
        if buf and len(buf) + len(para) > max_chars:
            chunks.append(buf)
            buf = para
        else:
            buf = f"{buf}\n{para}" if buf else para
    if buf:
        chunks.append(buf)

    out = []
    for i, body in enumerate(chunks):
        text = f"{title}\n{body}"
        out.append(Chunk(f"{doc_id}#{i}", doc_id, title, text, tokenize(text)))
    return out
