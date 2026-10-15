# VCF 变异文件格式

VCF（Variant Call Format）是存储基因组变异（SNP、indel、SV）的标准文本格式，由变异检测工具（GATK HaplotypeCaller、bcftools、DeepVariant）输出。

文件以 ## 开头的元信息行描述 INFO、FORMAT 字段和参考基因组，随后是表头行，固定列为：CHROM、POS、ID、REF、ALT、QUAL、FILTER、INFO，之后是 FORMAT 和各样本列。

样本列中的 GT 字段表示基因型：0/0 为参考纯合，0/1 为杂合，1/1 为替代纯合；用 | 分隔（如 0|1）表示已定相。DP 为测序深度，GQ 为基因型质量。

常用处理工具：bcftools（过滤、合并、统计）、VEP 和 ANNOVAR（功能注释）、GATK VQSR（变异质量重校准）。压缩后用 bgzip + tabix 建索引以便快速按区域查询。
