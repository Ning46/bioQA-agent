# 表达量标准化：CPM、RPKM/FPKM、TPM

原始 read count 受测序深度和基因长度影响，不能直接比较，需要标准化。

- CPM（Counts Per Million）：只校正测序深度，count / 总 reads × 10^6，适合样本间比较同一基因。
- RPKM / FPKM：同时校正测序深度和基因长度（每千碱基每百万 reads），FPKM 用于双端测序（按片段计）。缺点是各样本的 FPKM 总和不同，样本间不严格可比。
- TPM（Transcripts Per Million）：先除以基因长度，再按样本总和缩放到 10^6，每个样本 TPM 总和相同，样本间比较更合理。

做差异表达分析时不应输入 TPM/FPKM，DESeq2 使用原始 count 并用中位数比值法（median of ratios）计算 size factor，edgeR 使用 TMM 标准化。
