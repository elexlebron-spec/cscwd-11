# BARR — Budget Anchored Region Reduction

Research code, manuscript and saved experiments for **Budget Anchored Region Reduction for Collaborative Responsibility Repair**, prepared for CSCWD 2027. This is a research draft; it has not been submitted or accepted.

## 作者与联系方式

- 姓名：**王治然（Zhiran Wang）**
- 作者身份：**独立第一作者**，当前论文作者名单仅列王治然。
- 单位：**中国海洋大学（Ocean University of China）**
- 邮箱：**2174560006@qq.com**

The author information above was supplied by the author. No department, academic title, ORCID, coauthor or publication DOI has been added.

## Paper and method

- [Authored paper PDF](paper/BARR_CSCWD2027_ZhiranWang.pdf)
- [LaTeX source](paper/manuscript/main.tex)
- [Model, proof and limitations](THEORY.md)
- [Experiment protocol](EXPERIMENT_PROTOCOL.md)
- [Author metadata](AUTHOR_INFO.json)

BARR derives a safe activity region from local unary perturbations, positive weighted handoff costs and an old-objective certificate. At zero old gap the restricted problem preserves an optimal value; otherwise its loss is at most the old gap. It preserves the existence of an appropriate optimum, not every tied optimum. The model has a fixed attractive binary graph and no additional capacity/scheduling constraints. Graph cuts, CP-SAT and Lagrangian relaxation are established tools. This repository does not establish priority over all prior work or guarantee conference acceptance.

## Reproduce

Use Python 3.12 on a CPU machine:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/summarize_comparison_v5.py results/public_comparison_v5 results/route_comparison_v5
.venv/bin/python scripts/summarize_core_repeats_v6.py results/core_repeats_v6_completed
```

These commands validate the saved evidence without rerunning long experiments. For a fresh core timing run, use a new output directory. On macOS keep the laptop awake and prefix the command with `caffeinate -disu`:

```sh
.venv/bin/python run_core_repeats_v6.py --config configs/core_repeats_v6_confirmed_awake.json --out results/core_repeats_new
```

Never overwrite frozen raw results. The 20 fixed core inputs have ten repeats per CP method (400 completed calls), recorded in two execution segments (261 + 139 after a tool interruption). Final queries pass clock/pause gates. These are not new independent inputs or a cross-hardware success-rate estimate. Earlier interrupted/timing-diagnostic attempts remain separate. See [clock correction](TIMING_FIX_V6.md).

## Evidence and boundaries

Saved inputs, source snapshots, output labels, lower/upper bounds, configurations and timing components are retained in `results/`. This includes 480 main combinations, 240 weighted ablation combinations, 32 inexact-old-plan cases, 140 scale/core inputs and 72 public-graph cases. Reused cases and merged views must not be counted as new independent instances. All incomplete solves and negative results remain.

The 72 public-graph cases use six CAD co-edit graphs; 66 finish by the shared unconstrained-cut shortcut. Public structure does not validate team qualification, spare capacity, synthetic costs, real handoff savings or universal speedups. Dense graphs and retained hard cores expose the method's limits.

## Public data and attribution

Gopsill, Snider and Hicks (2019), University of Bath Research Data Archive, [DOI 10.15125/BATH-00621](https://doi.org/10.15125/BATH-00621); original study [DOI 10.1017/dsj.2019.20](https://doi.org/10.1017/dsj.2019.20). Database/README are CC BY 4.0; the source notebook is MIT-licensed as stated by the archive and was not executed. [Attribution and transformation details](data/bath_00621/ATTRIBUTION.md) are retained. Authored-code licensing has not been newly assigned by this upload.

This repository intentionally identifies its author. It must not be represented as an anonymous review link. Historical experimental snapshots and the former materials README record earlier stages; the current paper and author metadata above govern this authored release. Private planning documents, chat/review notes, credentials, virtual environments and third-party paper PDFs are not part of this repository.
