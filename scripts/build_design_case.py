"""Compute a fully synthetic responsibility-transfer example by enumeration."""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from barr.core import Problem,anchored_region,brute_force,restrict
from barr.baselines import greedy_delta
from barr.flow import mincut_fast

root=Path(__file__).resolve().parents[1]
out=root/'results/design_case_v4'
out.mkdir(parents=True,exist_ok=False)
names=['Sensor I/O','Signal spec','Schematic','PCB layout','Bring-up','Integration test',
       'Enclosure','CAD','Thermal','Fixture','Safety doc','Release doc']
x0=(0,)*6+(1,)*6
penalties=(2,2,2,1,1,1,2,2,2,2,2,2)
unary=tuple(tuple(penalties[i]*(a!=x0[i]) for a in (0,1)) for i in range(12))
edges=((0,1,10),(0,2,10),(1,2,10),(2,3,8),(3,4,2),(4,5,2),
       (5,6,1),(6,7,4),(6,8,4),(7,8,4),(8,9,3),(9,10,2),(10,11,2))
r=(2,1,2,2,1,1,1,1,2,1,2,1);budget=5
old=Problem(unary,edges,x0,r)
new_u=list(unary);new_u[0]=(40,2)
new=Problem(tuple(new_u),edges,x0,r)
oldmin,_=mincut_fast(old);free,xfree=mincut_fast(new)
value,x=brute_force(new,budget);gval,gx=greedy_delta(new,budget)
region=anchored_region(new,[0],budget);p,c,ids=restrict(new,region)
assert oldmin==old.energy(x0)==1
assert brute_force(p,budget)[0]+c==value
result={'scope':'Fully synthetic illustrative sensor-module design; no industrial observations or measured costs',
        'names':names,'old':{'unary':old.unary,'edges':old.edges,'x0':x0,'recourse':r},
        'new_unary':new.unary,'budget':budget,'anchors':[0],'region':region,
        'old_optimum':oldmin,'new_old_plan_value':new.energy(x0),'epsilon':0,
        'unconstrained':{'value':free,'x':xfree,'resource':new.resource(xfree)},
        'budget_optimum':{'value':value,'x':x,'resource':new.resource(x)},
        'greedy':{'value':gval,'x':gx,'resource':new.resource(gx)},
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(out/'case.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:result[k] for k in ['old_optimum','new_old_plan_value','region','unconstrained','budget_optimum','greedy']},indent=2))
