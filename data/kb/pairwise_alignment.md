# 双序列比对：Needleman-Wunsch 与 Smith-Waterman

双序列比对是用动态规划求两条序列的最优对齐。

- Needleman-Wunsch 算法做全局比对（global alignment），要求两条序列从头到尾对齐，适合长度相近、整体相似的序列。
- Smith-Waterman 算法做局部比对（local alignment），得分矩阵中负值置零，从最高分回溯，找出最相似的子片段，适合寻找保守结构域。BLAST 是对局部比对的启发式加速。

打分包括替换矩阵和空位罚分。核酸常用简单的匹配/错配得分，蛋白质常用 BLOSUM62（适合中等距离同源蛋白）或 PAM 矩阵。仿射空位罚分（affine gap penalty）区分空位开启和空位延伸，更符合生物学实际。两种算法的时间复杂度都是 O(mn)。
