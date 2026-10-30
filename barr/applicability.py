"""Check when static additive capacities are redundant over the whole budget ball.

This is a deployment guard, not a solver for active capacity constraints.
Loads/capacities must be supplied in consistent units by the operator; graph
structure and CODEOWNERS records do not establish these quantities.
"""
from .timing import query_clock


def capacity_guard(p, budget, loads, capacities):
    """Exact worst incoming load by 0/1 knapsack, O(n * min(B, sum r)) time.

    loads[i][t] is the nonnegative integer load of package i on team t.
    For each team, ignore outflows (they only help) and maximize incoming load
    over transfers costing at most B. Passing certifies EVERY budget-feasible
    assignment respects both static capacities. Failure does not mean that
    the desired optimum is infeasible, only that BARR's unconstrained theorem
    alone cannot certify that capacity model. No scheduling guarantee is made.
    """
    if not isinstance(budget, int) or budget < 0:
        raise ValueError("budget must be a nonnegative integer")
    loads = tuple(tuple(row) for row in loads)
    capacities = tuple(capacities)
    if (len(loads) != p.n or any(len(row) != 2 for row in loads)
            or len(capacities) != 2
            or any(not isinstance(v, int) or v < 0 for row in loads for v in row)
            or any(not isinstance(v, int) or v < 0 for v in capacities)):
        raise ValueError("loads and two capacities must be nonnegative integers")
    old_load = tuple(sum(loads[i][t] for i in range(p.n) if p.x0[i] == t)
                     for t in (0, 1))
    incoming = []
    for t in (0, 1):
        items = [(p.recourse[i], loads[i][t]) for i in range(p.n) if p.x0[i] != t]
        cap = min(budget, sum(r for r, _ in items))
        dp = [0] * (cap + 1)
        for r, load in items:
            for b in range(cap, r - 1, -1):
                dp[b] = max(dp[b], dp[b - r] + load)
        incoming.append(dp[cap])
    worst = tuple(old_load[t] + incoming[t] for t in (0, 1))
    return {"certified": all(worst[t] <= capacities[t] for t in (0, 1)),
            "old_load": old_load, "available_slack": tuple(capacities[t] - old_load[t] for t in (0, 1)),
            "max_incoming_load": tuple(incoming), "worst_budget_load": worst,
            "capacities": capacities, "budget": budget,
            "scope": "static additive loads; every budget-feasible binary repair"}


class CapacityNotCertified(ValueError):
    """Use a full model with explicit capacities; do not apply the region theorem."""

    def __init__(self, audit):
        self.audit = audit
        super().__init__("Capacity redundancy not certified; use a full capacity-constrained model")


def solve_capacity_guarded(old, new, budget, loads, capacities, **kwargs):
    """Run the existing query pipeline only after proving capacity redundancy.

    The additional guard time is included in total_seconds. Failing the guard
    raises before any regional solve, with the failed audit attached.
    """
    from .cpsat import solve_repair_cpsat
    start = query_clock()
    audit = capacity_guard(new, budget, loads, capacities)
    if not audit["certified"]:
        raise CapacityNotCertified(audit)
    guard_seconds = query_clock() - start
    kwargs["seconds"] = max(0.001, kwargs.get("seconds", 5) - guard_seconds)
    result = solve_repair_cpsat(old, new, budget, **kwargs)
    assigned_load = tuple(sum(loads[i][t] for i in range(new.n) if result["x"][i] == t)
                          for t in (0, 1))
    assert all(assigned_load[t] <= capacities[t] for t in (0, 1))
    return {**result, "capacity_audit": audit, "assigned_load": assigned_load,
            "capacity_guard_seconds": guard_seconds, "total_seconds": query_clock() - start}
