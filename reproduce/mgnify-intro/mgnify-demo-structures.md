# `mgnify_1A0N` / `mgnify_1A32` — 两个 demo 样本速览

> 一句话：repo 里**唯一两个带结构的 "mgnify" 示例**。结构是 **AF2 预测**的（不是实验结构），
> 序列是**天然蛋白**、**不属于 MGnify 训练/测试索引**，**只有其中一个有实验 ΔG**。
>
> 数据集背景见 `mgnify-stability-dataset.md`；我们的折叠任务见 `ibex-records/mgnify-structure-prediction-by-esmfold2/`。
> 本文结论均为**实测/源码核实**（2026-08-30 复核）。

---

## 1. 文件在哪

| 用途 | 路径 |
|---|---|
| **作者提供的结构**（随 repo 提交）| `examples/mgnify_1A0N.pdb`（73 KB）、`examples/mgnify_1A32.pdb`（89 KB）|
| 作者的 demo 定义 | `scripts/run_paper_examples_esm3dg.py` / `_saprotdg.py` 的 `EXAMPLES`：chain **A**，L=58 / 63，分组注释为 **`# MGnify dark proteome`** |
| 我们重折的对照结构 | Ibex `…/mgnify-structure-prediction-by-esmfold2/data/esmfold2-fast-pred-structure-validation/mgnify_1A0N.cif.gz`、`mgnify_1A32.cif.gz`（**未同步本地**）|
| 我们的折叠输入 | `data/esmfold2_fast_validation_input/val_manifest.csv`（2 行）|

---

## 2. 是什么序列

| id | L | 序列 | 真实身份（实测：与 PDB 沉积序列**精确匹配**）|
|---|---|---|---|
| `mgnify_1A0N` | 58 | `VTLFVALYDYEARTEDDLSFHKGEKFQILNSSEGDWWEARSLTTGETGYIPSNYVAPV` | **SH3 domain** = PDB **1A0N 链 B** 全长（SOLUTION NMR，SH3 与 proline-rich peptide 的复合物）|
| `mgnify_1A32` | 63 | `SPEVQIAILTEQINNLNEHLRVHKKDHHSRRGLLKMVGKRRRLLAYLRNKDVARYREIVEKLG` | **核糖体蛋白 S15** = PDB **1A32 链 A 第 22–84 位**（X-RAY）|

⚠ 两条都是**天然蛋白**，文件名就是对应的 PDB 条目号 —— 尽管作者脚本把它们标成 `"Metagenomic domain"`。
别把这个标签当作"来自 MGnify 数据集"的依据（见 §4）。

---

## 3. 结构怎么来的：**AF2 预测 + Amber relax**

四条互相印证的证据：

1. **不是实验结构** —— 与沉积坐标比不重合：
   `mgnify_1A0N` vs 1A0N 链 B = **CA-RMSD 0.86 Å**；`mgnify_1A32` vs 1A32 链 A = **0.67 Å**。
2. **B-factor 是 per-residue 的 pLDDT**（不是晶体学 B factor）：同残基内所有原子取值相同，
   沿序列呈典型置信度曲线（1A0N：N 端 67.1 → 核心 98.8 → C 端 92.7）。
   mean 96.6（1A0N，仅 1 个残基 <70）/ 97.3（1A32，无残基 <70）。
3. **含氢且是 Amber/OpenMM(PDB v3) 命名**（N 端 `H/H2/H3`，侧链 `HB2/HB3`、`HG21/22/23`；共 435 / 566 个 H）
   → 经过 **relaxation**，正是 AF2 pipeline 的标准收尾。
4. **排除法**：README「Structure Folding」只给两条产结构的路子 —— ESM Atlas 的 **ESMFold API** 与 **ColabFold**。
   源码核实 ESMFold 写的是 **per-atom** pLDDT 且**不加氢**（`b_factors=output["plddt"]`），与本文件特征相反
   （repo 里 `stability_*.pdb` / `darkmatter_*.pdb` 才是那个特征）。→ 只剩 **ColabFold = AF2**。
   论文方法学也一致：MGnify domain 由 **AlphaFold2** 预测结构的 PAE 聚类切出，模型训练用的是 "AlphaFold2-predicted native structures"。

> **保留**：两个文件的头被清空（全文只有 `ATOM`/`TER`/`END`，无 REMARK / pLDDT header），
> 所以**没有文件内元数据直接写着 "AlphaFold"**。以上是间接但一致的证据链。

---

## 4. 有什么 label

| id | 实验 ΔG | 在 MGnify 训练索引里吗 |
|---|---|---|
| `mgnify_1A0N` | ✅ **5.18 kcal/mol**（95% CI 5.12–5.25）| ❌ **不在** |
| `mgnify_1A32` | ❌ **无** | ❌ **不在** |

- **1A0N**：序列可在完整数据 `data/230515_K50dG_dmsv4_dmsv5_dmsv7_concat260429.csv` 中找到，
  对应行 `name = rocklin_batch2_825686`（`lib = dms4`）。但该行 **`mgnify = False` / `dm_design = True`**，
  且 `train_name` 与 `split` **均为空** → **被排除在训练索引之外**（也不在 `dmsv4_filtered_train_splits.csv`）。
  ⚠ 数据里的构建体是 62 aa（`GTG` + 58 aa + `DS`，两端另有 `SAGGSAGG` linker），**demo PDB 只含中间那 58 aa**。
- **1A32**：完整 CSV 与训练索引里**都找不到**（全长序列与 22 aa 内部子串均 0 命中）→ 无任何实验 label。
- **判据说明**：全量扫过 2,287,291 行完整 CSV —— 凡 `name` 出现在 `mgnify_training_index.csv` 的 529,611 行，
  `mgnify` flag **全部为 True**。所以 `mgnify = False` 就意味着不属于 MGnify 那个库。

**结论：这两个是 demo，不是 MGnify 数据集样本**，不能当作 in-distribution 的参照点。

---

## 5. 我们拿它们做了什么（+ 实验结构锚定的对比）

用途：验证我们的 ESMFold2-Fast 折叠流程没有大问题（详见 record md §8）。补上实验结构后的完整对比：

| 对比 | 1A0N (58 aa) | 1A32 (63 aa) |
|---|---|---|
| 作者 demo（AF2）vs **实验结构** | 0.86 Å / TM 0.918 | 0.67 Å / TM 0.948 |
| **我们 ESMFold2-Fast** vs **实验结构** | **0.78 Å** / TM 0.924 | **0.64 Å** / TM 0.952 |
| 我们 ESMFold2-Fast vs 作者 demo | 0.49 Å / TM 0.972 | 0.25 Å / TM 0.992 |

- **两个预测器彼此（0.49 / 0.25 Å）比各自与实验结构（0.6–0.9 Å）更接近** —— 典型的"预测器共享方法/训练偏差"。
  所以 record §8 里那个 0.25 Å 衡量的是**与 AF2 的一致性**，不是**准确性**。
- 这 2 个 case 上我们的 ESMFold2-Fast 对实验结构的偏差**略小于**作者 AF2 demo（0.78 vs 0.86、0.64 vs 0.67），
  但差距只有零点零几埃、且 n=2 —— 只能说"没有证据表明换成 ESMFold2-Fast 让结构变差"。

**能用来做什么**：pipeline sanity-check（模型/精度/输出/后处理是否有大问题）。
**不能用来做什么**：① 当 MGnify 分布内的精度评估（序列不在索引里）；② 当 AF2-vs-ESMFold2 的 domain-shift 证据
（仅 2 个高置信易折 case，mean pLDDT ~97，完全没覆盖我们全量里 pLDDT<0.5 的那 8.6%）。
