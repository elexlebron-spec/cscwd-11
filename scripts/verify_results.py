"""Reconstruct inputs and independently check every saved solution's objective/budget."""
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from barr.generate import generate

root = Path(sys.argv[1] if len(sys.argv) > 1 else "results/pilot_001")
meta = json.loads((root / "metadata.json").read_text())
config = meta["config"]
records = [json.loads(line) for line in (root / "solutions.jsonl").read_text().splitlines()]
pairs = {}
for record in records:
    _, p = generate(record["n"], record["seed"], record["topology"],
                    config.get("shock_count", 1), config.get("weighted", True))
    assert p.energy(record["x"]) == record["upper"]
    assert p.resource(record["x"]) == record["recourse_used"] <= record["budget"]
    assert record["lower"] <= record["upper"]
    if record["status"] == "optimal":
        assert record["lower"] == record["upper"]
    key = (record["n"], record["seed"], record["topology"], record["budget"])
    pairs.setdefault(key, {})[record["method"]] = record
for pair in pairs.values():
    if all(v["status"] == "optimal" for v in pair.values()):
        assert len({v["upper"] for v in pair.values()}) == 1
print(f"Verified {len(records)} saved feasible solutions and {len(pairs)} paired cases in {root}")
