# 单细胞转录组分析（scRNA-seq）

单细胞 RNA 测序在单个细胞水平测量基因表达，可以识别细胞类型和细胞状态的异质性。常用平台为 10x Genomics，数据经 Cell Ranger 处理后得到细胞×基因的计数矩阵。

标准分析流程（Scanpy 或 Seurat）：
1. 质控：过滤检测到基因数过少的细胞（空液滴）和过多的细胞（双细胞 doublet），过滤线粒体基因比例过高的细胞。
2. 标准化与对数变换，筛选高变基因（HVG）。
3. 降维：PCA，然后构建邻居图。
4. 聚类：Leiden 或 Louvain 算法。
5. 可视化：UMAP 或 t-SNE。
6. 找 marker 基因并注释细胞类型。

批次效应可用 Harmony、scVI 或 BBKNN 校正。拟时序分析（trajectory / pseudotime，如 Monocle、PAGA）用于研究分化过程。
