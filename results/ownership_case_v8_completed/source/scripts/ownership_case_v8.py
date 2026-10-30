"""Verify a sourced two-owner portfolio and enumerate every declared toy repair.

No dependency on a live network; use byte-verified upstream source blobs. This
case validates an explicitly proposed routing layer, not an industrial trial.
"""
from pathlib import Path
from itertools import product
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from barr.core import Problem, anchored_region, restrict
from barr.flow import mincut_fast
from barr.applicability import capacity_guard, solve_capacity_guarded, CapacityNotCertified


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source_portfolio():
    directory = ROOT / 'data/fluentui_v8'
    provenance = json.loads((directory / 'provenance.json').read_text())
    for f in provenance['files']:
        raw = (directory / f['local_path']).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == f['git_blob_sha1']
    teams = {'@microsoft/cxe-prg', '@microsoft/teams-prg'}
    package_roots = set()
    lines = (directory / 'CODEOWNERS').read_text().splitlines()
    for line in lines:
        fields = line.split('#', 1)[0].split()
        if fields and fields[0].startswith('packages/') and set(fields[1:]) == teams:
            path = fields[0]
            package_roots.add(path.rsplit('/', 1)[0] if path.endswith(('/library', '/stories')) else path)
    manifests = sorted(directory.rglob('package.json'))
    assert len(manifests) == len(package_roots) == 8
    nodes = []
    for file in manifests:
        path = file.relative_to(directory).as_posix()
        package_root = path.removesuffix('/package.json').removesuffix('/library')
        assert package_root in package_roots
        # Matching implementation file path, not later build/config/spec exceptions.
        implementation = path.removesuffix('/package.json') + '/src/index.ts'
        last_match = None
        for number, line in enumerate(lines, 1):
            fields = line.split('#', 1)[0].split()
            if fields and ('*' not in fields[0]) and (implementation == fields[0] or implementation.startswith(fields[0].rstrip('/') + '/')):
                last_match = (number, fields[0], fields[1:])
        assert last_match and set(last_match[2]) == teams
        data = json.loads(file.read_text())
        nodes.append({'name': data['name'], 'manifest': path, 'implementation_scope': implementation.rsplit('/', 1)[0],
                      'owner_rule_line': last_match[0], 'owner_rule_pattern': last_match[1],
                      'listed_alternatives': last_match[2], 'dependencies': sorted(data.get('dependencies', {}))})
    nodes.sort(key=lambda x: x['name'])
    pos = {node['name']: i for i, node in enumerate(nodes)}
    edges = sorted({(min(i, pos[name]), max(i, pos[name]), 1) for i, node in enumerate(nodes)
                    for name in node['dependencies'] if name in pos and name != node['name']})
    return nodes, tuple(edges), provenance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    cfg = json.loads((ROOT / 'configs/ownership_case_v8.json').read_text())
    nodes, edges, provenance = source_portfolio()
    n = len(nodes)
    penalty = cfg.get('old_nonpreferred_cost', 4)
    unary = tuple((0, penalty) if i % 2 == 0 else (penalty, 0) for i in range(n))
    initial = Problem(unary, edges, (0,) * n, (1,) * n)
    old_min, x0 = mincut_fast(initial)
    old = Problem(unary, edges, x0, initial.recourse)
    all_labels = list(product((0, 1), repeat=n))
    assert old_min == min(map(old.energy, all_labels)) == old.energy(x0)
    loads = ((1, 1),) * n
    rows = []
    for anchor in range(n):
        for increase in cfg['old_label_cost_increases']:
            changed = [list(c) for c in unary]
            changed[anchor][x0[anchor]] += increase
            new = Problem(tuple(map(tuple, changed)), edges, x0, initial.recourse)
            unrestricted_value, cut = mincut_fast(new)
            for budget in cfg['budgets']:
                region = anchored_region(new, (anchor,), budget)
                reduced, constant, ids = restrict(new, region)
                feasible = [x for x in all_labels if new.resource(x) <= budget]
                opt = min(map(new.energy, feasible))
                oracle = min(x for x in feasible if new.energy(x) == opt)
                opt_k = min(reduced.energy(x) + constant for x in product((0, 1), repeat=reduced.n)
                            if reduced.resource(x) <= budget)
                assert opt == opt_k
                initial_gate = capacity_guard(new, budget, loads, (n, n))
                capacities = initial_gate['worst_budget_load']
                audit = capacity_guard(new, budget, loads, capacities)
                assert audit['certified']
                for x in feasible:
                    assert all(x.count(t) <= capacities[t] for t in (0, 1))
                # Two routes include the same capacity guard, and the same shortcut.
                results = [solve_capacity_guarded(old, new, budget, loads, capacities,
                                                 regional=regional, seconds=3, seed=0)
                           for regional in (False, True)]
                assert all(r['upper'] == r['lower'] == opt for r in results)
                fail_team = next((t for t in (0, 1) if audit['max_incoming_load'][t] > 0), None)
                failed = None
                if fail_team is not None:
                    tight = list(capacities)
                    tight[fail_team] -= 1
                    try:
                        solve_capacity_guarded(old, new, budget, loads, tuple(tight), regional=True)
                        raise AssertionError('Guard accepted a nonredundant capacity')
                    except CapacityNotCertified as exc:
                        failed = exc.audit
                rows.append({'case_id': f'a{anchor}_d{increase}_b{budget}', 'anchor': anchor,
                             'increase': increase, 'budget': budget, 'region': region,
                             'old_energy': old_min, 'new_energy_x0': new.energy(x0),
                             'unrestricted_value': unrestricted_value, 'unrestricted_recourse': new.resource(cut),
                             'strict_budget_binding': opt > unrestricted_value,
                             'region_optimum': opt_k, 'optimum': opt, 'oracle': oracle,
                             'capacity_pass': audit, 'capacity_fail': failed,
                             'FullCP': results[0], 'BARRCP': results[1]})
    illustration = next((r for r in rows if r['unrestricted_recourse'] > r['budget']
                         and len(r['region']) < n and r['optimum'] < r['new_energy_x0']), None)
    summary = {'case_role': cfg['purpose'], 'source_commit': provenance['commit'], 'n': n, 'm': len(edges),
               'cases': len(rows), 'calls': len(rows) * 2,
               'shared_shortcuts': sum(r['FullCP']['fastpath'] for r in rows),
               'strict_budget_binding': sum(r['strict_budget_binding'] for r in rows),
               'proper_region': sum(len(r['region']) < n for r in rows),
               'all_enumerated_values_match': True, 'capacity_guard_passes': len(rows),
               'capacity_guard_rejections': sum(r['capacity_fail'] is not None for r in rows),
               'worked_case': illustration['case_id'] if illustration else None, 'performance_claim': False}
    (out / 'config.json').write_text(json.dumps(cfg, indent=2) + '\n')
    (out / 'portfolio.json').write_text(json.dumps({'nodes': nodes, 'edges': edges, 'old_unary': unary,
                                                  'x0': x0, 'recourse': old.recourse}, indent=2) + '\n')
    (out / 'runs.json').write_text(json.dumps(rows, indent=2) + '\n')
    (out / 'worked_case.json').write_text(json.dumps(illustration, indent=2) + '\n')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    sources = ['scripts/ownership_case_v8.py', 'configs/ownership_case_v8.json', 'barr/applicability.py',
               'barr/core.py', 'barr/cpsat.py', 'barr/flow.py', 'barr/timing.py', 'data/fluentui_v8/provenance.json']
    for rel in sources:
        target = out / 'source' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / rel).read_bytes())
    (out / 'source_hashes.json').write_text(json.dumps({rel: digest(ROOT / rel) for rel in sources}, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
