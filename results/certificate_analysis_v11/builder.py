"""v11: Audit frozen records and derive descriptive geometry/certificate analyses.

No timed CP query is rerun. New files go into a new directory; source outcomes
are read only. Speed plots use the 480-case cohort with equal certified optima.
"""
from pathlib import Path
from collections import Counter, defaultdict
from statistics import median
import argparse, csv, hashlib, json, sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from barr.core import Problem, anchored_region
from barr.flow import mincut_fast
from barr.cpsat import merge_global_lower_bound


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def problem(q):
    return Problem(tuple(map(tuple, q['unary'])), tuple(map(tuple, q['edges'])),
                   tuple(q['x0']), tuple(q['recourse']))


def quantiles(values):
    return {key: float(v) for key, v in zip(['min', 'q1', 'median', 'q3', 'max'],
                                          np.quantile(values, [0, .25, .5, .75, 1]))}


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.] * len(values); j = 0
    while j < len(order):
        k = j + 1
        while k < len(order) and values[order[k]] == values[order[j]]:
            k += 1
        for t in range(j, k):
            result[order[t]] = (j + k - 1) / 2
        j = k
    return result


def spearman(rows, a, b):
    x, y = ranks([r[a] for r in rows]), ranks([r[b] for r in rows])
    return None if np.std(x) == 0 or np.std(y) == 0 else float(np.corrcoef(x, y)[0, 1])


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', required=True)
    args = parser.parse_args(); out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    source_hashes = {}
    def read_json(rel):
        path = ROOT / rel; source_hashes[rel] = sha(path)
        return json.loads(path.read_text())
    main_cases = read_json('results/gate_combined_v2/cases.json')
    raw_by_folder = {}
    for folder in ['holdout_v2', 'holdout_extension_v2', 'epsilon_v2']:
        path = ROOT / 'results' / folder / 'solutions.jsonl'
        source_hashes[str(path.relative_to(ROOT))] = sha(path)
        grouped = defaultdict(lambda: defaultdict(list))
        for line in path.read_text().splitlines():
            r = json.loads(line); grouped[r['case_id']][r['method']].append(r)
        raw_by_folder[folder] = grouped
    rows = []; timing_rows = []
    for c in main_cases:
        folder, case_id = c['case_id'].split('/')
        raw = read_json(f'results/{folder}/inputs/{case_id}.json')
        p = problem(raw['new']); old = problem(raw['old'])
        methods = raw_by_folder[folder][case_id]
        full, reg = methods['FullCP'], methods['BARRCP']
        assert len(full) == len(reg) == 3
        assert all(r['status'] == 'OPTIMAL' and r['lower'] == r['upper'] == full[0]['upper']
                   for rs in methods.values() for r in rs)
        for rs in methods.values():
            for r in rs:
                assert r['input_sha256'] == hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
                assert p.energy(r['x']) == r['upper'] and p.resource(r['x']) <= c['budget']
        assert all(r['fastpath'] == full[0]['fastpath'] for rs in methods.values() for r in rs)
        for fr, rr in zip(sorted(full, key=lambda r: r['repeat']), sorted(reg, key=lambda r: r['repeat'])):
            assert fr['repeat'] == rr['repeat']
            tr = {'case_id': c['case_id'], 'topology': c['topology'], 'n': p.n,
                  'repeat': fr['repeat'], 'shortcut': fr['fastpath']}
            for label, record in [('full', fr), ('barr', rr)]:
                for component in ['common', 'preprocess', 'build', 'solver', 'total']:
                    tr[label + '_' + component + '_ms'] = 1000 * record[component + '_seconds']
                tr[label + '_other_ms'] = tr[label + '_total_ms'] - sum(
                    tr[label + '_' + component + '_ms'] for component in ['common', 'preprocess', 'build', 'solver'])
            for component in ['common', 'preprocess', 'build', 'solver', 'other', 'total']:
                tr['saving_' + component + '_ms'] = tr['full_' + component + '_ms'] - tr['barr_' + component + '_ms']
            assert abs(sum(tr['saving_' + k + '_ms'] for k in ['common', 'preprocess', 'build', 'solver', 'other']) - tr['saving_total_ms']) < 1e-8
            timing_rows.append(tr)
        shortcut = full[0]['fastpath']
        anchors = [i for i in range(p.n) if old.unary[i] != p.unary[i]]
        region = anchored_region(p, anchors, c['budget']); keep = set(region)
        m = len(p.edges); mk = sum(i in keep and j in keep for i, j, _ in p.edges)
        tf, tr = median(r['total_seconds'] for r in full), median(r['total_seconds'] for r in reg)
        assert abs(tf / tr - c['ratio']) < 1e-9
        if not shortcut:
            assert all(r['region_n'] == len(region) for r in reg)
        rows.append({'case_id': c['case_id'], 'topology': c['topology'], 'n': p.n,
                     'm': m, 'budget': c['budget'], 'seed': c['seed'], 'shortcut': shortcut,
                     'equal_certified_optimum': True, 'censored': False,
                     'potential_region_n': len(region), 'potential_region_m': mk,
                     'retained_node_fraction': None if shortcut else len(region) / p.n,
                     'retained_edge_fraction': None if shortcut else mk / m,
                     'constructed_bool_fraction': None if shortcut else (len(region) + mk) / (p.n + m),
                     'plot_node_fraction': None if shortcut else len(region) / p.n,
                     'full_ms': tf * 1000, 'barr_ms': tr * 1000, 'paired_speed': tf / tr,
                     'common_ms': median(r['common_seconds'] for r in reg) * 1000,
                     'preprocess_ms': median(r['preprocess_seconds'] for r in reg) * 1000,
                     'build_ms': median(r['build_seconds'] for r in reg) * 1000,
                     'solver_ms': median(r['solver_seconds'] for r in reg) * 1000})
    groups = []
    for family in ['grid', 'modular', 'smallworld']:
        for n in [128, 512]:
            all_rows = [r for r in rows if r['topology'] == family and r['n'] == n]
            cp = [r for r in all_rows if not r['shortcut']]
            groups.append({'topology': family, 'n': n, 'cases': len(all_rows), 'cp_required': len(cp),
                           'shortcut': len(all_rows) - len(cp),
                           **{'median_' + key: median(r[key] for r in cp) for key in
                              ['retained_node_fraction', 'retained_edge_fraction', 'constructed_bool_fraction',
                               'full_ms', 'barr_ms', 'paired_speed', 'common_ms', 'preprocess_ms',
                               'build_ms', 'solver_ms']},
                           'sum_case_median_full_seconds': sum(r['full_ms'] for r in all_rows) / 1000,
                           'sum_case_median_barr_seconds': sum(r['barr_ms'] for r in all_rows) / 1000,
                           'ratio_sums_case_medians': sum(r['full_ms'] for r in all_rows) / sum(r['barr_ms'] for r in all_rows),
                           'median_speed_all': median(r['paired_speed'] for r in all_rows),
                           'median_full_ms_all': median(r['full_ms'] for r in all_rows),
                           'median_barr_ms_all': median(r['barr_ms'] for r in all_rows),
                           'spearman_node_speed_cp': spearman(cp, 'retained_node_fraction', 'paired_speed'),
                           'spearman_bool_speed_cp': spearman(cp, 'constructed_bool_fraction', 'paired_speed')})
    eps_cases = read_json('results/epsilon_v2/case_summary.json'); eps_rows = []
    for c in eps_cases:
        raw = read_json(f"results/epsilon_v2/inputs/{c['case_id']}.json")
        old, p = problem(raw['old']), problem(raw['new'])
        methods = raw_by_folder['epsilon_v2'][c['case_id']]
        full, reg = methods['FullCP'][0], methods['BARRCP'][0]
        assert not full['fastpath'] and not reg['fastpath']
        assert full['lower'] == full['upper'] and reg['lower_reduced'] == reg['upper']
        eps = old.energy(old.x0) - mincut_fast(old)[0]
        region = set(anchored_region(p, [i for i in range(p.n) if old.unary[i] != p.unary[i]], c['budget']))
        assert all(reg['x'][i] == p.x0[i] for i in range(p.n) if i not in region)
        for r in [full, reg]:
            assert p.energy(r['x']) == r['upper'] and p.resource(r['x']) <= c['budget']
        delta = reg['upper'] - full['upper']
        assert eps == c['old_epsilon'] > 0 and delta == c['actual_loss'] and 0 <= delta <= eps
        eps_rows.append({'case_id': c['case_id'], 'topology': c['topology'], 'budget': c['budget'],
                         'epsilon': eps, 'delta': delta, 'delta_over_epsilon': delta / eps,
                         'full_optimum': full['upper'], 'restricted_optimum': reg['upper'],
                         'n': p.n, 'region_n': len(region), 'full_region': len(region) == p.n,
                         'retained_fraction': len(region) / p.n, 'both_optima_proved': True})
    strata = []
    for name, selected in [('All', eps_rows), ('Full region', [r for r in eps_rows if r['full_region']]),
                           ('Proper region', [r for r in eps_rows if not r['full_region']]),
                           ('B=8', [r for r in eps_rows if r['budget'] == 8]),
                           ('B=16', [r for r in eps_rows if r['budget'] == 16])]:
        strata.append({'stratum': name, 'cases': len(selected), 'zero_loss': sum(r['delta'] == 0 for r in selected),
                       'proper_regions': sum(not r['full_region'] for r in selected),
                       'zero_loss_percent': 100 * sum(r['delta'] == 0 for r in selected) / len(selected)})
    assert [(r['cases'], r['zero_loss']) for r in strata] == [(32,22),(6,6),(26,16),(16,6),(16,16)]
    per_case_timing = []
    for case_id in sorted({r['case_id'] for r in timing_rows}):
        selected = [r for r in timing_rows if r['case_id'] == case_id]
        assert len(selected) == 3
        c = {k: selected[0][k] for k in ['case_id','topology','n','shortcut']}
        for key in selected[0]:
            if key.endswith('_ms'):
                c[key] = sum(r[key] for r in selected) / 3
        per_case_timing.append(c)
    timing_groups = []
    for family in ['grid', 'modular', 'smallworld']:
        for n in [128, 512]:
            for scope in ['all', 'not_shortcut']:
                selected = [r for r in timing_rows if r['topology'] == family and r['n'] == n
                            and (scope == 'all' or not r['shortcut'])]
                g = {'topology': family, 'n': n, 'scope': scope, 'calls_per_method': len(selected),
                     'cases': len(selected) // 3}
                for key in selected[0]:
                    if key.endswith('_ms'):
                        g['sum_' + key] = sum(r[key] for r in selected)
                        g['mean_' + key] = g['sum_' + key] / len(selected)
                assert abs(sum(g['mean_saving_' + k + '_ms'] for k in ['common','preprocess','build','solver','other']) - g['mean_saving_total_ms']) < 1e-8
                timing_groups.append(g)
    # Postprocess bounds only: never edit source calls or infer faster timing.
    certificate_rows = []
    stages = ['holdout_v2','holdout_extension_v2','epsilon_v2','ablation_weighted_v3',
              'scale_holdout_v4','core_holdout_v4','route_comparison_v5',
              'public_comparison_v5','core_repeats_v6_completed']
    for stage in stages:
        path = ROOT / 'results' / stage / 'solutions.jsonl'
        source_hashes[str(path.relative_to(ROOT))] = sha(path)
        cache = {}
        for line in path.read_text().splitlines():
            record = json.loads(line)
            if record['method'] not in ('FullCP','BARRCP','HopCP'):
                continue
            case_id = record['case_id']
            if case_id not in cache:
                raw = read_json(f'results/{stage}/inputs/{case_id}.json')
                new = problem(raw['new']); v = mincut_fast(new)[0]
                cache[case_id] = new, v
            new, v = cache[case_id]
            if record.get('unconstrained_value') is not None:
                assert record['unconstrained_value'] == v
            eps = record['old_epsilon'] or 0
            full_region = record['region_n'] == new.n
            lower = merge_global_lower_bound(v, record['lower_reduced'], eps, full_region)
            assert record['lower'] <= lower <= record['upper']
            if record['method'] != 'FullCP' and not record['fastpath']:
                assert abs(record['region_ratio'] - record['region_n'] / new.n) < 1e-10
            certificate_rows.append({'stage': stage, 'case_id': case_id, 'method': record['method'],
                'repeat': record['repeat'], 'shortcut': record['fastpath'], 'full_region': full_region,
                'epsilon': eps, 'unconstrained_value': v, 'restricted_lower': record['lower_reduced'],
                'upper': record['upper'], 'original_lower': record['lower'], 'derived_lower': lower,
                'original_gap': record['upper'] - record['lower'], 'derived_gap': record['upper'] - lower,
                'original_status': record['status'], 'derived_status': 'OPTIMAL' if lower == record['upper'] else record['status'],
                'newly_closed': record['lower'] < record['upper'] == lower})
    cert_groups = []
    for stage in stages:
        for method in sorted({r['method'] for r in certificate_rows if r['stage'] == stage}):
            selected = [r for r in certificate_rows if r['stage'] == stage and r['method'] == method]
            cert_groups.append({'stage': stage, 'method': method, 'calls': len(selected),
                'original_closed': sum(r['original_gap'] == 0 for r in selected),
                'derived_closed': sum(r['derived_gap'] == 0 for r in selected),
                'lower_strengthened': sum(r['derived_lower'] > r['original_lower'] for r in selected),
                'max_original_gap': max(r['original_gap'] for r in selected),
                'max_derived_gap': max(r['derived_gap'] for r in selected)})
    eps_summary = {'cases': len(eps_rows), 'zero_loss': sum(r['delta'] == 0 for r in eps_rows),
                   'positive_loss': sum(r['delta'] > 0 for r in eps_rows),
                   'tight': sum(r['delta'] == r['epsilon'] for r in eps_rows),
                   'zero_loss_percent': 100 * sum(r['delta'] == 0 for r in eps_rows) / len(eps_rows),
                   'epsilon': quantiles([r['epsilon'] for r in eps_rows]),
                   'absolute_delta': quantiles([r['delta'] for r in eps_rows]),
                   'ratio_all': quantiles([r['delta_over_epsilon'] for r in eps_rows]),
                   'ratio_positive': quantiles([r['delta_over_epsilon'] for r in eps_rows if r['delta'] > 0])}
    assert eps_summary['zero_loss'] == 22 and eps_summary['tight'] == 3
    summary = {'main_cases': len(rows), 'main_cp_required': sum(not r['shortcut'] for r in rows),
               'main_shortcuts': sum(r['shortcut'] for r in rows), 'main_censored': 0, 'groups': groups,
               'epsilon': eps_summary,
               'epsilon_strata': strata, 'timing_groups': timing_groups, 'certificate_groups': cert_groups,
               'scope': 'Descriptive paired medians of original three-timing 480-case cohort. No rerun or causal/time-to-target claim. Shortcuts occupy a separate marker band; no region or CP model built. Censored scale/core stages remain in separate manuscript tables.',
               'model_size': 'Before presolve: n+m Boolean variables, one label and one cut variable. Reduced count |K|+|E[K]|; crossing edges are absorbed into unaries.',
               'quantiles': 'NumPy linear interpolation; all repeats summarized within each case first.'}
    write_csv(out / 'timing_components_calls.csv', timing_rows)
    write_csv(out / 'timing_components_cases.csv', per_case_timing)
    write_csv(out / 'timing_components_groups.csv', timing_groups)
    write_csv(out / 'derived_certificates.csv', certificate_rows)
    write_csv(out / 'derived_certificate_groups.csv', cert_groups)
    write_csv(out / 'epsilon_strata.csv', strata)
    for name, value in [('summary.json', summary), ('groups.json', groups), ('source_hashes.json', source_hashes)]:
        (out / name).write_text(json.dumps(value, indent=2) + '\n')
    write_csv(out / 'geometry_cases.csv', rows); write_csv(out / 'epsilon_cases.csv', eps_rows)
    write_csv(out / 'geometry_groups.csv', groups)
    (out / 'builder.py').write_bytes(Path(__file__).read_bytes())
    labels = {'grid': 'Grid', 'modular': 'Modular', 'smallworld': 'Small-world'}
    table = [f"{labels[g['topology']]}, {g['n']} & {g['cp_required']}/{g['cases']} & "
             f"{100*g['median_retained_node_fraction']:.1f}/{100*g['median_constructed_bool_fraction']:.1f} & "
             f"{g['median_full_ms']:.1f}/{g['median_barr_ms']:.1f} & "
             f"{g['median_paired_speed']:.2f}/{g['median_speed_all']:.2f} " + r'\\' for g in groups]
    (out / 'main_rows_v11.tex').write_text('\n'.join(table) + '\n')
    print(json.dumps({'main': [len(rows), summary['main_cp_required'], summary['main_shortcuts']],
                      'cumulative': [(g['topology'], g['n'], g['ratio_sums_case_medians']) for g in groups], 'epsilon_strata': strata, 'cert_changed': [g for g in cert_groups if g['lower_strengthened']] }, indent=2))


if __name__ == '__main__':
    main()
