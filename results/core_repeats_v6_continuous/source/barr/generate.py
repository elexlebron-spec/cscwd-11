"""Documented synthetic instances, never represented as industrial observations."""
from __future__ import annotations
from random import Random
from .core import Problem, mincut


def generate(n=80, seed=0, topology="chain", shock_count=1, weighted=True):
    rng = Random(seed)
    pairs = set()
    if topology == "chain":
        pairs.update((i, i + 1) for i in range(n - 1))
    elif topology == "grid":
        width = max(2, int(n ** 0.5))
        for i in range(n):
            if i + 1 < n and (i + 1) % width:
                pairs.add((i, i + 1))
            if i + width < n:
                pairs.add((i, i + width))
    elif topology == "smallworld":
        pairs.update((i, i + 1) for i in range(n - 1))
        for _ in range(3 * n):
            i, j = sorted(rng.sample(range(n), 2))
            pairs.add((i, j))
    else:
        raise ValueError(topology)
    edges = tuple((i, j, rng.randint(1, 4)) for i, j in sorted(pairs))
    costs = []
    for i in range(n):
        preferred = (i // 8) % 2
        base = rng.randint(2, 10)
        mismatch = rng.randint(3, 14)
        costs.append(tuple(base + mismatch * (v != preferred) for v in (0, 1)))
    r = tuple(rng.randint(1, 4) if weighted else 1 for _ in range(n))
    temporary = Problem(tuple(costs), edges, (0,) * n, r)
    _, x0 = mincut(temporary)
    old = Problem(tuple(costs), edges, x0, r)
    new_costs = [list(c) for c in costs]
    for i in rng.sample(range(n), min(shock_count, n)):
        new_costs[i][x0[i]] += rng.randint(25, 60)
    new = Problem(tuple(map(tuple, new_costs)), edges, x0, r)
    return old, new
