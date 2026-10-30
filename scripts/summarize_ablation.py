"""Validate every three-way ablation result, then summarize paired timings."""
from collections import defaultdict, Counter
import csv
import hashlib
import json
from pathlib import Path
from statistics import median
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from barr.core import Problem
from summarize_gate import cluster_ci


def main(folder):
    root = Path(folder)
    completion = json.loads((root / 'completion.json').read_text())
    cfg = completion['config']
    records = [json.loads(line) for line in (root / 'solutions.jsonl').read_text().splitlines()]
    by_case = defaultdict(lambda: defaultdict(list))
    inputs = {}
    for r in records:
        cid = r['case_id']
        if cid not in inputs:
            payload = json.loads((root / 'inputs' / f'{cid}.json').read_text())
            assert hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest() == r['input_sha256']
            q = payload['new']
            inputs[cid] = Problem(tuple(map(tuple, q['unary'])), tuple(map(tuple, q['edges'])), tuple(q['x0']), tuple(q['recourse']))
        p = inputs[cid]
        assert p.energy(r['x']) == r['upper']
        assert p.resource(r['x']) == r['recourse_used'] <= r['budget']
        assert r['lower'] <= r['upper']
        by_case[cid][r['method']].append(r)
    cases = []
    for cid, methods in sorted(by_case.items()):
        assert set(methods) == {'FullCP', 'HopCP', 'BARRCP'}
        for rows in methods.values():
            assert len(rows) == cfg['repeats']
            assert {r['repeat'] for r in rows} == set(range(cfg['repeats']))
        rows = [r for values in methods.values() for r in values]
        exact = all(r['status'] == 'OPTIMAL' and r['lower'] == r['upper'] and r['old_epsilon'] == 0 for r in rows)
        if exact:
            assert len({r['upper'] for r in rows}) == 1
        assert len({r['fastpath'] for r in rows}) == 1
        first = rows[0]
        t = {m: median(r['total_seconds'] for r in values) for m, values in methods.items()}
        cases.append({'case_id': cid, 'topology': first['topology'], 'n': first['n'],
                      'coupling': first['coupling'], 'anchors': first['anchors'],
                      'budget': first['budget'], 'seed': first['seed'],
                      'cluster': (first['n'], first['topology'], first['seed']),
                      'exact': exact, 'nontrivial': not first['fastpath'],
                      'weighted_region_ratio': first['weighted_region_n'] / first['n'],
                      'hop_region_ratio': first['hop_region_n'] / first['n'],
                      'hop_over_barr': t['HopCP'] / t['BARRCP'],
                      'full_over_barr': t['FullCP'] / t['BARRCP'],
                      'full_over_hop': t['FullCP'] / t['HopCP'],
                      **{m + '_ms': value * 1000 for m, value in t.items()}})
    assert len(cases) == completion['completed_cases']
    groups = []
    for topo in sorted({c['topology'] for c in cases}):
        all_cases = [c for c in cases if c['topology'] == topo]
        active = [c for c in all_cases if c['nontrivial'] and c['exact']]
        estimates = {}
        for ratio in ['hop_over_barr', 'full_over_barr', 'full_over_hop']:
            lo, hi = cluster_ci([{**c, 'ratio': c[ratio]} for c in active])
            estimates[ratio] = {'all_median': median(c[ratio] for c in all_cases),
                                'active_median': median(c[ratio] for c in active) if active else None,
                                'active_cluster_bootstrap_95': [lo, hi]}
        groups.append({'topology': topo, 'cases': len(all_cases), 'active_exact': len(active),
                       'median_weighted_region_ratio': median(c['weighted_region_ratio'] for c in active) if active else None,
                       'median_hop_region_ratio': median(c['hop_region_ratio'] for c in active) if active else None,
                       'estimates': estimates})
    report = {'cases': len(cases), 'solver_runs': len(records), 'all_solutions_validated': True,
              'all_three_way_exact': all(c['exact'] for c in cases),
              'statuses': dict(Counter(r['status'] for r in records)), 'groups': groups,
              'statistics': 'median of per-case paired ratios after three timing repetitions; bootstrap clusters (n,topology,seed), 2000 resamples; all cases and non-fastpath stratum both retained'}
    (root / 'summary.json').write_text(json.dumps(report, indent=2))
    (root / 'case_summary.json').write_text(json.dumps(cases, indent=2))
    with (root / 'case_summary.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(cases[0]))
        writer.writeheader()
        writer.writerows(cases)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main(sys.argv[1])
