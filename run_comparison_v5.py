"""Fresh three-route comparisons on all V4 cases plus public graph cases."""
import argparse,csv,hashlib,json,platform,random,shutil,sys
from dataclasses import asdict
from datetime import datetime,timezone
from itertools import product
from pathlib import Path
import ortools
from barr.core import Problem,anchored_region
from barr.cpsat import solve_repair_cpsat,solve_cpsat
from barr.flow import mincut_fast
from barr.lagrangian import solve_lagrangian_repair
root=Path(__file__).resolve().parent

def load_problem(q):
    return Problem(tuple(map(tuple,q['unary'])),tuple(map(tuple,q['edges'])),tuple(q['x0']),tuple(q['recourse']))

def public_cases(cfg):
    for project,hours,a,budget,seed in product(cfg['projects'],cfg['windows_hours'],cfg['anchors'],cfg['budgets'],cfg['seeds']):
        graph=json.loads((root/f'data/bath_00621/graphs/{project}_{hours}h.json').read_text())
        n=len(graph['vertices']);rng=random.Random(f'bath-{project}-{hours}-{a}-{budget}-{seed}')
        subs=sorted({v['subsystem'] for v in graph['vertices']});pref={s:i%2 for i,s in enumerate(subs)}
        unary=[]
        for v in graph['vertices']:
            wanted=pref[v['subsystem']];penalty=rng.randint(*cfg['old_unary_penalty'])
            unary.append((penalty*wanted,penalty*(1-wanted)))
        p=Problem(tuple(unary),tuple(map(tuple,graph['edges'])),(0,)*n,tuple(graph['recourse']))
        _,x0=mincut_fast(p);old=Problem(p.unary,p.edges,x0,p.recourse)
        anchors=sorted(rng.sample(range(n),a));costs=[list(c) for c in unary]
        for i in anchors:
            costs[i][x0[i]]+=rng.randint(*cfg['anchor_old_label_increase'])
            costs[i][1-x0[i]]-=rng.randint(*cfg['anchor_other_label_decrease'])
        new=Problem(tuple(map(tuple,costs)),p.edges,x0,p.recourse)
        yield old,new,{'suite':'public','project':project,'hours':hours,'n':n,'m':len(p.edges),'anchors':a,
                       'budget':budget,'seed':seed,'seconds':cfg['seconds_per_query'],'source_case':f'{project}_{hours}h'}

def saved_cases():
    for folder in ['scale_holdout_v4','core_holdout_v4']:
        path=root/'results'/folder
        rows=[json.loads(l) for l in (path/'solutions.jsonl').read_text().splitlines()]
        bycase={r['case_id']:r for r in rows if r['method']=='FullCP'}
        for cid,r in sorted(bycase.items()):
            data=json.loads((path/'inputs'/f'{cid}.json').read_text())
            old,new=load_problem(data['old']),load_problem(data['new'])
            yield old,new,{'suite':'core' if folder.startswith('core') else 'scale',
                 'family':r.get('topology','core'+str(r.get('core_size'))),'n':new.n,'m':len(new.edges),
                 'anchors':r.get('anchors',1),'budget':r['budget'],'seed':r['seed'],
                 'seconds':r['seconds_target'],'source_case':folder+'/'+cid}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--suite',choices=['public','synthetic'],required=True)
    args=ap.parse_args();cfg=json.loads((root/'configs/public_comparison_v5.json').read_text())
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False);(out/'inputs').mkdir()
    (out/'config.json').write_text(json.dumps({'public_config':cfg,'suite':args.suite,'saved_suites':['scale_holdout_v4','core_holdout_v4'],
                                            'methods':cfg['methods'],'repeats':1,'LR_max_bisections':24,'LR_cut_fraction':.65},indent=2))
    sources=[Path(__file__),*sorted((root/'barr').glob('*.py'))];hashes={}
    for p in sources:
        rel=p.relative_to(root);dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        hashes[str(rel)]=hashlib.sha256(p.read_bytes()).hexdigest()
    meta={'started_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':hashes,'config_sha256':hashlib.sha256((out/'config.json').read_bytes()).hexdigest(),
          'python':sys.version,'platform':platform.platform(),'ortools':ortools.__version__,
          'design':'All saved V4 cases, or every new public Cartesian case; fresh single timings with rotating method order; no outcome-based rejection.',
          'timing':'Same query cap and new-mincut shortcut; BARR includes cold old certification. LR has rational adaptive cut bounds plus feasible primal repair, no CP calls. All stages/preparation timed; soft limits.'}
    (out/'metadata.json').write_text(json.dumps(meta,indent=2));solve_cpsat(Problem(((0,1),),(),(0,),(1,)),0,1)
    cases=public_cases(cfg) if args.suite=='public' else saved_cases();count=0;writer=None
    with (out/'solutions.jsonl').open('w') as jf,(out/'runs.csv').open('w',newline='') as cf:
        for k,(old,new,detail) in enumerate(cases):
            cid=f'case_{k:04d}';payload={'old':asdict(old),'new':asdict(new)}
            digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
            (out/'inputs'/f'{cid}.json').write_text(json.dumps(payload));order=cfg['methods'][k%3:]+cfg['methods'][:k%3]
            eps=old.energy(old.x0)-mincut_fast(old)[0];assert eps==0
            freevalue,freex=mincut_fast(new);region=len(anchored_region(new,tuple(i for i in range(new.n) if old.unary[i]!=new.unary[i]),detail['budget']))
            for method in order:
                if method=='LRRepair':result=solve_lagrangian_repair(new,detail['budget'],detail['seconds'])
                else:result=solve_repair_cpsat(old,new,detail['budget'],detail['seconds'],method=='BARRCP',True,detail['seed'])
                assert new.energy(result['x'])==result['upper'] and new.resource(result['x'])<=detail['budget']
                row={'case_id':cid,**detail,'method':method,'repeat':0,'input_sha256':digest,
                     'old_epsilon':eps,'geodesic_region_n':region,'unconstrained_value':freevalue,
                     'unconstrained_recourse':new.resource(freex),**result}
                row['gap_abs']=row['upper']-row['lower'];assert row['gap_abs']>=0
                jf.write(json.dumps(row)+'\n');jf.flush()
                flat={key:val for key,val in row.items() if key not in ('x','dual_trace')}
                if writer is None:
                    fields=['case_id','suite','project','hours','family','n','m','anchors','budget','seed','seconds','source_case','method','repeat','input_sha256','old_epsilon','geodesic_region_n','unconstrained_value','unconstrained_recourse','upper','lower','status','recourse_used','fastpath','total_seconds','gap_abs','cut_calls','dual_seconds','recovery_seconds','common_seconds','preprocess_seconds','build_seconds','solver_seconds','branches','conflicts','region_n','region_ratio','lower_reduced']
                    writer=csv.DictWriter(cf,fieldnames=fields,extrasaction='raise');writer.writeheader()
                writer.writerow(flat);cf.flush()
            count+=1
            if count%6==0:print(f'Completed {count} cases ({args.suite})',flush=True)
    meta.update(completed_cases=count,completed_utc=datetime.now(timezone.utc).isoformat())
    (out/'completion.json').write_text(json.dumps(meta,indent=2));print(f'Completed {count} cases',flush=True)
if __name__=='__main__':main()
