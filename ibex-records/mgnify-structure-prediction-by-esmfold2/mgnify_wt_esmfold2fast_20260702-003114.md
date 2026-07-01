# mgnify-structure-prediction-by-esmfold2 — experiment record
(created 2026-07-02 00:31; status: **RUNNING** — deploy/benchmark 阶段)

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
  权重下载（ESMC-6B ~24G/25.4G）、Ibex env 构建、代码/输入同步 —— 均进行中。

## 5. Results（所有作业完成后填）
- benchmark：每条耗时 / 显存 / 输出平均大小 / bf16-vs-fp32 → 待填
- 全量：完成数 / 覆盖率 / 失败数 / pLDDT 分布 / 总磁盘占用 → 待填
- 结构绝对路径（最终确认）：见 §3 ★
- 复现命令：见 sh/ 脚本
