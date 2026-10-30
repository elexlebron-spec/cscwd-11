"""Large-size and hard-core experiments. Retain every case and censored solve."""
import argparse
import csv
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
from itertools import product
import json
from pathlib import Path
import platform
import shutil
import sys
import ortools
from barr.core import Problem,anchored_region
from barr.cpsat import solve_cpsat,solve_repair_cpsat
from barr.generate_v2 import Setting,generate
from barr.stress import StressSetting,generate_stress
from barr.flow import mincut_fast
from barr.baselines import greedy_delta


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--out',required=True)
    args=ap.parse_args();raw=Path(args.config).read_bytes();cfg=json.loads(raw)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False);(out/'inputs').mkdir()
    (out/'config.json').write_bytes(raw)
    manifest={}
    for path in [Path(__file__).resolve(),*sorted(Path('barr').glob('*.py'))]:
        rel=Path(path.name) if path.name=='run_followup.py' else Path('barr')/path.name
        dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
        manifest[str(rel)]=hashlib.sha256(path.read_bytes()).hexdigest()
    meta={'started_utc':datetime.now(timezone.utc).isoformat(),'config':cfg,
          'config_sha256':hashlib.sha256(raw).hexdigest(),'source_sha256':manifest,
          'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'ortools':ortools.__version__,
          'timing':'one worker, equal query target, common mincut shortcut, cold old certificate charged only to BARR, all query preparation/modeling included; soft time limits',
          'selection':'complete Cartesian grid, no outcome rejection; new holdout seeds; censored calls retained'}
    (out/'metadata.json').write_text(json.dumps(meta,indent=2))
    solve_cpsat(Problem(((0,1),),(),(0,),(1,)),0,1)
    names=list(cfg['grid']);count=0;writer=None
    with (out/'solutions.jsonl').open('w') as jf,(out/'runs.csv').open('w',newline='') as cf:
        for index,values in enumerate(product(*(cfg['grid'][k] for k in names))):
            params=dict(zip(names,values))
            if cfg['generator']=='scale':
                s=Setting(**params);old,new,details=generate(s);budget=s.budget
            else:
                s=StressSetting(**params);old,new,details=generate_stress(s);budget=details['budget']
            cid=f'case_{index:04d}';payload={'old':asdict(old),'new':asdict(new)}
            digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
            (out/'inputs'/f'{cid}.json').write_text(json.dumps(payload))
            oldmin,_=mincut_fast(old);eps=old.energy(old.x0)-oldmin
            assert eps==details['old_epsilon']==0
            freevalue,freex=mincut_fast(new);gvalue,_=greedy_delta(new,budget)
            region_n=len(anchored_region(new,details['anchors'],budget))
            for repeat in range(cfg['repeats']):
                order=[False,True] if (index+repeat)%2 else [True,False]
                for regional in order:
                    result=solve_repair_cpsat(old,new,budget,cfg['seconds_per_query'],regional,True,s.seed)
                    row={'case_id':cid,**asdict(s),'budget':budget,'generator':cfg['generator'],
                         'repeat':repeat,'method':'BARRCP' if regional else 'FullCP',
                         'seconds_target':cfg['seconds_per_query'],'input_sha256':digest,
                         'geodesic_region_n':region_n,'greedy_upper':gvalue,
                         'unconstrained_value':freevalue,'unconstrained_recourse':new.resource(freex),
                         **result,'old_epsilon':eps}
                    assert new.energy(row['x'])==row['upper'] and new.resource(row['x'])<=budget
                    row['gap_abs']=row['upper']-row['lower']
                    jf.write(json.dumps(row)+'\n');jf.flush()
                    if writer is None:
                        writer=csv.DictWriter(cf,fieldnames=[k for k in row if k!='x'],extrasaction='ignore');writer.writeheader()
                    writer.writerow(row);cf.flush()
            count+=1
            if count%4==0:print(f'Completed {count} cases ({cfg["generator"]})',flush=True)
    meta.update(completed_cases=count,completed_utc=datetime.now(timezone.utc).isoformat())
    (out/'completion.json').write_text(json.dumps(meta,indent=2))
    print(f'Completed {count} cases at {out}',flush=True)


if __name__=='__main__':main()
