"""Finish only missing planned queries after a tool/process interruption."""
import csv,hashlib,json,os,random,shutil,time
from pathlib import Path
from datetime import datetime,timezone
from barr.core import Problem
from barr.cpsat import solve_cpsat,solve_repair_cpsat
from barr.timing import query_clock,CLOCK_NAME
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'results/core_repeats_v6_confirmed_awake';OUT=ROOT/'results/core_repeats_v6_resume'
def now():return datetime.now(timezone.utc).isoformat()
def p(q):return Problem(tuple(map(tuple,q['unary'])),tuple(map(tuple,q['edges'])),tuple(q['x0']),tuple(q['recourse']))
cfg=json.loads((SRC/'config.json').read_text());meta=json.loads((SRC/'metadata.json').read_text())
for rel,digest in meta['source_sha256'].items():
 if rel.startswith('barr/'):
  assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest
prior=[json.loads(l) for l in (SRC/'solutions.jsonl').read_text().splitlines()]
assert len(prior)==261 and all(r['clock_consistent'] and r['suspend_clock_delta_seconds']<=.1 for r in prior)
seen={(r['case_id'],r['repeat'],r['method']) for r in prior};assert len(seen)==261
base={r['case_id']:r for r in [json.loads(l) for l in (ROOT/'results/core_holdout_v4/solutions.jsonl').read_text().splitlines()] if r['method']=='FullCP'}
cases=[]
for cid,r in sorted(base.items()):
 payload=json.loads((SRC/'inputs'/f'{cid}.json').read_text());digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest();assert digest==r['input_sha256']
 cases.append((cid,r,digest,p(payload['old']),p(payload['new'])))
OUT.mkdir(exist_ok=False);shutil.copy2(SRC/'config.json',OUT/'config.json')
files=[Path(__file__),*sorted((ROOT/'barr').glob('*.py'))];hashes={}
for f in files:
 rel=f.relative_to(ROOT);dest=OUT/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest);hashes[str(rel)]=hashlib.sha256(f.read_bytes()).hexdigest()
metadata={'started_utc':now(),'completed_prior_calls':261,'planned_remaining':139,'source_sha256':hashes,'query_clock':CLOCK_NAME,'reason':'tool turn interrupted; prior process no longer active; completed rows retained; any unlogged in-flight call is executed as missing, not selected by outcome'}
(OUT/'metadata.json').write_text(json.dumps(metadata,indent=2));solve_cpsat(Problem(((0,1),),(),(0,),(1,)),0,1)
count=0;writer=None
with (OUT/'solutions.jsonl').open('w') as jf,(OUT/'runs.csv').open('w',newline='') as cf:
 for rep in range(cfg['repeats']):
  order=list(cases);random.Random(cfg['shuffle_seed_base']+rep).shuffle(order)
  for rank,(cid,r,digest,old,new) in enumerate(order):
   methods=cfg['methods'] if (rep+rank)%2==0 else list(reversed(cfg['methods']))
   for mi,method in enumerate(methods):
    if (cid,rep,method) in seen:continue
    cr=time.time();cm=time.perf_counter();cc=query_clock()
    result=solve_repair_cpsat(old,new,r['budget'],5,method=='BARRCP',True,r['seed'])
    ec=query_clock()-cc;em=time.perf_counter()-cm;er=time.time()-cr
    result.update(external_monotonic_seconds=em,external_realtime_seconds=er,external_continuous_seconds=ec,suspend_clock_delta_seconds=ec-em,clock_consistent=(result['solver_seconds']<=ec+.1 and abs(er-ec)<=.1 and abs(result['total_seconds']-ec)<=.1))
    row={'case_id':cid,'n':new.n,'core_size':r['core_size'],'seed':r['seed'],'solver_seed':r['seed'],'budget':r['budget'],'repeat':rep,'order_rank':rank,'method_order':mi,'method':method,'seconds_target':5.,'input_sha256':digest,'finished_utc':now(),**result}
    row['gap_abs']=row['upper']-row['lower'];assert row['gap_abs']>=0 and new.energy(row['x'])==row['upper'] and new.resource(row['x'])<=r['budget']
    jf.write(json.dumps(row)+'\n');jf.flush();flat={k:v for k,v in row.items() if k!='x'}
    if writer is None:writer=csv.DictWriter(cf,fieldnames=list(flat));writer.writeheader()
    writer.writerow(flat);cf.flush();count+=1
    if not row['clock_consistent'] or row['suspend_clock_delta_seconds']>.1:
     (OUT/'interruption.json').write_text(json.dumps({'completed_calls':count,'reason':'clock gate failed; rows retained'}));raise RuntimeError('Clock interruption')
  if count:print(f'Finished planned round {rep+1}: {count}/139 missing calls',flush=True)
assert count==139
metadata.update(completed_calls=count,completed_utc=now());(OUT/'completion.json').write_text(json.dumps(metadata,indent=2))
