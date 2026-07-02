# mgnify-structure-prediction-by-esmfold2 — experiment record
(created 2026-07-02 00:31; status: **DONE ✅** — 528,365 WT 全部完成, 100% 覆盖, 0 失败)

## 1. Goal / hypothesis
用 **ESMFold2-Fast**（Biohub, 2026-05 发布）为 **MGnify Stability Dataset** 的 **WT scaffold**
批量预测 all-atom 3D 结构，供下游 structure-aware ΔG 模型（SaProtΔG / ESM3ΔG）使用。
目标：**每个 WT sample 都产出一个结构**（完整性是硬指标）。

## 2. Design & decision points（submit 前定稿；用户已逐条拍板）
- **模型**：`biohub/ESMFold2-Fast`（单序列 / 无 MSA 的 inference-optimized 变体）。
  - ⚠ fast checkpoint 本体 `model.safetensors` 仅 755MB（folding trunk），但 `config.json` 的
    `esmc_id = biohub/ESMC-6B` → **仍挂载完整 ESMC-6B（25.4GB）作为 LM backbone**。
    "fast" 来自 单序列 + 少 diffusion steps + 少 loops，而非小 LM。→ **必须 a100**。
- **fast 采样参数**：`num_loops=3, num_sampling_steps=50, num_diffusion_samples=1, seed=0`
  （官方 fast 示例值）。
- **精度 (dtype)**：默认 **bfloat16**（省显存、a100 快）。benchmark 时抽样与 float32 对比
  mean pLDDT / 结构差异，若可忽略则全量用 bf16（决策点，benchmark 后确认）。
- **序列范围（用户指示：仅 WT）**：`name == PDB_name` 的行 = **528,365 个 WT**，每条序列唯一。
  - 另有 **4,623 个 orphan PDB_name**（只被 mutant 引用、无自身 WT 行）→ **不 fold**，
    显式记录于 `data/esmfold2_fast_wt_input/orphan_pdb_names.txt`（不静默丢弃）。
  - 序列长度 60–80 aa（median 70）。
- **输出格式**：gzip 压缩 mmCIF（`<id>.cif.gz`，ESMFold2 原生 `to_mmcif()`）。
  - 目录分 **256 桶**（`md5(id)[:2]`）避免单目录 ~53 万文件。
  - 原子写（`.tmp`→`os.replace`）：断点续跑安全，partial 文件不计为完成。
  - B-factor/pLDDT：每条 mean pLDDT + pTM 记入 per-shard metrics TSV，供后续按置信度筛选。
- **tag（用户指示）**：存储文件夹与文档均标 fast → 目录名 `esmfold2-fast-pred-structure`。
- **分支（用户指示）**：从 main **原地** `git checkout -b mgnify-structure-prediction-by-esmfold2`
  （不建新 worktree），**绝不 push main**；本任务**只增量**新文件夹/脚本，不改任何现存文件。
- **并行策略（用户指示）**：SLURM **array 分片**，短 walltime，分批 launch；a100 当前排队重
  （`squeue -p gpu` ~536）→ 用短 walltime 换更快调度 + 断点续跑，避免单作业超时丢进度。
- **验收（用户指示）**：`check_completeness.py` 核对每个 WT 都有非空结构，缺失者写 redo_manifest 补跑。

## 3. Run config
- **代码（本地分支）**：`mgnify-structure-prediction/`
  - `build_wt_manifest.py` — 生成 WT fasta/manifest（已跑）
  - `esmfold2_fast_predict.py` — 分片 folding worker（分片/续跑/原子写/metrics）
  - `check_completeness.py` — 完整性验收 + redo manifest
  - `download_esmfold2_weights.sh` / `setup_ibex_env.sh` — 权重下载 / env 构建
- **ESMFold2 源码**：本地 `/home/guoj0f/share/esm-latest/esm/` ↔ Ibex `/ibex/user/guoj0f/share/esm-latest/esm/`
  （与旧 `share/esm` = evolutionaryscale/esm 严格分离）
- **权重（shared store）**：`share/hf_cache/`（本地下载→rsync 到 `/ibex/user/guoj0f/share/hf_cache/`）
  - `biohub/ESMFold2-Fast`（721MB） + `biohub/ESMC-6B`（25.4GB）
- **conda env**：`mgnify-esm`（Python 3.12 + `pip install -e esm` → torch 2.12 + Biohub transformers fork）
- **Ibex per-branch dir**：`/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2/`
- **★ 预测结构绝对路径（Ibex，暂存于此）**：
  `/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2/data/esmfold2-fast-pred-structure/`
- **WT 输入（Ibex）**：`…/mgnify-structure-prediction-by-esmfold2/data/esmfold2_fast_wt_input/wt_manifest.csv`
- **SLURM**：默认 `--gres=gpu:a100:1`；benchmark walltime 1h；array walltime 待 benchmark 定；
  sbatch 脚本在 `ibex-records/mgnify-structure-prediction-by-esmfold2/sh/`
- **job ids**：benchmark = TBD；array = TBD

## 4. Change log
- 2026-07-02 00:31: 分支建立、目录骨架、WT manifest（528,365）、fast 配置锁定；
  权重下载、Ibex env 构建、代码/输入同步 —— 完成。
- 2026-07-02 00:5x: benchmark 调试三连（每次 sbatch 快速暴露一个问题）：
  1. **cu130 too old**：esm 默认拉 torch 2.12.1+cu130，但 a100 驱动为 CUDA 12.8 →
     在 mgnify-esm 重装 **torch 2.11.0+cu128**（已写入 setup_ibex_env.sh，可复现）。
  2. **CCD offline 缺失**：`ESMFold2InputBuilder` 需 `ccd.pkl`（来自 biohub/ESMFold2），
     compute node 无外网 → login node 预下 `ccd.pkl`（417MB）到 hf_cache，脚本设 `ESMCFOLD_CCD_PATH`。
  3. **bf16 dtype 冲突**：模型 bf16 但输入 featurization 为 fp32（`mat1/mat2 dtype` 报错）→
     改用 **float32**（native 精度，零冲突，质量最佳；显存仅 13.6GB）。
- 2026-07-02 01:10: benchmark 通过（200/200，见 §5）；提交全量 array `47941241`（0-199%20, fp32）。

## 5. Results
### Benchmark（job 47941188, A100-80GB, fp32, 200 WT）
- **200/200 成功，0 失败**；速度 **~1.0 s/structure**（steady state）；模型加载 13s。
- **显存 13.6 GB**（40GB a100 亦可）；输出 **平均 11.8 KB/结构**（gzip mmCIF）。
- pLDDT（0–1 尺度）样例 0.50–0.77，pTM 0.29–0.57（小 domain，中等置信度符合预期）。
- **全量投影**：528,365 × 1.0s ≈ **147 GPU-h ≈ 6.1 GPU-day**；总输出 **~6.2 GB**。

### 全量 array（job 47941241 — **DONE ✅**）
- 配置：200 shards（~2,642 WT/shard, 实测 ~43min/shard）× walltime 1:15:00 × 并发 %20 × fp32 × seed 0。
- **结果（完整性验收通过）**：
  - **完成 528,365 / 528,365 = 100.0000% 覆盖，0 失败** ✅（实际 .cif.gz 文件数 = 528,365，与 manifest 一致）
  - 墙钟 ~9.7h（01:10 提交 → 10:52 完成）：前段并发被其他作业挤到 ~2–5，其他作业结束后爬满 %20 提速跑完。
  - **pLDDT 分布**（0–1 尺度）：mean **0.687**，mean pTM 0.537；≥0.7 高 **58.4%**（308,373）、0.5–0.7 中 33.1%（174,630）、<0.5 低 **8.6%**（45,362）。
  - **总磁盘占用 6.9 GB**（平均 ~13 KB/结构，gzip mmCIF）。
  - 抽查 `rocklin_batch2_667445.cif.gz` 为合法 mmCIF（455 原子行）。
- ★ **预测结构绝对路径（Ibex，暂存于此）**：
  `/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2/data/esmfold2-fast-pred-structure/`
  （256 桶 `md5(id)[:2]`，每个 `<id>.cif.gz`；B-factor/plddt 记于 `results/fold_logs/shard*_metrics.tsv`）
- 复现：`ibex-records/mgnify-structure-prediction-by-esmfold2/sh/fold_array_20260702-010936.sh`
- 验收：`check_completeness.py --manifest wt_manifest.csv --out-dir <★> --redo-manifest redo.csv --metrics-glob '<fold_logs>/shard*_metrics.tsv'`

## 6. 状态：DONE ✅（2026-07-02 ~10:52）
528,365 个 WT 结构全部预测完成、100% 覆盖、0 失败，暂存于 Ibex（见 §5 ★路径）。

## 7. 补充任务: orphan WT structures（filtered-WT, structure-only）
- **目的**：为 **4,623 个 orphan scaffold**（WT 被 filter 出训练索引，但其 mutant 仍在 train）补 fold WT 结构，供 orphan mutant **threading**（补齐主任务按 WT 行 fold 时漏掉的这部分）。
- **数据来源**：orphan WT 序列从完整 CSV `230515_...csv` 的 `aa_seq` 找回（实测 **4,623/4,623**，0 缺失）。
- **⚠ 尊重作者 benchmark 设计（用户第4点）**：这些 WT 为 **structure-only** —— 标 `split=filtered_wt_structure_only`、`ddg_eligible=False`，**绝不作为训练/benchmark 样本**（不重新引入被 filter 的 WT）。关联的 **6,391 个 orphan mutant 全部在 `train` split**（不碰 test/val benchmark）。
- **不混淆（用户第2点）**：输出到**独立目录** `data/esmfold2-fast-pred-structure-orphan-wt/`（256 桶），**与主 528,365 严格分开**；跑完单独同步回本地。
- **link（用户第3点）**：`data/esmfold2_fast_orphan_wt_input/orphan_mutant_structure_links.csv`
  （`mutant_name → PDB_name → wt_structure_relpath`，附 `ddg_eligible=False`）供下游用 MGnify 训练 dG 时消费这批 orphan mutant 的 WT 结构。
- **配置**：同主任务（ESMFold2-Fast / 单序列 / fp32 / `num_loops=3, num_sampling_steps=50`, seed 0）；SLURM array `0-7%8`, walltime `0:45:00`；脚本 `sh/fold_orphan_wt_20260702-141644.sh`。
- **★ orphan WT 结构绝对路径（Ibex）**：`…/mgnify-structure-prediction-by-esmfold2/data/esmfold2-fast-pred-structure-orphan-wt/`
- job id / 覆盖率 / 磁盘 → 待填。
