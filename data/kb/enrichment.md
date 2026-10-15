# 功能富集分析（GO / KEGG / GSEA）

得到差异基因列表后，富集分析用来回答"这些基因集中在哪些生物学功能或通路上"。

GO（Gene Ontology）分为三个本体：生物过程（BP）、分子功能（MF）、细胞组分（CC）。KEGG 和 Reactome 提供代谢与信号通路注释。

过表达分析（ORA）用超几何检验或 Fisher 精确检验，比较差异基因在某个功能类别中的比例是否高于背景，需要做多重检验校正（FDR）。工具有 clusterProfiler、DAVID、g:Profiler、Enrichr。

GSEA（基因集富集分析）不需要设定差异阈值，而是把全部基因按差异程度排序，检验某个基因集是否集中在排序列表的顶部或底部，输出富集分数（ES/NES）。MSigDB 提供常用基因集。
