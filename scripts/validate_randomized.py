from pathlib import Path
import sys,json,hashlib
from random import Random
sys.path.insert(0,str(Path.cwd()))
from barr.core import Problem, brute_force, anchored_region, restrict
from barr.flow import mincut_fast
rng=Random(20261028)
counts={'cases':1200,'epsilon_zero':0,'epsilon_positive':0,'strict_region_loss_cases':0,'violations':0,'seed':20261028}
maxloss=0
for case in range(1200):
 n=rng.randint(2,8)
 edges=tuple((i,j,rng.randint(1,9)) for i in range(n) for j in range(i+1,n) if rng.random()<.25)
 unary=tuple((rng.randint(-3,12),rng.randint(-3,12)) for _ in range(n))
 r=tuple(rng.randint(1,4) for _ in range(n))
 p=Problem(unary,edges,(0,)*n,r)
 opt,xstar=mincut_fast(p)
 x0=xstar if case%2 else tuple(rng.randrange(2) for _ in range(n))
 old=Problem(unary,edges,x0,r)
 newcost=list(unary)
 for i in rng.sample(range(n),rng.randint(1,min(n,3))):
  a,b=unary[i];newcost[i]=(a+rng.randint(-10,10),b+rng.randint(-10,10))
 new=Problem(tuple(newcost),edges,x0,r)
 B=rng.randint(0,min(12,sum(r)))
 anchors=tuple(i for i in range(n) if unary[i]!=new.unary[i])
 region=anchored_region(new,anchors,B)
 reduced,C,ids=restrict(new,region)
 exact,_=brute_force(new,B)
 local,_=brute_force(reduced,B);local+=C
 eps=old.energy(x0)-opt
 assert exact<=local<=exact+eps,(case,exact,local,eps)
 counts['epsilon_zero' if eps==0 else 'epsilon_positive']+=1
 counts['strict_region_loss_cases']+=local>exact
 maxloss=max(maxloss,local-exact)
counts['max_observed_loss']=maxloss
counts['scope']='independent brute-force comparison for full/restricted problems; n=2..8, weighted budgets, bidirectional unary changes, multiple anchors and nonoptimal baselines'
Path('results/randomized_validation_v2.json').write_text(json.dumps(counts,indent=2))
print(json.dumps(counts,indent=2))
