# BioQA Agent · 生物信息问答智能体

一个面向生物信息学问题的问答 Agent：混合检索知识库、按需调用序列分析和基因/靶向药查询工具、支持多轮对话中的指代消解，并配有可复现的评估框架。

默认使用**离线规则模型**跑通全链路（不需要任何 API key，`pytest` 即可复现所有结果）；设置 `ANTHROPIC_API_KEY` 后可切换到 Claude。

```
用户问题
   │  指代消解（"它 / 这条序列 / 这个方法" → 上文实体）
   ▼
Agent 主循环 ──► 模型（function calling）──► 选工具 + 填参数
   ▲                                             │
   │  tool_result（成功结果 / 错误信息+修正建议）    ▼
   └──────────────────────── 参数校验 ──► 执行工具
                                   ├─ knowledge_search ─► BM25 ┐
                                   │                    向量 ──┴► RRF 融合 ─► 重排
                                   ├─ sequence_analysis（GC / 反向互补 / 翻译 / 六框 ORF）
                                   └─ gene_lookup（基因功能 / 别名 / 靶向药）
```

## 功能

### 1. 混合检索（`bioqa/retrieval/`）
- **双路召回**：Okapi BM25（中文字 unigram+bigram，英文按词）＋ 稠密向量检索。
- **RRF 融合**：`score = Σ 1/(k + rank)`，只看排名，规避 BM25 分数与余弦相似度量纲不一致的问题。
- **重排**：对召回的候选做 (query, doc) 成对打分。默认的 `FeatureReranker` 离线运行，特征包括领域概念匹配（口语说法 → 规范术语，见 `data/glossary.json`，并按概念在文档中的主导度加权）、查询词覆盖率、标题匹配和召回先验；也提供调用 Claude 的 `LLMReranker`。
- **增量知识更新**：对知识库每个文件计算 SHA-256，与 manifest 比对得出新增/修改/删除，只重新切块变化的文件；向量侧把新块折入已训练的嵌入空间，变化比例超过阈值（默认 30%）才整体重训。

> 向量检索默认用 LSA（字符 n-gram TF-IDF + TruncatedSVD），目的是完全离线可复现。`Embedder` 是可替换接口，换成 bge / sentence-transformers 只需实现 `fit` / `encode`。

### 2. Agent（`bioqa/agent/`, `bioqa/tools/`, `bioqa/llm/`）
- **Function calling 主循环**：模型决策 → 参数校验 → 执行 → 结果回传，设最大步数防止死循环。
- **三个工具**，均用 JSON Schema 描述参数：`knowledge_search`、`sequence_analysis`、`gene_lookup`。
- **参数校验与错误自我修正**：校验 required / type / enum / pattern / 范围 / 多余参数；校验失败或执行报错都以 `is_error` 的 tool_result 回传，并附修正建议（如"你是不是想查：EGFR"、"请去掉 FASTA 标题行"），模型据此改参重试；同一工具连续失败超过上限后停止调用。
- **多轮记忆与指代消解**：按轮保存历史，窗口裁剪只在用户消息边界切，保证 tool_use / tool_result 成对；从工具调用中抽取基因、序列、知识主题作为实体，把"它 / 这个基因 / 这条序列 / 这个方法"替换为对应实体。
- **模型可替换**：`RuleBasedLLM`（离线、确定性，用于测试全链路）与 `AnthropicLLM`（Claude Messages API tool use）实现同一接口。

### 3. 评估（`eval/`, `tests/`）
- **端到端用例**（`eval/e2e_cases.json`，12 个）：检查工具调用序列、报错次数、指代消解结果和回答关键词，覆盖拼错基因名的自我修正、带杂质序列的清洗重试、三类指代、知识外问题如实拒答等。
- **检索消融**：BM25 / 向量 / RRF / RRF+重排 四种配置，在两组各 20 条口语化困难查询上报告 Hit@1、Hit@3、MRR。
- **基线回归检查**：指标写入 `eval/baseline.json`，任一指标下降即失败；已接入 `pytest` 和 GitHub Actions。

## 评测结果

以下数字由 `python -m eval.run_eval` 生成（离线规则模型，结果确定可复现）。

**检索消融**（20 条口语化查询，按文档计 Hit@1）：

| 方法 | 开发集 Hit@1 | 开发集 MRR | 留出集 Hit@1 | 留出集 MRR |
|---|---|---|---|---|
| BM25 | 85% | 0.912 | 95% | 0.975 |
| 向量 | 80% | 0.868 | 100% | 1.000 |
| BM25 + 向量（RRF） | 85% | 0.897 | 95% | 0.975 |
| RRF + 重排 | **100%** | **1.000** | 95% | 0.975 |

**端到端用例**：12 / 12 通过。

**如何解读**：
- 开发集用于调试重排器（修正了概念打分方式、补充了两条术语别名），所以开发集上的 100% 有过拟合成分，不能当作泛化效果。
- 留出集在代码冻结后编写、只跑过一次。重排在留出集上没有带来提升（95% → 95%）：留出集查询含有较多专业术语，BM25 和向量检索本身就能命中；重排的收益集中在纯口语、缺少术语的查询上。
- 两组查询和术语表都由同一作者编写，规模小（各 20 条），结论只适合作为方向性参考。更可靠的评估需要他人编写的更大查询集。

## 快速开始

```bash
pip install -e ".[dev]"            # 或 pip install -r requirements.txt

python -m bioqa --trace            # 交互式问答，显示每步工具调用
python -m eval.run_eval            # 跑消融 + 端到端 + 基线回归检查
python -m pytest -q                # 单元测试 + 评测回归
ruff check .                       # 代码检查

export ANTHROPIC_API_KEY=sk-...    # 可选：切换到 Claude
python -m bioqa --llm claude --trace
python -m eval.run_eval --llm claude
```

示例对话（离线规则模型）：

```
你> EGRF的靶向药有哪些
  [✗ gene_lookup] {'gene': 'EGRF'}
      错误：未找到基因 'EGRF'  建议：你是不是想查：EGFR, ERBB2
  [✓ gene_lookup] {'gene': 'EGFR'}
Agent> EGFR（Epidermal growth factor receptor）… 奥希替尼：三代 EGFR-TKI，覆盖 T790M 耐药突变 …

你> 它的功能是什么
  [指代消解] EGFR的功能是什么
  [✓ gene_lookup] {'gene': 'EGFR'}
```

## 项目结构

```
bioqa/
  retrieval/   text.py 分词切块 · bm25.py · vector.py · fusion.py(RRF) · reranker.py · index.py(混合索引+增量更新)
  tools/       base.py(Schema 校验/ToolError) · knowledge.py · sequence.py · gene.py
  llm/         base.py(接口) · rule_based.py(离线) · anthropic_llm.py(Claude)
  agent/       loop.py(主循环) · memory.py(多轮记忆+指代消解)
data/
  kb/          26 篇生物信息学知识文档
  glossary.json  口语/别名 → 规范术语
  genes.json     13 个基因的功能与靶向药
eval/          e2e_cases.json · hard_queries.jsonl(开发集) · heldout_queries.jsonl(留出集) · run_eval.py · baseline.json
tests/         27 个测试
```

CI（GitHub Actions）在每次 push 时跑 `pytest` 和 `eval.run_eval`，评测指标低于 `eval/baseline.json` 即判定失败。

## 局限与后续

- 离线规则模型只是为了验证链路，回答是对工具结果的抽取式拼接；真实问答质量需要接入大模型评测（`--llm claude` 已支持，计划补充 LLM-as-judge 的回答质量评分）。
- 知识库和基因表规模很小，仅作演示；`genes.json` 中的用药信息不构成医疗建议。
- 计划：替换为真实嵌入模型、扩充他人编写的评测集、接入 PubMed / NCBI 等外部工具。

## License

MIT
