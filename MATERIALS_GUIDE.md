# Historical anonymous-material guide

The text below records the earlier v6 materials archive. The current repository intentionally identifies its author; it does not inherit that archive's anonymous-hosting status. Use the root README and AUTHOR_INFO.json for this authored release. Frozen experimental data remain unchanged.

# BARR review materials

Anonymous experimental materials for Budget Anchored Region Reduction for Collaborative Responsibility Repair. No submission-author identity, affiliation, private proposal, credentials, or local workspace path is included. Third-party data creators are credited below; they are not the submission authors.

## Quick start

Use Python 3.12 on a CPU machine. From this folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m unittest discover -s tests -v
```

To reproduce graph extraction without overwriting the supplied graphs, run `.venv/bin/python scripts/import_bath_graphs.py --out data/bath_00621/graphs_rerun_new`. The original importer is retained as data/bath_00621/importer_v5_source.py.

The saved outcomes are the evidence used in the manuscript; rerunning wall-clock solves can change certified counts and times. Never overwrite a saved results folder.

```sh
.venv/bin/python scripts/summarize_comparison_v5.py results/public_comparison_v5 results/route_comparison_v5
.venv/bin/python run_comparison_v5.py --suite public --out results/public_rerun_new
.venv/bin/python run_comparison_v5.py --suite synthetic --out results/route_rerun_new
```

The public experiment is 72 cases/216 calls. The fresh route comparison uses all 140 earlier scale/core inputs, with 420 calls. These are reused inputs, not 140 new independent instances. Earlier stages remain separate: holdout_v2 + holdout_extension_v2 (480 main cases), ablation_weighted_v3 (240 weighted cases), epsilon_v2 (32 quality cases), scale_holdout_v4/core_holdout_v4 (original large/core timings). Single v5 timings are not pooled with older triple-timing intervals. The original easy pilot is retained for historical diagnosis only.

Each results stage supplies source snapshots, full original inputs, output labels, lower/upper bounds, configuration and hashes. runs.csv is for inspection; solutions.jsonl preserves labels and the rational Lagrangian trace. summary.json and case_summary.json are validated summaries. MANIFEST.sha256 hashes the distributed files.

## Methods and guarantees

barr/core.py contains region and boundary construction; barr/cpsat.py matches full/reduced CP-SAT; barr/lagrangian.py is the classical rational-cut plus primal-recovery comparator. It is not a reproduction of a complete named optimizer and its finite multiplier search is not claimed to optimize the dual. Feasible candidates and valid lower bounds are reported together; no speed comparison silently equates approximate and exact solutions.

With a valid old-objective gap epsilon, local unary changes, positive handoff costs, a fixed attractive graph and no additional hard constraints, BARR preserves one budget optimum when epsilon is zero, otherwise its loss is at most epsilon. It does not preserve every tied optimum. Active capacity, skills, multi-team feasibility or scheduling need a new proof; past budget optima need recertification at later events.

## Repeated hard-core queries

The v6 stage repeats every one of the 20 saved core inputs ten times per CP method (400 calls). It uses the original fixed instance solver seeds, a five-second query target, a single worker and balanced sequential order. The configuration was frozen before the new outcomes. These are repeats in two execution segments on one laptop, not 200 new independent inputs and not evidence about all hardware or future sessions. The original v4/v5 timings remain separate. Query-time median/IQR includes incomplete calls and must not be called uncensored time-to-optimum. Per-instance closure counts, residual gaps, full labels and checksums are retained.

```sh
.venv/bin/python scripts/summarize_core_repeats_v6.py results/core_repeats_v6_completed
.venv/bin/python run_core_repeats_v6.py --config configs/core_repeats_v6_confirmed_awake.json --out results/core_repeats_rerun_new
```

The first completed 400-query session had 42 internal/external clock discrepancies above 0.1 s (six above 5 s); a second diagnostic attempt was stopped after 129 calls. All these rows remain diagnostic material. The complete replacement uses macOS CLOCK_MONOTONIC_RAW for backend accounting/deadlines, three-clock validation and temporary process-scoped sleep assertions. A further 400-query continuous-clock diagnostic session recorded 13 pauses and is retained separately. The final cohort completes all 400 planned queries in two execution segments (261 saved, 139 resumed after a tool interruption); completed records are never rerun. It with the operator keeping the laptop awake and aborts if clock consistency or a pause-delta gate fails. Model/search settings are unchanged. Check the saved timing notes and clock audit; do not pool diagnostic attempts into the repeated-query table. On macOS, prefix the timing command with `/usr/bin/caffeinate -disu`.

Reading/validating saved outcomes is quick; a full timing rerun may take tens of minutes. Run without other benchmarks or builds from this task. Runtime results may differ. The summarizer uses the frozen source/config hashes and checks all budgets/energies/intervals against saved earlier runs. External proof of an optimum never retroactively changes a call's original closure status.

## Public source and transformations

Gopsill, J., Snider, C., and Hicks, B. (2019), University of Bath Research Data Archive, DOI https://doi.org/10.15125/BATH-00621 . Original study: https://doi.org/10.1017/dsj.2019.20 . The source CAD-edit database/README are CC BY 4.0; demonstration notebook is MIT-licensed per the archive. See data/bath_00621/ATTRIBUTION.md and provenance_v5.json for attribution, source hashes, transformation details and retained graph statistics. The notebook was not executed. Retain these third-party notices.

A/B/C denote three historical projects, not our two synthetic pools. Co-edit associations are inferred proxies, not verified physical interfaces. Ownership, qualification, reserved capacity, costs, changes and budgets are assumptions; no measured industrial transfer savings are asserted. All 72 public cases are kept, including 66 cut-shortcut cases. Dense/high-connectivity and timed-out hard-core results are retained.

## Scope

A single laptop, synthetic cost models, sparse seed coverage and wall-clock time limits constrain conclusions. Originality and venue acceptance are not established by this archive. Authored code is supplied as peer-review material; its release license is to be finalized by the authors. Third-party data retain their stated licenses.
