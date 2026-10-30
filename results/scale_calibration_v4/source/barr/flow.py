"""C++ OR-Tools max-flow backend. Classical backend, not a research contribution."""
from .core import Problem


def mincut_fast(p: Problem, multiplier=0, fixed=None):
    from ortools.graph.python import max_flow
    assert isinstance(multiplier, int) and multiplier >= 0
    fixed = dict(fixed or {})
    free = [i for i in range(p.n) if i not in fixed]
    pos = {v: k for k, v in enumerate(free)}
    unary = [[p.unary[i][v] + multiplier * p.recourse[i] * (v != p.x0[i])
              for v in (0, 1)] for i in free]
    constant = sum(p.unary[i][v] + multiplier * p.recourse[i] * (v != p.x0[i])
                   for i, v in fixed.items())
    edges = []
    for i, j, w in p.edges:
        if i in fixed and j in fixed:
            constant += w * (fixed[i] != fixed[j])
        elif i in fixed:
            for v in (0, 1):
                unary[pos[j]][v] += w * (v != fixed[i])
        elif j in fixed:
            for v in (0, 1):
                unary[pos[i]][v] += w * (v != fixed[j])
        else:
            edges.append((pos[i], pos[j], w))
    s, t = len(free), len(free) + 1
    flow = max_flow.SimpleMaxFlow()
    for k, (c0, c1) in enumerate(unary):
        shift = min(c0, c1)
        constant += shift
        flow.add_arc_with_capacity(s, k, c1 - shift)
        flow.add_arc_with_capacity(k, t, c0 - shift)
    # Also register both terminal nodes when all variables were eliminated.
    flow.add_arc_with_capacity(s, t, 0)
    for i, j, w in edges:
        flow.add_arc_with_capacity(i, j, w)
        flow.add_arc_with_capacity(j, i, w)
    status = flow.solve(s, t)
    if status != flow.OPTIMAL:
        raise RuntimeError(f"max-flow failed with status {status}")
    source = set(flow.get_source_side_min_cut())
    x = list(p.x0)
    for i, v in fixed.items():
        x[i] = v
    for k, i in enumerate(free):
        x[i] = 0 if k in source else 1
    objective = int(flow.optimal_flow()) + constant
    assert p.energy(x) + multiplier * p.resource(x) == objective
    return objective, tuple(x)
