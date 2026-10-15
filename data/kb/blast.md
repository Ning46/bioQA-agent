# BLAST 序列相似性搜索

BLAST（Basic Local Alignment Search Tool）是最常用的序列相似性搜索工具，用于在数据库中查找与查询序列相似的核酸或蛋白质序列。它基于启发式的种子-延伸（seed-and-extend）策略：先找到短的精确匹配词（word），再向两侧延伸成高分片段对（HSP）。

常见程序：blastn（核酸对核酸）、blastp（蛋白对蛋白）、blastx（翻译核酸查询对蛋白库）、tblastn（蛋白查询对翻译核酸库）。

结果中的 E-value（期望值）表示在给定数据库大小下，随机得到同等或更高得分的匹配数量。E-value 越小，匹配越显著，通常 E < 1e-5 被认为可信。Bit score 与数据库大小无关，可用于不同搜索之间的比较。

想知道一段未知序列是什么物种或什么基因，通常第一步就是用 NCBI BLAST 比对 nr/nt 数据库。
