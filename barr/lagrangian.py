"""Classical Lagrangian cuts plus primal budget repair. No CP-SAT calls.

Integer-scaled rational multipliers give exact cut values and valid integer
lower bounds. Finite multiplier search is not claimed to solve the dual.
"""
from fractions import Fraction
from heapq import heappop, heappush
from .timing import query_clock as perf_counter
from .core import Problem
from .flow import mincut_fast


def rational_cut(p, lam):
    lam = Fraction(lam)
    a, b = lam.numerator, lam.denominator
    q = Problem(tuple(tuple(b*c+a*r*(v!=old) for v,c in enumerate(cost))
                      for cost,r,old in zip(p.unary,p.recourse,p.x0)),
                tuple((i,j,b*w) for i,j,w in p.edges), p.x0, p.recourse)
    value,x = mincut_fast(q)
    return Fraction(value,b),x


def _adjacency(p):
    adj=[[] for _ in range(p.n)]
    for i,j,w in p.edges:adj[i].append((j,w));adj[j].append((i,w))
    return adj


def _delta(p,adj,x,i):
    return p.unary[i][1-x[i]]-p.unary[i][x[i]]+sum(w*(1 if x[i]==x[j] else -1) for j,w in adj[i])


def restore_budget(p,x,budget,deadline=float('inf')):
    """Revert changed vertices by minimum energy increase per freed resource."""
    x=list(x);used=p.resource(x);adj=_adjacency(p);version=[0]*p.n;heap=[]
    def push(i):
        if x[i]!=p.x0[i]:
            d=_delta(p,adj,x,i)
            heappush(heap,(Fraction(d,p.recourse[i]),d,i,version[i]))
    for i in range(p.n):push(i)
    while used>budget:
        if perf_counter()>=deadline:return p.x0
        _,_,i,v=heappop(heap)
        if v!=version[i] or x[i]==p.x0[i]:continue
        x[i]^=1;used-=p.recourse[i];version[i]+=1
        for j,_ in adj[i]:version[j]+=1;push(j)
    return tuple(x)


def feasible_descent(p,x,budget,deadline=float('inf')):
    """Single-flip improvement from any feasible primal candidate."""
    x=list(x);used=p.resource(x);assert used<=budget;adj=_adjacency(p)
    while perf_counter()<deadline:
        best=None
        for i in range(p.n):
            resource=used+(p.recourse[i] if x[i]==p.x0[i] else -p.recourse[i])
            if resource>budget:continue
            d=_delta(p,adj,x,i)
            key=(Fraction(d,p.recourse[i]),d,i)
            if d<0 and (best is None or key<best[0]):best=(key,i,resource)
        if best is None:break
        _,i,used=best;x[i]^=1
    return tuple(x)


def solve_lagrangian_repair(p,budget,seconds=3,max_bisections=24):
    start=perf_counter();deadline=start+seconds;cut_deadline=start+.65*seconds
    best=p.x0;upper=p.energy(best);lower=None;calls=0;trace=[];infeasible=[]
    def evaluate(lam):
        nonlocal best,upper,lower,calls
        v,x=rational_cut(p,lam);calls+=1;used=p.resource(x);energy=p.energy(x)
        lb=v-lam*budget;lower=lb if lower is None else max(lower,lb)
        trace.append({'lambda_num':lam.numerator,'lambda_den':lam.denominator,
                      'energy':energy,'resource':used,'lower_num':lb.numerator,'lower_den':lb.denominator})
        if used<=budget and energy<upper:best,upper=x,energy
        elif used>budget:infeasible.append((used-budget,energy,x))
        return used
    lo=Fraction(0);used=evaluate(lo)
    if used<=budget:
        return {'x':best,'upper':upper,'lower':upper,'status':'OPTIMAL','recourse_used':p.resource(best),
                'fastpath':True,'cut_calls':calls,'dual_trace':trace,'total_seconds':perf_counter()-start,
                'dual_seconds':perf_counter()-start,'recovery_seconds':0.0}
    hi=Fraction(1)
    while perf_counter()<cut_deadline:
        used=evaluate(hi)
        if lower>=upper:break
        if used<=budget:break
        lo=hi;hi*=2
    if used<=budget and lower<upper:
        for _ in range(max_bisections):
            if perf_counter()>=cut_deadline or lower>=upper:break
            mid=(lo+hi)/2;used=evaluate(mid)
            if used>budget:lo=mid
            else:hi=mid
    dual_end=perf_counter()
    # Improve the best feasible cut and the original hint; restore the closest
    # infeasible cut. These deterministic candidates do not use exact optima.
    starts=[best,p.x0]
    if infeasible:
        starts.append(restore_budget(p,min(infeasible,key=lambda z:(z[0],z[1]))[2],budget,deadline))
    for x in starts:
        if perf_counter()>=deadline:break
        x=feasible_descent(p,x,budget,deadline);v=p.energy(x)
        if v<upper:upper,best=v,x
    integer_lower=-((-lower.numerator)//lower.denominator)
    assert integer_lower<=upper and p.resource(best)<=budget
    return {'x':best,'upper':upper,'lower':integer_lower,
            'status':'OPTIMAL' if integer_lower==upper else 'FEASIBLE',
            'recourse_used':p.resource(best),'fastpath':False,'cut_calls':calls,
            'dual_trace':trace,'dual_seconds':dual_end-start,
            'recovery_seconds':perf_counter()-dual_end,'total_seconds':perf_counter()-start}
