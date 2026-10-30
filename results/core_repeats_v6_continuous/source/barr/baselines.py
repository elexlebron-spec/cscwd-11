"""Classical baselines with incremental single-flip energy evaluation."""
from .flow import mincut_fast


def greedy_delta(p, budget):
    x = list(p.x0)
    used = 0
    adjacency = [[] for _ in range(p.n)]
    for i, j, w in p.edges:
        adjacency[i].append((j, w))
        adjacency[j].append((i, w))
    while True:
        best = None
        for i in range(p.n):
            trial_used = used + (p.recourse[i] if x[i] == p.x0[i] else -p.recourse[i])
            if trial_used > budget:
                continue
            delta = p.unary[i][1 - x[i]] - p.unary[i][x[i]]
            delta += sum(w * (1 if x[i] == x[j] else -1) for j, w in adjacency[i])
            gain = -delta
            key = (gain / p.recourse[i], gain, -i)
            if gain > 0 and (best is None or key > best[0]):
                best = (key, i, trial_used)
        if best is None:
            assert used == p.resource(x)
            return p.energy(x), tuple(x)
        _, i, used = best
        x[i] ^= 1


def penalty_scan(p, budget, multipliers=(0, 1, 2, 4, 8, 16, 32, 64, 128)):
    upper, xbest = p.energy(p.x0), p.x0
    lower = float("-inf")
    calls = 0
    for lam in multipliers:
        value, x = mincut_fast(p, lam)
        calls += 1
        lower = max(lower, value - lam * budget)
        if p.resource(x) <= budget and p.energy(x) < upper:
            upper, xbest = p.energy(x), x
        if lower >= upper:
            break
    return {"upper": upper, "lower": lower, "x": xbest, "calls": calls}
