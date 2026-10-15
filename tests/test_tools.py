import pytest

from bioqa.tools import GeneDB, ToolError, validate
from bioqa.tools.gene import make_gene_tool
from bioqa.tools.sequence import SEQUENCE_TOOL, find_orfs, gc_content, reverse_complement, translate


def test_gc_content():
    assert gc_content("GGCC") == 1.0
    assert gc_content("ATGC") == 0.5
    assert gc_content("at gc\n") == 0.5


def test_reverse_complement():
    assert reverse_complement("ATGCGT") == "ACGCAT"


def test_translate_standard_code():
    assert translate("ATGGCCTAA") == "MA*"
    assert translate("ATGGCCTAAGGG", to_stop=True) == "MA"


def test_find_orfs_both_strands():
    fwd = "ATG" + "GCT" * 5 + "TAA"
    orfs = find_orfs("CC" + fwd + "CC", min_aa=3)
    assert orfs[0]["strand"] == "+" and orfs[0]["start"] == 3 and orfs[0]["protein"] == "MAAAAA"
    rev = find_orfs(reverse_complement(fwd), min_aa=3)
    assert rev[0]["strand"] == "-" and rev[0]["protein"] == "MAAAAA"


def test_validate_required_enum_pattern():
    schema = SEQUENCE_TOOL.input_schema
    with pytest.raises(ToolError, match="缺少必填参数"):
        validate({"operation": "gc_content"}, schema)
    with pytest.raises(ToolError, match="不在允许值中"):
        validate({"sequence": "ATGC", "operation": "fold"}, schema)
    with pytest.raises(ToolError, match="格式不正确"):
        validate({"sequence": "ATG1C", "operation": "gc_content"}, schema)
    with pytest.raises(ToolError, match="未知参数"):
        validate({"sequence": "ATGC", "operation": "gc_content", "foo": 1}, schema)
    out = validate({"sequence": "ATGC", "operation": "find_orfs", "min_orf_aa": "10"}, schema)
    assert out["min_orf_aa"] == 10  # 字符串数字被宽容转换


def test_validate_fills_default():
    assert validate({"sequence": "ATGC", "operation": "stats"}, SEQUENCE_TOOL.input_schema)["min_orf_aa"] == 30


def test_mixed_t_and_u_rejected():
    with pytest.raises(ToolError, match="同时包含 T 和 U"):
        SEQUENCE_TOOL({"sequence": "ATGCU", "operation": "stats"})


def test_gene_alias_and_suggestion():
    tool = make_gene_tool(GeneDB())
    assert tool({"gene": "her2"})["symbol"] == "ERBB2"
    with pytest.raises(ToolError) as e:
        tool({"gene": "EGRF"})
    assert "EGFR" in e.value.hint


def test_tool_spec_hides_internal_fields():
    spec = SEQUENCE_TOOL.spec()
    assert "pattern_hint" not in spec["input_schema"]["properties"]["sequence"]
