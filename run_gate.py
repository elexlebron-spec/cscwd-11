#!/usr/bin/env python3
"""Prospective matched CP-SAT experiments; preserve every planned setting/seed.

Run from the project directory with .venv/bin/python. No objective-dependent
instance filtering. Raw records include solutions and difficulty diagnostics.
"""
import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter
import ortools
from ortools.sat.python import cp_model
from barr.baselines import greedy_delta, penalty_scan
from barr.core import Problem, anchored_region
from barr.cpsat import solve_repair_cpsat, solve_cpsat
from barr.flow import mincut_fast
from barr.generate_v2 import Setting, generate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    raw = Path(args.config).read_bytes()
    cfg = json.loads(raw)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    # Warm imports/solver initialization equally outside measured queries.
    solve_cpsat(Problem(((0, 1),), (), (0,), (1,)), 0, 1)
    names = ["n", "topology", "coupling", "preference", "shock_scale", "anchors", "budget", "weighted", "degraded", "seed"]
    source_files = [Path(__file__).resolve(), *sorted(Path("barr").glob("*.py"))]
    manifest = {}
    for path in source_files:
        rel = Path(path.name) if path.name == "run_gate.py" else Path("barr") / path.name
        snapshot = out / "source" / rel
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, snapshot)
        manifest[str(rel)] = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata = {"utc_started": datetime.now(timezone.utc).isoformat(), "python": sys.version,
                "machine": platform.machine(), "platform": platform.platform(), "ortools": ortools.__version__,
                "config": cfg, "config_sha256": hashlib.sha256(raw).hexdigest(), "source_sha256": manifest,
                "timing": "warm common imports; all query preprocessing, model build and solver construction included; single-thread; cold old certificate charged to BARR only",
                "scope": cfg["purpose"], "selection": "complete Cartesian configuration; no rejection/filtering"}
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (out / "config.json").write_bytes(raw)
    fields = ["case_id", *names, "repeat", "method", "status", "upper", "lower", "lower_reduced",
              "gap_abs", "region_n", "region_ratio", "old_epsilon", "recourse_used", "fastpath",
              "total_seconds", "common_seconds", "preprocess_seconds", "build_seconds", "solver_seconds",
              "branches", "conflicts", "greedy_upper", "unconstrained_value", "unconstrained_recourse",
              "penalty_upper", "penalty_lower", "geodesic_region_n", "input_sha256"]
    count = 0
    with (out / "runs.csv").open("w", newline="") as csvfile, (out / "solutions.jsonl").open("w") as jsonfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for index, values in enumerate(product(*(cfg["grid"][name] for name in names))):
            setting = Setting(**dict(zip(names, values)))
            old, new, details = generate(setting)
            case = asdict(setting)
            input_data = {"old": asdict(old), "new": asdict(new)}
            digest = hashlib.sha256(json.dumps(input_data, sort_keys=True).encode()).hexdigest()
            case_id = f"case_{index:04d}"
            (out / "inputs").mkdir(exist_ok=True)
            (out / "inputs" / f"{case_id}.json").write_text(json.dumps(input_data), encoding="utf-8")
            gvalue, _ = greedy_delta(new, setting.budget)
            freevalue, freex = mincut_fast(new)
            scan = penalty_scan(new, setting.budget)
            region_n = len(anchored_region(new, details["anchors"], setting.budget))
            for repeat in range(cfg.get("repeats", 1)):
                order = (False, True) if (index + repeat) % 2 else (True, False)
                for regional in order:
                    result = solve_repair_cpsat(old, new, setting.budget, cfg["seconds_per_query"],
                                                 regional, cfg["common_fastpath"], setting.seed)
                    record = {"case_id": case_id, **case, "repeat": repeat,
                              "method": "BARRCP" if regional else "FullCP", **result,
                              "gap_abs": result["upper"] - result["lower"],
                              "old_epsilon": details["old_epsilon"],
                              "greedy_upper": gvalue, "unconstrained_value": freevalue,
                              "unconstrained_recourse": new.resource(freex),
                              "penalty_upper": scan["upper"], "penalty_lower": scan["lower"],
                              "geodesic_region_n": region_n, "input_sha256": digest}
                    assert new.energy(record["x"]) == record["upper"]
                    assert new.resource(record["x"]) <= setting.budget
                    writer.writerow(record)
                    jsonfile.write(json.dumps(record) + "\n")
                    csvfile.flush()
                    jsonfile.flush()
            count += 1
            if count % 8 == 0:
                print(f"Completed {count} cases; last {setting.topology} n={setting.n} seed={setting.seed}", flush=True)
    metadata["utc_completed"] = datetime.now(timezone.utc).isoformat()
    metadata["completed_cases"] = count
    (out / "completion.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Completed {count} cases at {out}", flush=True)


if __name__ == "__main__":
    main()
