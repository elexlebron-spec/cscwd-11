"""Validate all repeated labels/bounds, preserving censored calls and instance clusters."""
import csv,hashlib,json,statistics,sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from barr.core import Problem
def p(q):return Problem(tuple(map(tuple,q['unary'])),tuple(map(tuple,q['edges'])),tuple(q['x0']),tuple(q['recourse']))
def stats(values):
    values=sorted(values);q=statistics.quantiles(values,n=4,method='inclusive')
    return {'median':statistics.median(values),'q1':q[0],'q3':q[2],'min':min(values),'max':max(values)}
def main():
    folder=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'results/core_repeats_v6_completed');cfg=json.loads((folder/'config.json').read_text())
    assert (folder/'completion.json').exists(),'Do not summarize incomplete benchmark'
    rows=[json.loads(s) for s in (folder/'solutions.jsonl').read_text().splitlines()]
    expected=cfg['expected_cases']*cfg['repeats']*len(cfg['methods']);assert len(rows)==expected
    metadata=json.loads((folder/'metadata.json').read_text())
    assert metadata['config_sha256']==hashlib.sha256((folder/'config.json').read_bytes()).hexdigest()
    for rel,digest in metadata['source_sha256'].items():assert hashlib.sha256((folder/'source'/rel).read_bytes()).hexdigest()==digest
    cases={};bycase=defaultdict(list);groups=defaultdict(list);seen=set()
    reference=defaultdict(list)
    for r in [json.loads(s) for s in (ROOT/'results/core_holdout_v4/solutions.jsonl').read_text().splitlines()]:reference[r['input_sha256']].append(r)
    for r in [json.loads(s) for s in (ROOT/'results/route_comparison_v5/solutions.jsonl').read_text().splitlines() if s.strip()]:
        if r['suite']=='core':reference[r['input_sha256']].append(r)
    for r in rows:
        cid=r['case_id'];key=(cid,r['repeat'],r['method']);assert key not in seen;seen.add(key)
        if cid not in cases:
            payload=json.loads((folder/'inputs'/f'{cid}.json').read_text());digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
            cases[cid]=(p(payload['old']),p(payload['new']),digest)
        old,new,digest=cases[cid]
        assert r['input_sha256']==digest and r['seed']==r['solver_seed'] and r['seconds_target']==5
        assert new.energy(r['x'])==r['upper'] and new.resource(r['x'])==r['recourse_used']<=r['budget']
        assert r['lower']<=r['upper'] and r['gap_abs']==r['upper']-r['lower']
        assert not r['fastpath'] and (r['status']=='OPTIMAL')==(r['gap_abs']==0)
        assert all(t['upper']>=r['lower'] and t['lower']<=r['upper'] for t in reference[digest])
        bycase[cid].append(r);groups[(r['n'],r['core_size'],r['method'])].append(r)
    assert len(cases)==cfg['expected_cases']
    case_summary=[]
    for cid,rr in sorted(bycase.items()):
        assert len(rr)==cfg['repeats']*len(cfg['methods'])
        # Every reported interval must contain the common intersection implied by all valid runs.
        allr=rr+reference[rr[0]['input_sha256']];global_l=max(r['lower'] for r in allr);global_u=min(r['upper'] for r in allr)
        assert global_l<=global_u
        row={k:rr[0][k] for k in ['case_id','n','core_size','seed','budget','input_sha256']}
        row['cross_stage_best_lower']=global_l;row['cross_stage_best_upper']=global_u
        for method in cfg['methods']:
            mr=[r for r in rr if r['method']==method];assert {r['repeat'] for r in mr}==set(range(cfg['repeats']))
            row[method]={'closed':sum(r['gap_abs']==0 for r in mr),'attempts':len(mr),'query_seconds':stats([r['total_seconds'] for r in mr]),
                         'gap_median':statistics.median(r['gap_abs'] for r in mr),'gap_max':max(r['gap_abs'] for r in mr),
                         'branches':stats([r['branches'] for r in mr]),'conflicts':stats([r['conflicts'] for r in mr])}
        case_summary.append(row)
    group_summary=[]
    for (n,q,method),rr in sorted(groups.items()):
        cr=[r[method]['closed'] for r in case_summary if r['n']==n and r['core_size']==q]
        row={'n':n,'core_size':q,'method':method,'unique_instances':len(cr),'calls':len(rr),'closed':sum(r['gap_abs']==0 for r in rr),
             'per_instance_closed_min':min(cr),'per_instance_closed_max':max(cr),
             'median_within_case_relative_iqr_percent':statistics.median(100*(r[method]['query_seconds']['q3']-r[method]['query_seconds']['q1'])/r[method]['query_seconds']['median'] for r in case_summary if r['n']==n and r['core_size']==q),
             'pause_affected_calls':sum(r.get('suspend_clock_delta_seconds',0)>.1 for r in rr),
             'query_seconds':stats([r['total_seconds'] for r in rr]),'gap_median':statistics.median(r['gap_abs'] for r in rr),'gap_max':max(r['gap_abs'] for r in rr)}
        group_summary.append(row)
    clock_bad=[{k:r.get(k) for k in ['case_id','repeat','method','solver_seconds','total_seconds','external_monotonic_seconds','external_realtime_seconds','external_continuous_seconds']} for r in rows if (r['solver_seconds']>r['total_seconds']+.1 or r.get('clock_consistent',True) is False)]
    pause_rounds=[r['repeat'] for r in rows if r.get('suspend_clock_delta_seconds',0)>.1 or not r.get('clock_consistent',True)]
    prefix_rounds=min(pause_rounds,default=cfg['repeats']);prefix_groups=[]
    for (n,q,method),rr in sorted(groups.items()):
        pr=[r for r in rr if r['repeat']<prefix_rounds]
        prefix_groups.append({'n':n,'core_size':q,'method':method,'calls':len(pr),'closed':sum(r['gap_abs']==0 for r in pr),'query_seconds':stats([r['total_seconds'] for r in pr]) if pr else None,'gap_max':max((r['gap_abs'] for r in pr),default=None)})
    summary={'clean_prefix_repeats':prefix_rounds,'clean_prefix_calls':prefix_rounds*cfg['expected_cases']*len(cfg['methods']),'clean_prefix_definition':'post hoc first complete rounds before any detected pause; selected by clock flag, not objective or certification; does not replace the planned 10-repeat cohort', 'clean_prefix_groups':prefix_groups,'no_pause_during_logged_queries':not pause_rounds,'execution_segments':len(metadata.get('segments',[])) or 1,'fully_uninterrupted_protocol':not pause_rounds and len(metadata.get('segments',[]))<=1,'clock_audit_passed':not clock_bad,'clock_inconsistent_calls':clock_bad,'cases':len(cases),'calls':len(rows),'repeats_per_case_method':cfg['repeats'],'solutions_validated':True,
             'input_and_source_hashes_verified':True,'all_intervals_mutually_consistent_with_prior_stages':True,
             'design':f"fixed seed per instance, balanced sequential order, {len(metadata.get('segments',[])) or 1} execution segment(s) on one laptop; no independent-instance confidence intervals",
             'quantiles':'statistics.quantiles(n=4, method=inclusive)',
             'timing':'all query totals including censored calls; median/IQR is not uncensored time-to-optimum; no speed ratio claimed on unresolved cores',
             'environment_control':'Background OS load, temperature and power mode not controlled; round load averages recorded; no other benchmark or heavy document build launched by this task',
             'summary_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'continuous_clock_recorded_calls':sum('external_continuous_seconds' in r for r in rows),
             'suspend_delta_above_0_1s_calls':sum(r.get('suspend_clock_delta_seconds',0)>.1 for r in rows),
             'over_target_by_0_25s_calls':sum(r['total_seconds']>r['seconds_target']+.25 for r in rows),
             'groups':group_summary}
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(folder/'case_summary.json').write_text(json.dumps(case_summary,indent=2)+'\n')
    with (folder/'case_repeatability.csv').open('w',newline='') as f:
        out=[]
        for r in case_summary:
            out.append({**{k:r[k] for k in ['case_id','n','core_size','seed']},**{f'{m}_closed_out_of_10':r[m]['closed'] for m in cfg['methods']}})
        writer=csv.DictWriter(f,fieldnames=list(out[0]));writer.writeheader();writer.writerows(out)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
