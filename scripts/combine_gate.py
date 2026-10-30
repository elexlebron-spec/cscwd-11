"""Combine disjoint first-pass and extension seeds without treating repeats as data."""
import csv
import json
from pathlib import Path
from statistics import median
import sys
from collections import Counter
from summarize_gate import cluster_ci

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)
cases = []
all_seeds = set()
for name in sys.argv[2:]:
    root = Path(name)
    current = json.loads((root / "case_summary.json").read_text())
    seeds = {c["seed"] for c in current}
    assert not (all_seeds & seeds), "Extension seeds must be disjoint"
    all_seeds.update(seeds)
    for c in current:
        c["case_id"] = root.name + "/" + c["case_id"]
        c["cluster"] = tuple(c["cluster"])
        cases.append(c)
groups = []
for topo in sorted({c["topology"] for c in cases}):
    for n in sorted({c["n"] for c in cases}):
        all_cases = [c for c in cases if c["topology"] == topo and c["n"] == n]
        nontrivial = [c for c in all_cases if c["nontrivial"] and c["exact_pair"]]
        lo, hi = cluster_ci(nontrivial)
        groups.append({"topology": topo, "n": n, "all_cases": len(all_cases),
                       "nontrivial_equal_optimum_cases": len(nontrivial),
                       "median_ratio_all_cases": median(c["ratio"] for c in all_cases),
                       "median_ratio_nontrivial": median(c["ratio"] for c in nontrivial),
                       "cluster_bootstrap_95_low": lo, "cluster_bootstrap_95_high": hi,
                       "median_full_ms_nontrivial": median(c["full_ms"] for c in nontrivial),
                       "median_barr_ms_nontrivial": median(c["barr_ms"] for c in nontrivial),
                       "median_region_ratio_nontrivial": median(c["region_ratio"] for c in nontrivial),
                       "greedy_suboptimal_cases": sum(c["greedy_suboptimal"] for c in all_cases),
                       "proven_budget_binding_cases": sum(c["proven_binding"] for c in all_cases)})
report = {"sources": sys.argv[2:], "cases": len(cases), "seeds": sorted(all_seeds),
          "solver_runs": len(cases) * 2 * 3,
          "all_exact_pairs": all(c["exact_pair"] for c in cases),
          "greedy_suboptimal_cases": sum(c["greedy_suboptimal"] for c in cases),
          "proven_budget_binding_cases": sum(c["proven_binding"] for c in cases),
          "full_statuses": dict(Counter(c["full_status"] for c in cases)),
          "barr_statuses": dict(Counter(c["barr_status"] for c in cases)),
          "groups": groups,
          "design": "Initial holdout seeds 100-102 frozen before calibration analysis; extension seeds 103-109 frozen after first holdout results, with identical factor levels. Report stages separately as well as combined.",
          "timing_estimator": "Median of per-case FullCP/BARRCP ratios after first taking the median of three timings per method; percentile bootstrap by (n,topology,seed), 2000 resamples. All easy, active and degenerate strata retained."}
(out / "summary.json").write_text(json.dumps(report, indent=2))
(out / "cases.json").write_text(json.dumps(cases, indent=2))
with (out / "paired_summary.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(groups[0]))
    writer.writeheader()
    writer.writerows(groups)
print(json.dumps(report, indent=2))
