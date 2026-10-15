# 蛋白质结构预测与 AlphaFold

蛋白质结构决定功能。实验解析方法包括 X 射线晶体学、核磁共振（NMR）和冷冻电镜（cryo-EM），结果存放在 PDB 数据库。

计算预测方法：同源建模（homology modeling，如 SWISS-MODEL，需要相似模板）、穿线法（threading）和从头预测。AlphaFold2 利用多序列比对中的共进化信息和 Evoformer 注意力网络，在 CASP14 中达到接近实验精度。AlphaFold 数据库已为大部分已知蛋白提供预测结构。

pLDDT 是 AlphaFold 给出的每个残基的置信度分数（0–100），>90 为高置信，<50 的区域常是无序区（intrinsically disordered region）。PAE（predicted aligned error）反映结构域之间相对位置的可信度。RMSD 用来衡量两个结构的差异。
