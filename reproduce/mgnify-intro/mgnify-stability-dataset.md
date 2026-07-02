# MGnify Stability Dataset — 我们目前的理解与认知

> 记录截至 2026-07-02 我们对 **MGnify Stability Dataset** 的调研认知，供后续复现/建模参考。
> 标注了 **哪些是数据实测、哪些来自论文、哪些是我们推导的概念**，便于后人判断可信度。

---

## 0. 一句话
MGnify Stability 是一个 **~百万级、小 domain（60–80 aa）绝对折叠稳定性（ΔG）** 数据集，由 mega-scale cDNA display proteolysis 实验测得；配套的 **SaProtΔG / ESM3ΔG** 是在其上 fine-tune、以 **序列 + 预测结构** 为输入来预测**绝对 ΔG** 的模型。

## 1. 来源论文
- **标题**：*Accurate protein stability prediction for small domains using mega-scale experiments*
- **作者**：Yehlin Cho\*, Kotaro Tsuboyama\*, …, Sergey Ovchinnikov†, Gabriel J. Rocklin†（MIT / Northwestern）
- **出处**：bioRxiv 2026，DOI `10.64898/2026.05.19.726285`（posted 2026-05-20, CC-BY-NC-ND）
- **本 repo** = 该论文的官方模型 release（作者 Yehlin Cho；`absolute-stability-predictor`，inference-only）。
- 论文 PDF 本地：`/home/guoj0f/repos/Sources/MGnify.pdf`（62 页，含 Methods + SI）。

## 2. 数据集是怎么造出来的（论文 Methods, "Library design"）
1. 对 **MGnify sequence clusters（≥10 条）** 跑 **AlphaFold2** 得结构；
2. 用 Clauset-Newman-Moore 聚类把结构**切成独立 domain**；
3. 过滤：去 Cys、限 **60–80 aa**、mean **pLDDT ≥ 50**、去单长螺旋/无二级结构；
4. 随机选 **730,000 个 wild-type 序列**做实验；
5. 从这些 WT 序列**设计** single/multiple/**indel** mutant（random + BLOSUM-biased 采样）；
6. 用 **cDNA display proteolysis（mega-scale）** 测稳定性 → recalibrated ΔG。

→ **要点**：**结构是"按 WT domain"用 AF2 折的**；mutant 是从 WT 序列派生的，**共用母体 WT 的 backbone**（非逐 mutant 折）。

## 3. 本 repo 里的相关文件（实测）
| 文件 | 内容 | 规模 |
|---|---|---|
| `data/230515_K50dG_dmsv4_dmsv5_dmsv7_concat260429.csv` | **完整** MGnify Stability（recalibrated ΔG, dmsv4/5/7 合并）| 2.1G / **2,287,292 行 × 38 列** |
| `data/mgnify_training_index.csv` | **训练用 sequence index** | 132M / **965,856 行 × 5 列** |
| `data/benchmarks.zip` | 各 benchmark（S1724/ThermoMutDB/TED…）| — |
| `data/README.md` | 各数据集说明 | — |

- 完整 CSV 的 38 列全是 `dna_seq / aa_seq / aa_seq_full / deltaG / log10_K50* / fitting_error / mgnify(flag) / dm_design / split …` —— **序列 + ΔG/拟合元数据，无任何结构/坐标列**。
- ⚠ **数据集本身只有 sequence + dG，不含 folded/predicted structures**（repo 里仅 `examples/` 下 2 个 mgnify 示例 PDB，属 demo，非数据集）。结构须自行 fold。

## 4. 训练索引 `mgnify_training_index.csv` 解剖（实测）
列：`name, split, seq, dG, PDB_name`

| 维度 | 数值 |
|---|---|
| 总行数 / unique seq | 965,856 / 965,856（每行序列唯一）|
| unique `PDB_name`（scaffold）| 532,988 |
| **WT 行**（`name == PDB_name`）| **528,365**（每条 seq 唯一）|
| **mutant 行**（`name != PDB_name`）| 437,491（`PDB_name` 指向母体 scaffold）|
| **orphan scaffold**（有 `PDB_name`、无 `name==PDB_name` 行）| **4,623**（= WT 的 0.87%）|
| 归属 orphan 的行（全是 mutant）| 6,391（占全部行 0.66% / mutant 的 1.46%）|
| 序列长度 | 60–80 aa（min 60 / median 70 / mean 69.7 / max 80）|
| split 分布 | **train 960,216** / test 3,283 / validation 1,761 / validation_online 596 |

- **`PDB_name` 的语义 = 该行使用哪份结构**。WT 行用自己的结构；mutant 行的 `PDB_name` 指向母体 → **mutant 复用母体 WT 结构**（thread）。
- **"orphan" 是我们从数据推导的概念**（论文未用此词）：某 scaffold 只在训练索引里被 mutant 引用、自己没有 WT 标签行。
  - ✅ **实测**：这 4,623 个 orphan 的 **WT 序列全部存在于完整 CSV `230515_...csv`**（`name==orphan` 行带 `aa_seq`，4,623/4,623 找到），只是其 `train_name` 为**空** → 被排除出训练集，故在训练索引里无 WT 行。它们的 mutant 反而进了训练。
  - 所以 orphan 缺的只是**训练索引里的 WT 标签行**；**WT 序列可从完整 CSV 完整找回**（→ 需要时可 fold 补齐母体结构）。
- split=='train'（960,216）**正好等于论文的训练集规模** → 该 split 即论文训练集。

## 5. 模型如何使用这份数据（论文 + repo 代码交叉确认）
- **任务**：**绝对 ΔG 回归** —— 输入 `序列 + 预测结构`，per-residue 稳定性经 head 聚合成 global ΔG（`ESM3dG.py` 默认 forward → 单个 dG）。
- **训练/评测结构来源**：论文用 **AlphaFold2 预测结构（+ PAE）**；**mutant 用母体 WT backbone**（`PDB_name` 指向母体；Fig 3a："for a given backbone structure, WT and mutant sequences are evaluated independently"）。**train 与 test 同一套分配** —— test 里 mutant 的 dG 也用其 WT 对应结构。
  - ⚠ 注意：论文里"对每条 test 序列各折一个结构"（line 1256/1333）指的是 **baseline/外部模型**（zero-shot pLDDT/PAE 代理、IFUM），**不是** SaProtΔG/ESM3ΔG。
- **训练集**：960,216 条 = **525,127 WT + 435,089 point mutant**，**indel 不用于训练**，全部 <30% identity to test。
- **Loss（关键）**：**联合 loss = 0.3·WT-ΔG + 0.3·mutant-ΔG + 1.0·ΔΔG**（ΔΔG 项权重最高）。
  - ΔΔG = `ΔG_mut − ΔG_wt`（同 backbone，模型各算再相减）→ **ΔΔG loss 需要 WT**；orphan mutant 无 WT → **进不了 ΔΔG 项**，但仍能进绝对 mutant-ΔG（0.3）项。
- **微调方式**：LoRA/PEFT 效果最好；SaProtΔG / ESM3ΔG 均为 **3 个独立训练的 ensemble**。
- **性能**：MGnify test 上 Spearman **0.88 / 0.87**，RMSE **0.80 kcal/mol**。
- 另有 "augmented" 版本（缓解 cDNA proteolysis 的末端二级结构偏置）。

## 6. 我们自己产出的结构资产（ESMFold2-Fast）
- 按用户要求，用 **ESMFold2-Fast**（Biohub, single-seq, fp32, `num_loops=3, num_sampling_steps=50`）对 **528,365 个 WT** 全量 fold，**100% 覆盖 / 0 失败**，gzip mmCIF 共 ~6.9 GB。
- 存放：Ibex `…/mgnify-structure-prediction-by-esmfold2/data/esmfold2-fast-pred-structure/`；本地同 repo 相对路径 `data/esmfold2-fast-pred-structure/`。
- 详见 `ibex-records/mgnify-structure-prediction-by-esmfold2/mgnify_wt_esmfold2fast_20260702-003114.md`。
- ⚠ **与论文的差异**：论文训练结构用的是 **AF2（+PAE）**，我们用 **ESMFold2-Fast** —— 范式相同（每序列一结构、mutant thread 母体 backbone），但**结构来源不同**，喂给已训练的 SaProtΔG/ESM3ΔG 存在一定 domain shift。

## 7. 尚未解决 / 待核实
- **orphan（4,623, <1%）**：我们本次按训练索引的 WT 行 fold，未含这些 orphan。但其 **WT 序列已确认可从完整 CSV `230515_...csv` 完整找回（4,623/4,623）** → 若要补齐，直接抽 `name==orphan` 的 `aa_seq` 用 ESMFold2-Fast fold 即可（**不需要** mutant 代理，也**不存在"拿不到序列"的问题**）。
- ESMFold2-Fast vs AF2 结构对下游 ΔG 预测精度的实际影响，未量化。

## 8. 参考
- 论文：DOI `10.64898/2026.05.19.726285`（`/home/guoj0f/repos/Sources/MGnify.pdf`）
- 上游 mega-scale：Tsuboyama et al. 2023
- 本 repo：`github.com/yehlincho/absolute-stability-predictor`
- 我们的结构预测记录：`ibex-records/mgnify-structure-prediction-by-esmfold2/`
