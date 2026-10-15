# CRISPR-Cas9 基因编辑

CRISPR-Cas9 源自细菌的适应性免疫系统，现在是最主流的基因编辑技术。向导 RNA（sgRNA）通过约 20 nt 的间隔序列与靶 DNA 互补配对，引导 Cas9 核酸酶在 PAM 序列（SpCas9 识别 NGG）上游切割，造成 DNA 双链断裂（DSB）。

细胞通过两条途径修复断裂：非同源末端连接（NHEJ）容易引入小的插入缺失（indel），常用于基因敲除；同源定向修复（HDR）在提供修复模板时可以实现精确的点突变或片段插入。

脱靶效应（off-target）是 CRISPR 的主要风险，可通过优化 sgRNA 设计、使用高保真 Cas9 变体降低。衍生技术包括碱基编辑（base editing）、先导编辑（prime editing）以及 CRISPRi/CRISPRa 转录调控。Perturb-seq 就是将 CRISPR 筛选与单细胞测序结合的方法。
