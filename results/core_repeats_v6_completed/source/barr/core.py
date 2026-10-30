from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import product
from .timing import query_clock as perf_counter
import math


@dataclass(frozen=True)
class Problem:
    unary: tuple[tuple[int, int], ...]
    edges: tuple[tuple[int, int, int], ...]
    x0: tuple[int, ...]
    recourse: tuple[int, ...]

    def __post_init__(self):
        n = len(self.unary)
        assert len(self.x0) == len(self.recourse) == n
        assert all(x in (0, 1) for x in self.x0)
        assert all(isinstance(r, int) and r > 0 for r in self.recourse)
        assert all(len(c) == 2 and all(isinstance(v, int) for v in c) for c in self.unary)
        assert all(0 <= i < j < n and isinstance(w, int) and w >= 0 for i, j, w in self.edges)

    @property
    def n(self):
        return len(self.unary)

    def energy(self, x):
        return sum(c[v] for c, v in zip(self.unary, x)) + sum(
            w for i, j, w in self.edges if x[i] != x[j])

    def resource(self, x):
        return sum(r for a, b, r in zip(x, self.x0, self.recourse) if a != b)


class Dinic:
    """Integer max-flow. Reference implementation, not a novel contribution."""
    def __init__(self, n):
        self.g = [[] for _ in range(n)]

    def arc(self, u, v, c):
        assert c >= 0
        self.g[u].append([v, c, len(self.g[v])])
        self.g[v].append([u, 0, len(self.g[u]) - 1])

    def run(self, s, t):
        total = 0
        while True:
            level = [-1] * len(self.g)
            level[s] = 0
            q = deque([s])
            while q:
                u = q.popleft()
                for v, c, _ in self.g[u]:
                    if c and level[v] < 0:
                        level[v] = level[u] + 1
                        q.append(v)
            if level[t] < 0:
                return total, {i for i, d in enumerate(level) if d >= 0}
            it = [0] * len(self.g)

            def send(u, amount):
                if u == t:
                    return amount
                while it[u] < len(self.g[u]):
                    edge = self.g[u][it[u]]
                    v, c, rev = edge
                    if c and level[v] == level[u] + 1:
                        f = send(v, min(amount, c))
                        if f:
                            edge[1] -= f
                            self.g[v][rev][1] += f
                            return f
                    it[u] += 1
                return 0

            max_push = 1 + sum(e[1] for e in self.g[s])
            while (f := send(s, max_push)):
                total += f


def mincut(p: Problem, multiplier: int = 0, fixed=None):
    """Exact min E(x)+multiplier*R(x), with fixed labels eliminated.

    Label 0 is the source side. Unary constants are retained, including negatives.
    """
    assert isinstance(multiplier, int) and multiplier >= 0
    fixed = dict(fixed or {})
    free = [i for i in range(p.n) if i not in fixed]
    pos = {v: k for k, v in enumerate(free)}
    costs = [[p.unary[i][v] + multiplier * p.recourse[i] * (v != p.x0[i])
              for v in (0, 1)] for i in free]
    constant = sum(p.unary[i][v] + multiplier * p.recourse[i] * (v != p.x0[i])
                   for i, v in fixed.items())
    inside = []
    for i, j, w in p.edges:
        if i in fixed and j in fixed:
            constant += w * (fixed[i] != fixed[j])
        elif i in fixed:
            for v in (0, 1):
                costs[pos[j]][v] += w * (v != fixed[i])
        elif j in fixed:
            for v in (0, 1):
                costs[pos[i]][v] += w * (v != fixed[j])
        else:
            inside.append((pos[i], pos[j], w))
    s, t = len(free), len(free) + 1
    flow = Dinic(t + 1)
    for i, (c0, c1) in enumerate(costs):
        shift = min(c0, c1)
        constant += shift
        flow.arc(s, i, c1 - shift)
        flow.arc(i, t, c0 - shift)
    for i, j, w in inside:
        flow.arc(i, j, w)
        flow.arc(j, i, w)
    value, source = flow.run(s, t)
    x = list(p.x0)
    for i, v in fixed.items():
        x[i] = v
    for k, i in enumerate(free):
        x[i] = 0 if k in source else 1
    assert p.energy(x) + multiplier * p.resource(x) == value + constant
    return value + constant, tuple(x)


def anchored_region(p: Problem, anchors, budget):
    """Node-weighted shortest paths, including BOTH path endpoints."""
    adj = [[] for _ in range(p.n)]
    for i, j, w in p.edges:
        if w:  # Zero-weight factors do not transmit interaction.
            adj[i].append(j)
            adj[j].append(i)
    dist = [math.inf] * p.n
    queue = []
    for a in set(anchors):
        dist[a] = p.recourse[a]
        heappush(queue, (dist[a], a))
    while queue:
        d, i = heappop(queue)
        if d != dist[i] or d > budget:
            continue
        for j in adj[i]:
            candidate = d + p.recourse[j]
            if candidate < dist[j] and candidate <= budget:
                dist[j] = candidate
                heappush(queue, (candidate, j))
    return tuple(i for i, d in enumerate(dist) if d <= budget)


def hop_region(p: Problem, anchors, budget):
    """Safe coarse comparator: floor(B/r_min)-1 hops from any anchor.

    Replacing every node cost by r_min can only enlarge the weighted region.
    This is an ablation comparator, not an additional algorithmic contribution.
    """
    if not p.n or budget < min(p.recourse):
        return ()
    max_nodes = budget // min(p.recourse)
    adj = [[] for _ in range(p.n)]
    for i, j, _ in p.edges:
        adj[i].append(j)
        adj[j].append(i)
    dist = {a: 1 for a in set(anchors)}
    queue = deque(dist)
    while queue:
        i = queue.popleft()
        if dist[i] >= max_nodes:
            continue
        for j in adj[i]:
            if j not in dist:
                dist[j] = dist[i] + 1
                queue.append(j)
    return tuple(sorted(dist))


def restrict(p: Problem, region):
    """Absorb all crossing edges into unary terms; retain outside constant."""
    ids = tuple(sorted(set(region)))
    pos = {i: k for k, i in enumerate(ids)}
    unary = [list(p.unary[i]) for i in ids]
    constant = sum(p.unary[i][p.x0[i]] for i in range(p.n) if i not in pos)
    edges = []
    for i, j, w in p.edges:
        if i in pos and j in pos:
            edges.append((pos[i], pos[j], w))
        elif i in pos:
            for v in (0, 1):
                unary[pos[i]][v] += w * (v != p.x0[j])
        elif j in pos:
            for v in (0, 1):
                unary[pos[j]][v] += w * (v != p.x0[i])
        else:
            constant += w * (p.x0[i] != p.x0[j])
    reduced = Problem(tuple(map(tuple, unary)), tuple(edges),
                      tuple(p.x0[i] for i in ids), tuple(p.recourse[i] for i in ids))
    return reduced, constant, ids


def brute_force(p: Problem, budget):
    """Independent oracle: enumerates every binary assignment."""
    best = (math.inf, p.x0)
    for x in product((0, 1), repeat=p.n):
        if p.resource(x) <= budget and p.energy(x) < best[0]:
            best = (p.energy(x), x)
    return best


def greedy(p: Problem, budget):
    x = list(p.x0)
    while True:
        current = p.energy(x)
        candidates = []
        for i in range(p.n):
            trial = x.copy()
            trial[i] ^= 1
            if p.resource(trial) <= budget:
                gain = current - p.energy(trial)
                if gain > 0:
                    candidates.append((gain / p.recourse[i], gain, -i, trial))
        if not candidates:
            return p.energy(x), tuple(x)
        x = max(candidates)[-1]


def budget_bnb(p: Problem, budget: int, seconds=10.0, lambdas=(0, 1, 2, 4, 8, 16, 32, 64)):
    """Best-bound exact search with valid finite-family Lagrangian bounds.

    Timeout is cooperative BETWEEN mincut calls; a single mincut can overrun it.
    Every open node retains a valid bound, so timeout still returns a certificate.
    """
    assert budget >= 0
    start = perf_counter()
    upper, incumbent = greedy(p, budget)
    cut_calls = 0
    nodes = 0
    serial = 0
    queue = []
    degree = [0] * p.n
    for i, j, w in p.edges:
        degree[i] += w
        degree[j] += w

    def bound(fixed):
        nonlocal upper, incumbent, cut_calls
        forced_cost = sum(p.recourse[i] for i, v in fixed.items() if v != p.x0[i])
        if forced_cost > budget:
            return math.inf
        lower = -math.inf
        for lam in lambdas:
            value, x = mincut(p, lam, fixed)
            cut_calls += 1
            lower = max(lower, value - lam * budget)
            if p.resource(x) <= budget and p.energy(x) < upper:
                upper, incumbent = p.energy(x), x
            # The current lower bound already proves that this branch cannot
            # improve the incumbent. In particular, a feasible lambda=0 cut
            # proves the constrained optimum; do not scan redundant multipliers.
            if lower >= upper:
                return lower
        return lower

    root = bound({})
    if root < upper:
        heappush(queue, (root, serial, {}))
    while queue and perf_counter() - start < seconds:
        lower, _, fixed = heappop(queue)
        nodes += 1
        if lower >= upper:
            continue
        free = [i for i in range(p.n) if i not in fixed]
        if not free:
            continue
        i = max(free, key=lambda v: (degree[v] + abs(p.unary[v][0] - p.unary[v][1]), -v))
        for label in (p.x0[i], 1 - p.x0[i]):
            child = {**fixed, i: label}
            child_bound = bound(child)
            if child_bound < upper:
                serial += 1
                heappush(queue, (child_bound, serial, child))
    lower = min([upper] + [item[0] for item in queue])
    return {"x": incumbent, "upper": upper, "lower": lower,
            "gap_abs": upper - lower, "status": "optimal" if lower == upper else "timeout",
            "nodes": nodes, "cut_calls": cut_calls, "seconds": perf_counter() - start}


def solve_repair(old: Problem, new: Problem, budget: int, seconds=10.0, regional=True):
    """Prototype supports unary perturbations on an unchanged interaction graph.

    epsilon is COMPUTED from an exact old mincut; never assumed to be zero.
    """
    assert old.edges == new.edges and old.x0 == new.x0 and old.recourse == new.recourse
    start = perf_counter()
    anchors = tuple(i for i in range(old.n) if old.unary[i] != new.unary[i])
    old_opt, _ = mincut(old)
    epsilon = old.energy(old.x0) - old_opt
    region = anchored_region(new, anchors, budget) if regional else tuple(range(new.n))
    reduced, constant, ids = restrict(new, region)
    prep = perf_counter() - start
    result = budget_bnb(reduced, budget, seconds)
    x = list(new.x0)
    for k, i in enumerate(ids):
        x[i] = result["x"][k]
    upper = result["upper"] + constant
    lower_reduced = result["lower"] + constant
    lower_global = lower_reduced - (epsilon if regional else 0)
    assert new.energy(x) == upper and new.resource(x) <= budget
    return {**result, "x": tuple(x), "upper": upper, "lower": lower_global,
            "lower_reduced": lower_reduced, "gap_abs": upper - lower_global,
            "status": ("optimal" if upper == lower_global else
                       "epsilon_certified" if result["status"] == "optimal" and regional else "timeout"),
            "old_epsilon": epsilon, "region_n": len(ids), "original_n": new.n,
            "anchors": anchors, "recourse_used": new.resource(x),
            "preprocess_seconds": prep, "optimization_seconds": result["seconds"],
            "total_seconds": perf_counter() - start}
