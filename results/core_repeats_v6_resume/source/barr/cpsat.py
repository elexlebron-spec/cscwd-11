"""Single-thread exact CP-SAT baseline and the matched BARR wrapper."""
from math import ceil
from .timing import query_clock as perf_counter


def solve_cpsat(p, budget, seconds=10, seed=0):
    from ortools.sat.python import cp_model
    start = perf_counter()
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x_{i}") for i in range(p.n)]
    terms = [p.unary[i][0] + (p.unary[i][1] - p.unary[i][0]) * x[i] for i in range(p.n)]
    for i, j, w in p.edges:
        y = model.NewBoolVar(f"cut_{i}_{j}")
        model.AddAbsEquality(y, x[i] - x[j])
        terms.append(w * y)
    model.Add(sum(p.recourse[i] * (x[i] if p.x0[i] == 0 else 1 - x[i])
                  for i in range(p.n)) <= budget)
    model.Minimize(sum(terms))
    for i in range(p.n):
        model.AddHint(x[i], p.x0[i])
    built = perf_counter()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(0.001, seconds - (built - start))
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    status = solver.Solve(model)
    result = {"status": solver.StatusName(status), "lower": ceil(solver.BestObjectiveBound() - 1e-6),
              "build_seconds": built - start, "solver_seconds": solver.WallTime(),
              "branches": solver.NumBranches(), "conflicts": solver.NumConflicts(),
              "total_seconds": perf_counter() - start}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        labels = tuple(solver.Value(v) for v in x)
        result.update(x=labels, upper=p.energy(labels), recourse_used=p.resource(labels))
        assert result["recourse_used"] <= budget
    elif status == cp_model.UNKNOWN:
        from .flow import mincut_fast
        lower, _ = mincut_fast(p)
        result.update(x=p.x0, upper=p.energy(p.x0), recourse_used=0, lower=lower)
    else:
        raise RuntimeError(f"Unexpected CP-SAT status for a model with feasible x0: {result['status']}")
    result["total_seconds"] = perf_counter() - start
    return result


def solve_repair_cpsat(old, new, budget, seconds=5, regional=False,
                       common_fastpath=True, seed=0, old_certificate=None,
                       region_mode="weighted"):
    """Matched query pipeline; include preprocessing, model building and solving.

    old_certificate is an optional cached exact old optimum (generated offline).
    None means recompute and charge it only to the regional method.
    """
    from .core import anchored_region, hop_region, restrict
    from .flow import mincut_fast
    assert old.edges == new.edges and old.x0 == new.x0 and old.recourse == new.recourse
    if region_mode not in ("weighted", "hop"):
        raise ValueError("region_mode must be weighted or hop")
    start = perf_counter()
    common_seconds = 0.0
    if common_fastpath:
        value, x = mincut_fast(new)
        common_seconds = perf_counter() - start
        if new.resource(x) <= budget:
            return {"x": x, "upper": value, "lower": value, "lower_reduced": value,
                    "status": "OPTIMAL", "region_n": new.n, "region_ratio": 1.0,
                    "old_epsilon": None, "recourse_used": new.resource(x),
                    "fastpath": True, "common_seconds": common_seconds,
                    "preprocess_seconds": 0.0, "build_seconds": 0.0, "solver_seconds": 0.0,
                    "branches": 0, "conflicts": 0, "total_seconds": perf_counter() - start}
    epsilon = 0
    if regional:
        old_min = mincut_fast(old)[0] if old_certificate is None else old_certificate
        epsilon = old.energy(old.x0) - old_min
        if epsilon < 0:
            raise ValueError("Invalid old certificate")
        anchors = tuple(i for i in range(old.n) if old.unary[i] != new.unary[i])
        region = (anchored_region if region_mode == "weighted" else hop_region)(new, anchors, budget)
        p, constant, ids = restrict(new, region)
    else:
        p, constant, ids = new, 0, tuple(range(new.n))
    prep_seconds = perf_counter() - start - common_seconds
    if p.n == 0:
        result = {"x": (), "upper": 0, "lower": 0, "status": "OPTIMAL", "build_seconds": 0,
                  "solver_seconds": 0, "branches": 0, "conflicts": 0}
    else:
        result = solve_cpsat(p, budget, max(0.001, seconds - (perf_counter() - start)), seed)
    x = list(new.x0)
    for k, i in enumerate(ids):
        x[i] = result["x"][k]
    upper = result["upper"] + constant
    lower_reduced = result["lower"] + constant
    lower = lower_reduced - epsilon
    assert new.energy(x) == upper and new.resource(x) <= budget
    status = "OPTIMAL" if lower == upper else (
        "EPSILON_CERTIFIED" if result["status"] == "OPTIMAL" else result["status"])
    return {**result, "x": tuple(x), "upper": upper, "lower": lower,
            "lower_reduced": lower_reduced, "status": status, "old_epsilon": epsilon,
            "region_n": p.n, "region_ratio": p.n / max(1, new.n),
            "recourse_used": new.resource(x), "fastpath": False, "common_seconds": common_seconds,
            "preprocess_seconds": prep_seconds, "total_seconds": perf_counter() - start}
