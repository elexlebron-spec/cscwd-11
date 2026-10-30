#!/usr/bin/env python3
"""Small, reproducible feasibility runs. This is not the final paper benchmark."""
import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from datetime import datetime, timezone
from barr.core import greedy, mincut, solve_repair
from barr.generate import generate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/smoke.json")
    parser.add_argument("--out", default="results/smoke")
    args = parser.parse_args()
    raw_config = Path(args.config).read_bytes()
    config = json.loads(raw_config)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    code_files = sorted([Path(__file__), *Path("barr").glob("*.py")])
    code_hash = hashlib.sha256(b"".join(p.read_bytes() for p in code_files)).hexdigest()
    metadata = {"utc_started": datetime.now(timezone.utc).isoformat(),
                "python": sys.version, "machine": platform.machine(), "platform": platform.platform(),
                "config_sha256": hashlib.sha256(raw_config).hexdigest(), "code_sha256": code_hash,
                "config": config, "purpose": "feasibility_only_not_final_paper_evidence"}
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    fields = ["topology", "n", "seed", "budget", "method", "upper", "lower", "gap_abs", "status",
              "recourse_used", "region_n", "old_epsilon", "nodes", "cut_calls", "total_seconds",
              "preprocess_seconds", "optimization_seconds"]
    with (out / "runs.csv").open("w", newline="", encoding="utf-8") as file, (out / "solutions.jsonl").open("w", encoding="utf-8") as solutions:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for topology in config["topologies"]:
            for n in config["sizes"]:
                for seed in config["seeds"]:
                    old, new = generate(n, seed, topology, config.get("shock_count", 1), config.get("weighted", True))
                    for budget in config["budgets"]:
                        # Alternate order to reduce systematic thermal/order effects.
                        order = (True, False) if seed % 2 else (False, True)
                        for regional in order:
                            r = solve_repair(old, new, budget, config["seconds_per_solver"], regional)
                            record = {"topology": topology, "n": n, "seed": seed, "budget": budget,
                                      "method": "BARR" if regional else "FullBB", **r}
                            writer.writerow(record)
                            solutions.write(json.dumps(record) + "\n")
                            file.flush()
                            solutions.flush()
                            print(f'{record["method"]} {topology} n={n} seed={seed} B={budget}: U={r["upper"]} L={r["lower"]} region={r["region_n"]} status={r["status"]}', flush=True)
    print(f"Saved actual observations to {out}")


if __name__ == "__main__":
    main()
