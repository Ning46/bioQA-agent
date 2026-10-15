# RNA-seq 转录组测序与差异表达分析

RNA-seq 通过对 cDNA 文库进行高通量测序来测量基因表达水平。标准流程：质控（FastQC）→ 去接头（Trimmomatic/fastp）→ 比对到参考基因组（STAR、HISAT2）或伪比对（Salmon、kallisto）→ 计数（featureCounts）→ 差异表达分析。

差异表达分析常用 DESeq2 和 edgeR，二者都基于负二项分布对 read count 建模，能处理生物学重复间的过度离散。结果中的 log2FoldChange 表示表达倍数变化，padj 是经过 Benjamini-Hochberg 多重检验校正后的 p 值，一般以 padj < 0.05 且 |log2FC| > 1 筛选差异基因。

火山图（volcano plot）用于展示差异基因，横轴为 log2FC，纵轴为 -log10(padj)。差异基因之后通常做 GO/KEGG 富集分析。
