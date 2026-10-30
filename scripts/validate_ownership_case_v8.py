"""Read-only independent enumeration of both saved illustrative cohorts."""
from pathlib import Path
from itertools import product
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from barr.core import Problem, anchored_region
from barr.applicability import capacity_guard
from ownership_case_v8 import source_portfolio


def main():
    nodes, edges, _ = source_portfolio()
    report = {'source_blobs_verified': 10, 'cohorts': {}}
    for folder in ['ownership_case_v8_diagnostic', 'ownership_case_v8_completed']:
        directory = ROOT / 'results' / folder
        cfg = json.loads((directory / 'config.json').read_text())
        p = json.loads((directory / 'portfolio.json').read_text())
        rows = json.loads((directory / 'runs.json').read_text())
        assert p['nodes'] == nodes and tuple(map(tuple, p['edges'])) == edges
        old = Problem(tuple(map(tuple, p['old_unary'])), edges, tuple(p['x0']), tuple(p['recourse']))
        labels = list(product((0, 1), repeat=old.n))
        assert old.energy(old.x0) == min(map(old.energy, labels))
        expected = {(a, d, b) for a in range(old.n) for d in cfg['old_label_cost_increases'] for b in cfg['budgets']}
        actual = {(r['anchor'], r['increase'], r['budget']) for r in rows}
        assert len(rows) == len(expected) == len(actual) == 64 and actual == expected
        for row in rows:
            costs = [list(c) for c in old.unary]
            costs[row['anchor']][old.x0[row['anchor']]] += row['increase']
            new = Problem(tuple(map(tuple, costs)), edges, old.x0, old.recourse)
            region = anchored_region(new, (row['anchor'],), row['budget'])
            feasible = [x for x in labels if new.resource(x) <= row['budget']]
            unrestricted = min(map(new.energy, labels))
            opt = min(map(new.energy, feasible))
            opt_k = min(new.energy(x) for x in feasible if all(x[i] == old.x0[i] for i in range(old.n) if i not in region))
            assert row['optimum'] == row['region_optimum'] == opt == opt_k
            assert row['unrestricted_value'] == unrestricted and row['strict_budget_binding'] == (opt > unrestricted)
            assert row['new_energy_x0'] == new.energy(old.x0)
            assert tuple(row['region']) == region
            loads = ((1, 1),) * old.n
            for key, expected_pass in [('capacity_pass', True), ('capacity_fail', False)]:
                audit = capacity_guard(new, row['budget'], loads, row[key]['capacities'])
                assert audit['certified'] == expected_pass
                assert json.loads(json.dumps(audit)) == row[key]
            for method in ['FullCP', 'BARRCP']:
                r = row[method]
                assert new.resource(r['x']) <= row['budget'] and new.energy(r['x']) == r['upper'] == r['lower'] == opt
                assert r['fastpath'] == (row['unrestricted_recourse'] <= row['budget'])
        for rel, sha in json.loads((directory / 'source_hashes.json').read_text()).items():
            assert hashlib.sha256((directory / 'source' / rel).read_bytes()).hexdigest() == sha
        summary = json.loads((directory / 'summary.json').read_text())
        assert summary['shared_shortcuts'] == sum(r['FullCP']['fastpath'] for r in rows)
        assert summary['strict_budget_binding'] == sum(r['strict_budget_binding'] for r in rows)
        report['cohorts'][folder] = {'cases': len(rows), 'enumerated_labels_each': len(labels),
                                   'values_solutions_capacities_valid': True, 'source_snapshot_hashes_valid': True}
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
