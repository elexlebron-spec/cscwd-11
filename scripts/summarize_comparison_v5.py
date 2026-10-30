"""Validate three-route quality, certificates and time without censoring bias."""
from collections import defaultdict
from fractions import Fraction
import hashlib,json,sys
from pathlib import Path
from statistics import median
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from barr.core import Problem


def summarize(folder):
 p=Path(folder);meta=json.loads((p/'completion.json').read_text());rows=[json.loads(l) for l in (p/'solutions.jsonl').read_text().splitlines()]
 bycase=defaultdict(dict);cases=[]
 for row in rows:
  cid=row['case_id'];raw=json.loads((p/'inputs'/f'{cid}.json').read_text())
  assert hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()==row['input_sha256']
  q=raw['new'];problem=Problem(tuple(map(tuple,q['unary'])),tuple(map(tuple,q['edges'])),tuple(q['x0']),tuple(q['recourse']))
  assert problem.energy(row['x'])==row['upper'] and problem.resource(row['x'])==row['recourse_used']<=row['budget']
  assert row['lower']<=row['upper']
  if row['status']=='OPTIMAL':assert row['lower']==row['upper']
  if row['method']=='LRRepair':
   for t in row['dual_trace']:
    lb=Fraction(t['energy'])+Fraction(t['lambda_num'],t['lambda_den'])*(t['resource']-row['budget'])
    assert lb==Fraction(t['lower_num'],t['lower_den'])
  assert row['method'] not in bycase[cid];bycase[cid][row['method']]=row
 for cid,methods in bycase.items():
  assert set(methods)=={'FullCP','BARRCP','LRRepair'}
  low=max(r['lower'] for r in methods.values());high=min(r['upper'] for r in methods.values());assert low<=high
  exacts=[r['upper'] for r in methods.values() if r['lower']==r['upper']]
  assert len(set(exacts))<=1
  reference=exacts[0] if exacts else None
  f=methods['FullCP'];b=methods['BARRCP'];l=methods['LRRepair']
  case={'case_id':cid,'suite':f['suite'],'family':f.get('family'),'project':f.get('project'),'hours':f.get('hours'),
        'n':f['n'],'budget':f['budget'],'seed':f['seed'],'fastpath':f['fastpath'],
        'region_fraction':f['geodesic_region_n']/f['n'],'global_lower':low,'global_upper':high,
        'reference_optimum':reference,'CP_pair_exact':f['status']==b['status']=='OPTIMAL',
        'CP_speed':f['total_seconds']/b['total_seconds'] if f['status']==b['status']=='OPTIMAL' else None,
        'methods':{name:{'time':r['total_seconds'],'upper':r['upper'],'lower':r['lower'],'gap':r['upper']-r['lower'],
                         'certified':r['upper']==r['lower'],'loss_to_best':r['upper']-high,
                         'loss_to_optimum':r['upper']-reference if reference is not None else None} for name,r in methods.items()}}
  cases.append(case)
 assert len(cases)==meta['completed_cases']
 if cases[0]['suite']=='public':keys=sorted({(c['project'],c['hours']) for c in cases});key=lambda c:(c['project'],c['hours'])
 else:keys=sorted({(c['family'],c['n']) for c in cases});key=lambda c:(c['family'],c['n'])
 groups=[]
 for pair in keys:
  subset=[c for c in cases if key(c)==pair];active=[c for c in subset if not c['fastpath']];exact=[c for c in active if c['CP_pair_exact']]
  group={'key':list(pair),'cases':len(subset),'n':subset[0]['n'],'CP_required':len(active),
         'CP_region_fraction':median(c['region_fraction'] for c in active) if active else None,
         'CP_exact_speed':median(c['CP_speed'] for c in exact) if exact else None,'CP_exact_pairs':len(exact),'methods':{}}
  for name in ['FullCP','BARRCP','LRRepair']:
   chosen=[c['methods'][name] for c in subset]
   group['methods'][name]={'certified':sum(c['certified'] for c in chosen),'median_s':median(c['time'] for c in chosen),
     'max_gap':max(c['gap'] for c in chosen),'median_gap':median(c['gap'] for c in chosen),
     'max_loss_to_best':max(c['loss_to_best'] for c in chosen),
     'reference_cases':sum(c['loss_to_optimum'] is not None for c in chosen),
     'max_loss_to_optimum':max((c['loss_to_optimum'] for c in chosen if c['loss_to_optimum'] is not None),default=None),
     'matches_proven_optimum':sum(c['loss_to_optimum']==0 for c in chosen)}
  groups.append(group)
 report={'cases':len(cases),'calls':len(rows),'solutions_validated':True,'all_certificate_intersections_valid':True,
         'jointly_certified_optima_agree':True,'groups':groups,'scope':'New single timing per method per case, rotating method order. Descriptive only; retain all incomplete calls. LR feasible quality is not compared to exact CP quality as equal.'}
 (p/'case_summary.json').write_text(json.dumps(cases,indent=2)+'\n');(p/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':
 for directory in sys.argv[1:]:summarize(directory)
