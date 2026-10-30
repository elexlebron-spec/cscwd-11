"""Prospective difficulty-factor generator; never filters or rejects easy seeds."""
from dataclasses import asdict, dataclass
from random import Random
from .core import Problem
from .flow import mincut_fast


@dataclass(frozen=True)
class Setting:
    n: int = 128
    seed: int = 0
    topology: str = "modular"
    coupling: int = 12
    preference: int = 2
    shock_scale: int = 8
    anchors: int = 4
    budget: int = 12
    weighted: bool = False
    degraded: int = 0


def generate(setting: Setting):
    s = setting
    rng = Random(s.seed)
    pairs = {}
    if s.topology == "modular":
        # 4x4 interface modules, joined by weak chain bridges.
        block = 16
        for i in range(s.n):
            if i + 1 < s.n and i // block == (i + 1) // block and i % 4 != 3:
                pairs[i, i + 1] = rng.randint(s.coupling, 2 * s.coupling)
            if i + 4 < s.n and i // block == (i + 4) // block:
                pairs[i, i + 4] = rng.randint(s.coupling, 2 * s.coupling)
        for i in range(15, s.n - 1, 16):
            pairs[i, i + 1] = 1
    elif s.topology in ("grid", "smallworld"):
        width = max(2, int(s.n ** 0.5))
        for i in range(s.n):
            if i + 1 < s.n and (i + 1) % width:
                pairs[i, i + 1] = rng.randint(s.coupling, 2 * s.coupling)
            if i + width < s.n:
                pairs[i, i + width] = rng.randint(s.coupling, 2 * s.coupling)
        if s.topology == "smallworld":
            for _ in range(2 * s.n):
                i, j = sorted(rng.sample(range(s.n), 2))
                pairs[i, j] = rng.randint(s.coupling, 2 * s.coupling)
    else:
        raise ValueError(s.topology)
    edges = tuple((i, j, w) for (i, j), w in sorted(pairs.items()))
    unary = []
    for i in range(s.n):
        pref = (i // 16) % 2 if s.topology == "modular" else (i // max(2, int(s.n**0.5))) % 2
        base = rng.randint(1, 4)
        extra = rng.randint(1, 2 * s.preference)
        unary.append(tuple(base + extra * (v != pref) for v in (0, 1)))
    r = tuple(rng.randint(1, 3) if s.weighted else 1 for _ in range(s.n))
    old0 = Problem(tuple(unary), edges, (0,) * s.n, r)
    old_opt, xstar = mincut_fast(old0)
    # Stratify anchors across modules, with one uniformly sampled position in each.
    # No objective-dependent selection and no rejection of generated instances.
    selected_blocks = rng.sample(range((s.n + 15) // 16), min(s.anchors, (s.n + 15) // 16))
    anchors = tuple(rng.randrange(b * 16, min((b + 1) * 16, s.n)) for b in selected_blocks)
    new_unary = [list(c) for c in unary]
    for i in anchors:
        # Mix positive/negative shifts of the two label costs. Support stays local.
        shift = rng.randint(s.shock_scale * s.coupling, (s.shock_scale + 2) * s.coupling)
        new_unary[i][xstar[i]] += shift
        new_unary[i][1 - xstar[i]] -= rng.randint(0, max(1, shift // 4))
    x0 = list(xstar)
    if s.degraded:
        # Perturb the old plan at low-cost non-anchor vertices. This constructs
        # near-optimal synthetic baselines; it is not a measured human plan.
        candidates = []
        adj = [[] for _ in range(s.n)]
        for i, j, w in edges:
            adj[i].append((j, w))
            adj[j].append((i, w))
        for i in range(s.n):
            if i not in anchors:
                delta = unary[i][1 - xstar[i]] - unary[i][xstar[i]]
                delta += sum(w * (1 if xstar[i] == xstar[j] else -1) for j, w in adj[i])
                candidates.append((delta, i))
        for _, i in sorted(candidates)[:s.degraded]:
            x0[i] ^= 1
    old = Problem(tuple(unary), edges, tuple(x0), r)
    new = Problem(tuple(map(tuple, new_unary)), edges, tuple(x0), r)
    return old, new, {"old_optimum": old_opt, "old_epsilon": old.energy(old.x0) - old_opt,
                      "anchors": anchors, "setting": asdict(s)}
