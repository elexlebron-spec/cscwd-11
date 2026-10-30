"""Audit all solutions, keep censored calls, and avoid speed claims on timeouts."""
from collections import defaultdict,Counter
import hashlib
import json
from pathlib import Path
from statistics import median
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from barr.core import Problem


def summarize(folder):
    path=Path(folder);meta=json.loads((path/'completion.json').read_text())
    rows=[json.loads(line) for line in (path/'solutions.jsonl').read_text().splitlines()]
    bycase=defaultdict(lambda:defaultdict(list));inputs={}
    for r in rows:
        cid=r['case_id']
        if cid not in inputs:
            raw=json.loads((path/'inputs'/f'{cid}.json').read_text())
            assert hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()==r['input_sha256']
            q=raw['new'];inputs[cid]=Problem(tuple(map(tuple,q['unary'])),tuple(map(tuple,q['edges'])),tuple(q['x0']),tuple(q['recourse']))
        p=inputs[cid]
        assert p.energy(r['x'])==r['upper'] and p.resource(r['x'])==r['recourse_used']<=r['budget']
        assert r['lower']<=r['upper'] and r['old_epsilon']==0
        if r['status']=='OPTIMAL':assert r['lower']==r['upper']
        bycase[cid][r['method']].append(r)
    cases=[]
    for cid,methods in bycase.items():
        assert set(methods)=={'FullCP','BARRCP'}
        full,region=methods['FullCP'],methods['BARRCP']
        assert len(full)==len(region)==meta['config']['repeats']
        allrows=full+region
        assert max(r['lower'] for r in allrows)<=min(r['upper'] for r in allrows)
        exact=all(r['status']=='OPTIMAL' for r in allrows)
        if exact:assert len({r['upper'] for r in allrows})==1
        f,b=full[0],region[0]
        group=f.get('topology','core'+str(f.get('core_size','')))
        tf=median(r['total_seconds'] for r in full);tb=median(r['total_seconds'] for r in region)
        cases.append({'case_id':cid,'n':f['n'],'family':group,'seed':f['seed'],
                      'budget':f['budget'],'anchors':f.get('anchors',1),'core_size':f.get('core_size'),
                      'fastpath':f['fastpath'],'exact_pair':exact,'ratio_exact_only':tf/tb if exact else None,
                      'full_s':tf,'barr_s':tb,'region_fraction':f['geodesic_region_n']/f['n'],
                      'full_optimal':all(r['status']=='OPTIMAL' for r in full),
                      'barr_optimal':all(r['status']=='OPTIMAL' for r in region),
                      'full_gap':max(r['upper']-r['lower'] for r in full),
                      'barr_gap':max(r['upper']-r['lower'] for r in region),
                      'full_build_s':median(r['build_seconds'] for r in full),
                      'barr_build_s':median(r['build_seconds'] for r in region),
                      'full_solver_s':median(r['solver_seconds'] for r in full),
                      'barr_solver_s':median(r['solver_seconds'] for r in region),
                      'full_branches':max(r['branches'] for r in full),
                      'barr_branches':max(r['branches'] for r in region),
                      'global_lower':max(r['lower'] for r in allrows),'global_upper':min(r['upper'] for r in allrows),
                      'proven_binding':max(r['lower'] for r in allrows)>f['unconstrained_value'],
                      'greedy_proven_suboptimal':min(r['upper'] for r in allrows)<f['greedy_upper']})
    assert len(cases)==meta['completed_cases']
    groups=[]
    for family,n in sorted({(c['family'],c['n']) for c in cases}):
        selected=[c for c in cases if c['family']==family and c['n']==n]
        active=[c for c in selected if not c['fastpath']]
        timed=[c for c in active if c['exact_pair']]
        groups.append({'family':family,'n':n,'cases':len(selected),'CP_required':len(active),
                       'full_solved':sum(c['full_optimal'] for c in selected),'barr_solved':sum(c['barr_optimal'] for c in selected),
                       'all_median_full_s':median(c['full_s'] for c in selected),'all_median_barr_s':median(c['barr_s'] for c in selected),
                       'CP_median_full_s':median(c['full_s'] for c in active) if active else None,
                       'CP_median_barr_s':median(c['barr_s'] for c in active) if active else None,
                       'CP_median_full_build_s':median(c['full_build_s'] for c in active) if active else None,
                       'CP_median_barr_build_s':median(c['barr_build_s'] for c in active) if active else None,
                       'CP_median_full_solver_s':median(c['full_solver_s'] for c in active) if active else None,
                       'CP_median_barr_solver_s':median(c['barr_solver_s'] for c in active) if active else None,
                       'CP_median_region_fraction':median(c['region_fraction'] for c in active) if active else None,
                       'full_max_gap':max(c['full_gap'] for c in selected),'barr_max_gap':max(c['barr_gap'] for c in selected),
                       'exact_CP_pairs':len(timed),'exact_CP_median_speed':median(c['ratio_exact_only'] for c in timed) if timed else None,
                       'all_max_full_branches':max(c['full_branches'] for c in selected),
                       'all_max_barr_branches':max(c['barr_branches'] for c in selected)})
    report={'cases':len(cases),'calls':len(rows),'solutions_validated':True,'status_counts':dict(Counter(r['status'] for r in rows)),
            'proven_binding':sum(c['proven_binding'] for c in cases),'greedy_proven_suboptimal':sum(c['greedy_proven_suboptimal'] for c in cases),
            'groups':groups,'design':'new seeds; complete Cartesian factors; single timing per method; descriptive medians; no new confidence interval claim',
            'censoring':'All incomplete solves retained. Speed only for paired equal certified optima; deadline calls compared by solved counts and valid absolute gaps.'}
    (path/'case_summary.json').write_text(json.dumps(cases,indent=2));(path/'summary.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    for path in sys.argv[1:]:summarize(path)
