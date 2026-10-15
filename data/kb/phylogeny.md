# 系统发育树构建

系统发育树（phylogenetic tree）描述物种或基因之间的进化关系。输入通常是多序列比对结果。

主要方法：
- 距离法：邻接法（Neighbor-Joining, NJ）和 UPGMA，先计算两两进化距离矩阵再聚类，速度快。UPGMA 假设分子钟（各支进化速率相同），NJ 不需要这个假设。
- 最大简约法（Maximum Parsimony）：寻找所需突变次数最少的树。
- 最大似然法（Maximum Likelihood, ML）：在给定替代模型（如 GTR、JC69）下寻找似然最大的树，工具有 RAxML、IQ-TREE。
- 贝叶斯法：MrBayes、BEAST，给出后验概率。

自展检验（bootstrap）通过对比对列重抽样评估分支的可信度，支持率 > 70% 一般认为可靠。树可以用 FigTree、iTOL 可视化。
