# Perturb-seq

Perturb-seq 把 CRISPR 遗传扰动与单细胞 RNA 测序结合：在一个混合细胞群中引入成百上千种不同的 sgRNA（或编码变体），然后对每个细胞同时读出它接受的扰动标签和全转录组表达谱。这样一次实验就能得到大量基因扰动的转录组表型。

分析要点：先根据 guide 条形码把细胞分配到扰动组，过滤未检测到或检测到多个 guide 的细胞；与非靶向对照（non-targeting control）比较得到每个扰动的表达特征；再对扰动特征做聚类，发现功能相近的基因模块。

应用案例包括大规模解析癌症中编码变体的功能后果（massively parallel phenotyping of coding variants），以及绘制全基因组尺度的遗传相互作用图谱。
