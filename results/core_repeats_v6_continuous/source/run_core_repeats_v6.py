"""Frozen repeated timings of every saved difficult-core case, without new inputs."""
import argparse,csv,hashlib,json,os,platform,random,shutil,sys,time
from datetime import datetime,timezone
from pathlib import Path
import ortools
from barr.core import Problem
from barr.cpsat import solve_repair_cpsat,solve_cpsat
from barr.flow import mincut_fast
from barr.timing import query_clock,CLOCK_NAME
ROOT=Path(__file__).resolve().parent

def now(): return datetime.now(timezone.utc).isoformat()
def problem(q): return Problem(tuple(map(tuple,q['unary'])),tuple(map(tuple,q['edges'])),tuple(q['x0']),tuple(q['recourse']))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',default='configs/core_repeats_v6.json');ap.add_argument('--out',required=True)
    args=ap.parse_args();config_path=ROOT/args.config;cfg=json.loads(config_path.read_text());src=ROOT/cfg['source_folder']
    rows=[json.loads(l) for l in (src/'solutions.jsonl').read_text().splitlines()]
    base={r['case_id']:r for r in rows if r['method']=='FullCP'};assert len(base)==cfg['expected_cases']
    cases=[]
    for cid,r in sorted(base.items()):
        payload=json.loads((src/'inputs'/f'{cid}.json').read_text());digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        assert digest==r['input_sha256']
        old,new=problem(payload['old']),problem(payload['new'])
        assert old.energy(old.x0)==mincut_fast(old)[0] and r['seconds_target']==cfg['seconds_per_query']
        cases.append((cid,r,payload,digest,old,new))
    out=ROOT/args.out;out.mkdir(parents=True,exist_ok=False);(out/'inputs').mkdir();shutil.copy2(config_path,out/'config.json')
    hashes={}
    for p in [Path(__file__),config_path,*sorted((ROOT/'barr').glob('*.py'))]:
        rel=p.relative_to(ROOT);dest=out/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        hashes[str(rel)]=hashlib.sha256(p.read_bytes()).hexdigest()
    for cid,r,payload,digest,old,new in cases:
        shutil.copy2(src/'inputs'/f'{cid}.json',out/'inputs'/f'{cid}.json')
    meta={'started_utc':now(),'python':sys.version,'ortools':ortools.__version__,'platform':platform.platform(),'machine':platform.machine(),
          'logical_cpus':os.cpu_count(),'load_average_start':os.getloadavg(),'source_sha256':hashes,
          'config_sha256':hashlib.sha256(config_path.read_bytes()).hexdigest(),
          'scope':'within-session descriptive repeatability; fixed solver seeds; repeated queries are not new independent instances; no attribution of old session differences',
          'awake_protocol':'process-scoped caffeinate -disu; no persistent setting modified; continuous, realtime and suspend-excluding clocks recorded', 'query_clock':CLOCK_NAME }
    (out/'metadata.json').write_text(json.dumps(meta,indent=2));solve_cpsat(Problem(((0,1),),(),(0,),(1,)),0,1)
    count=0;writer=None
    with (out/'solutions.jsonl').open('w') as jf,(out/'runs.csv').open('w',newline='') as cf,(out/'rounds.jsonl').open('w') as rf:
        for rep in range(cfg['repeats']):
            order=list(cases);random.Random(cfg['shuffle_seed_base']+rep).shuffle(order)
            rf.write(json.dumps({'repeat':rep,'started_utc':now(),'load_average':os.getloadavg(),'case_order':[a[0] for a in order]})+'\n');rf.flush()
            for rank,(cid,r,payload,digest,old,new) in enumerate(order):
                methods=cfg['methods'] if (rep+rank)%2==0 else list(reversed(cfg['methods']))
                for mi,method in enumerate(methods):
                    clock_real_start=time.time();clock_mono_start=time.perf_counter();clock_cont_start=query_clock()
                    result=solve_repair_cpsat(old,new,r['budget'],cfg['seconds_per_query'],method=='BARRCP',True,r['seed'])
                    clock_cont=query_clock()-clock_cont_start;clock_mono=time.perf_counter()-clock_mono_start;clock_real=time.time()-clock_real_start
                    result.update(external_monotonic_seconds=clock_mono,external_realtime_seconds=clock_real,external_continuous_seconds=clock_cont,suspend_clock_delta_seconds=clock_cont-clock_mono,clock_consistent=(result['solver_seconds']<=clock_cont+.1 and abs(clock_real-clock_cont)<=.1 and abs(result['total_seconds']-clock_cont)<=.1))
                    assert new.energy(result['x'])==result['upper'] and new.resource(result['x'])<=r['budget']
                    row={'case_id':cid,'n':new.n,'core_size':r['core_size'],'seed':r['seed'],'solver_seed':r['seed'],'budget':r['budget'],
                         'repeat':rep,'order_rank':rank,'method_order':mi,'method':method,'seconds_target':cfg['seconds_per_query'],
                         'input_sha256':digest,'finished_utc':now(),**result}
                    row['gap_abs']=row['upper']-row['lower'];assert row['gap_abs']>=0
                    jf.write(json.dumps(row)+'\n');jf.flush();flat={k:v for k,v in row.items() if k!='x'}
                    if writer is None: writer=csv.DictWriter(cf,fieldnames=list(flat));writer.writeheader()
                    writer.writerow(flat);cf.flush();count+=1
            print(f'Completed round {rep+1}/{cfg["repeats"]}: {count} calls',flush=True)
    meta.update(completed_calls=count,completed_utc=now(),load_average_end=os.getloadavg())
    assert count==cfg['expected_cases']*cfg['repeats']*len(cfg['methods'])
    (out/'completion.json').write_text(json.dumps(meta,indent=2))
if __name__=='__main__':main()
