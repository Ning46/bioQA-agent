# 结构变异检测（Structural Variant Detection）

结构变异（SV）指长度通常大于 50 bp 的基因组变异，包括缺失、插入、倒位、易位和拷贝数变异（CNV）。基于二代测序的检测策略主要有四类：

1. 读段深度（read depth）：缺失区域覆盖度下降，重复区域覆盖度上升，适合检测 CNV。
2. 双端读段（read pair / discordant pair）：双端测序（paired-end，插入片段约 300–600 bp）或配对末端测序（mate-pair，跨度 2–10 kb）中，两条 read 的距离或方向异常提示存在 SV。mate-pair 跨度大，更适合大片段变异。
3. 分裂读段（split read）：一条 read 跨越断点，被拆成两段比对，可以精确到单碱基定位断点，工具如 Pindel。
4. 组装（assembly）：局部或从头组装后与参考比较。

常用工具：Manta、DELLY、LUMPY 综合多种信号。长读长测序（PacBio、Nanopore）对 SV 检测更有优势。
