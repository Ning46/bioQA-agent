# 基因型填补（Genotype Imputation）

基因型填补是利用参考单倍型面板（如 1000 Genomes、HapMap、HRC）推断芯片上未直接分型的 SNP 基因型，或补全缺失的基因型数据。

原理：同一区域的 SNP 之间存在连锁不平衡，先对样本做定相（phasing，用 SHAPEIT、Eagle），把基因型拆成两条单倍型，再把它们与参考面板中的单倍型匹配，按隐马尔可夫模型计算未分型位点的等位基因概率。常用软件有 IMPUTE2、Minimac4、Beagle。

基因型编码通常为 0、1、2，表示携带的替代等位基因个数：0 为参考纯合（homozygous reference），1 为杂合（heterozygous），2 为替代纯合（homozygous alternative）。填补的作用包括：合并不同芯片做 meta 分析、精细定位、提高检验效能。填补质量用 INFO 或 R² 评估，常过滤 R² < 0.3 的位点。
