# 多序列比对（Multiple Sequence Alignment）

多序列比对把三条或更多条序列同时对齐，用于找保守区域、构建系统发育树、预测蛋白功能域。精确求解是 NP 难问题，所以实际工具都用启发式方法。

渐进式比对（progressive alignment）：先计算两两距离，构建引导树（guide tree），再按树的顺序逐步合并序列。代表工具 ClustalW / Clustal Omega。缺点是早期引入的错误无法纠正（"once a gap, always a gap"）。

迭代精化：MUSCLE 和 MAFFT 在渐进比对后反复调整以提高得分。T-Coffee 结合多种比对信息提高准确度。

比对结果常用 FASTA 或 Clustal 格式保存，用 Jalview 可视化。保守位点可以用序列标识图（sequence logo）展示。
