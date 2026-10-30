"""Controlled anchored bisection core with a dominated positive-cost tail.

This is a synthetic optimization stress family, not an industrial dataset.
The old all-zero plan is uniquely optimal. After changing only vertex 0,
repair induces a near-bisection problem on a cycle-plus-random-matching core.
The remote tail tests preprocessing; it does not make the core search harder.
"""
from dataclasses import dataclass, asdict
from random import Random
from .core import Problem


@dataclass(frozen=True)
class StressSetting:
    n: int = 1024
    core_size: int = 64
    seed: int = 600


def generate_stress(s):
    c=s.core_size
    assert c>=4 and c%2==0 and s.n>=c+2
    rng=Random(s.seed)
    pairs={}
    def edge(i,j,w):
        i,j=sorted((i,j));pairs[i,j]=w
    # Random matching duplicates with cycle edges are merged, not rejected.
    for i in range(1,c+1):
        edge(i,1+i%c,1)
        edge(0,i,3)
    permutation=list(range(1,c+1));rng.shuffle(permutation)
    for i in range(0,c,2):edge(permutation[i],permutation[i+1],1)
    for i in range(c,s.n-1):edge(i,i+1,1)
    old_unary=[(0,4*c+1)]+[(0,-1)]*c+[(0,10)]*(s.n-c-1)
    new_unary=old_unary.copy();new_unary[0]=(0,-4*c)
    edges=tuple((i,j,w) for (i,j),w in sorted(pairs.items()))
    x0=(0,)*s.n;r=(1,)*s.n
    old=Problem(tuple(old_unary),edges,x0,r)
    new=Problem(tuple(new_unary),edges,x0,r)
    return old,new,{'anchors':(0,),'old_epsilon':0,'budget':1+c//2,'setting':asdict(s),
                    'description':'cycle plus merged random matching; anchor star weight3; core unary(0,-1); tail unary(0,10); fixed graph; only anchor unary changes'}
