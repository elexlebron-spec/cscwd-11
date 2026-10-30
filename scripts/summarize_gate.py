"""Audit all saved solutions; paired timing CIs resample graph-setting clusters."""
import csv
from collections import defaultdict, Counter
import hashlib
import json
from pathlib import Path
from random import Random
from statistics import median
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from barr.core import Problem


def number(r, field):
    return float(r[field])


def percentile(values, p):
    values = sorted(values)
    return values[round((len(values) - 1) * p)]


def cluster_ci(cases):
    groups = defaultdict(list)
    for case in cases:
        groups[case["cluster"]].append(case["ratio"])
    groups = list(groups.values())
    if not groups:
        return None, None
    rng = Random(7261)
    estimates = []
    for _ in range(2000):
        sample = [x for _ in groups for x in rng.choice(groups)]
        estimates.append(median(sample))
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def summarize(folder):
    root = Path(folder)
    completion = json.loads((root / "completion.json").read_text())
    records = [json.loads(line) for line in (root / "solutions.jsonl").read_text().splitlines()]
    pairs = defaultdict(lambda: defaultdict(list))
    inputs = {}
    for r in records:
        case_id = r["case_id"]
        if case_id not in inputs:
            raw = json.loads((root / "inputs" / f"{case_id}.json").read_text())
            assert hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest() == r["input_sha256"]
            q = raw["new"]
            inputs[case_id] = Problem(tuple(map(tuple, q["unary"])), tuple(map(tuple, q["edges"])),
                                      tuple(q["x0"]), tuple(q["recourse"]))
        p = inputs[case_id]
        assert p.energy(r["x"]) == r["upper"]
        assert p.resource(r["x"]) == r["recourse_used"] <= r["budget"]
        assert r["lower"] <= r["upper"]
        if r["status"] == "OPTIMAL":
            assert r["lower"] == r["upper"]
        pairs[case_id][r["method"]].append(r)
    cases = []
    for case_id, methods in sorted(pairs.items()):
        assert set(methods) == {"FullCP", "BARRCP"}
        full, region = methods["FullCP"][0], methods["BARRCP"][0]
        eps = region["old_epsilon"]
        global_optimal = full["status"] == "OPTIMAL"
        if global_optimal:
            assert full["upper"] <= region["upper"] <= full["upper"] + eps
        assert region["lower"] <= full["upper"]
        tf = median(r["total_seconds"] for r in methods["FullCP"])
        tr = median(r["total_seconds"] for r in methods["BARRCP"])
        exact_pair = eps == 0 and all(r["status"] == "OPTIMAL" for values in methods.values() for r in values)
        if exact_pair:
            assert all(r["upper"] == full["upper"] for values in methods.values() for r in values)
        setting_keys = ["n", "topology", "coupling", "preference", "shock_scale", "anchors", "weighted", "degraded", "seed"]
        # Conservatively keep ALL factor levels that reuse the same RNG seed
        # together, not only different budgets and timing repetitions.
        cluster = tuple(full[key] for key in ("n", "topology", "seed"))
        cases.append({**{key: full[key] for key in setting_keys}, "case_id": case_id, "budget": full["budget"],
                      "cluster": cluster, "ratio": tf / tr, "full_ms": tf * 1000, "barr_ms": tr * 1000,
                      "old_epsilon": eps, "actual_loss": region["upper"] - full["upper"] if global_optimal else None,
                      "lower_slack": full["upper"] - region["lower"] if global_optimal else None,
                      "exact_pair": exact_pair, "nontrivial": not full["fastpath"],
                      "proven_binding": global_optimal and full["upper"] > full["unconstrained_value"],
                      "greedy_suboptimal": full["greedy_upper"] > full["upper"],
                      "finite_lr_gap": global_optimal and full["upper"] > full["penalty_lower"],
                      "full_branches": full["branches"],
                      "region_ratio": region["geodesic_region_n"] / region["n"],
                      "full_status": full["status"], "barr_status": region["status"]})
    assert len(cases) == completion["completed_cases"]
    summaries = []
    for topology in sorted({c["topology"] for c in cases}):
        for n in sorted({c["n"] for c in cases}):
            selected = [c for c in cases if c["topology"] == topology and c["n"] == n]
            if not selected:
                continue
            timed = [c for c in selected if c["exact_pair"] and c["nontrivial"]]
            lo, hi = cluster_ci(timed)
            summaries.append({"topology": topology, "n": n, "all_cases": len(selected),
                              "nontrivial_exact_cases": len(timed),
                              "median_full_ms": median(c["full_ms"] for c in timed) if timed else None,
                              "median_barr_ms": median(c["barr_ms"] for c in timed) if timed else None,
                              "median_paired_speed_ratio": median(c["ratio"] for c in timed) if timed else None,
                              "cluster_bootstrap_95_low": lo, "cluster_bootstrap_95_high": hi,
                              "median_region_ratio": median(c["region_ratio"] for c in timed) if timed else None,
                              "region_ge_70pct_cases": sum(c["region_ratio"] >= .7 for c in selected)})
    report = {"folder": str(root), "cases": len(cases), "solver_runs": len(records),
              "all_solutions_validated": True,
              "full_statuses": dict(Counter(c["full_status"] for c in cases)),
              "barr_statuses": dict(Counter(c["barr_status"] for c in cases)),
              "greedy_suboptimal_cases": sum(c["greedy_suboptimal"] for c in cases),
              "proven_budget_binding_cases": sum(c["proven_binding"] for c in cases),
              "finite_lr_gap_cases": sum(c["finite_lr_gap"] for c in cases),
              "full_branching_cases": sum(c["full_branches"] > 0 for c in cases),
              "nonzero_epsilon_cases": sum(c["old_epsilon"] > 0 for c in cases),
              "actual_loss_positive_cases": sum(c["actual_loss"] is not None and c["actual_loss"] > 0 for c in cases),
              "epsilon_range": [min(c["old_epsilon"] for c in cases), max(c["old_epsilon"] for c in cases)],
              "max_actual_loss": max(c["actual_loss"] for c in cases if c["actual_loss"] is not None),
              "median_certificate_gap": median(c["old_epsilon"] for c in cases),
              "groups": summaries,
              "caveat": "CIs resample (n, topology, seed) clusters, keeping all factor levels, budgets and timing repeats together. Three timing repetitions are not three independent instances. Nontrivial equal-optimum strata are reported separately; all easy/censored/approximate cases retained."}
    (root / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (root / "case_summary.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    with (root / "case_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(cases[0]))
        writer.writeheader()
        writer.writerows(cases)
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    for folder in sys.argv[1:]:
        summarize(folder)
