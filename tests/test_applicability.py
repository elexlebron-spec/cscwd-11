import unittest
from itertools import product
from random import Random
from barr.core import Problem, anchored_region, restrict
from barr.applicability import capacity_guard, solve_capacity_guarded, CapacityNotCertified


class ApplicabilityTests(unittest.TestCase):
    def test_worst_capacity_load_against_every_budget_assignment(self):
        rng = Random(20261030)
        for _ in range(100):
            n = 7
            p = Problem(((0, 0),) * n, (), tuple(rng.randrange(2) for _ in range(n)),
                        tuple(rng.randrange(1, 5) for _ in range(n)))
            loads = tuple((rng.randrange(5), rng.randrange(5)) for _ in range(n))
            budget = rng.randrange(sum(p.recourse) + 2)
            feasible = [x for x in product((0, 1), repeat=n) if p.resource(x) <= budget]
            worst = tuple(max(sum(loads[i][t] for i in range(n) if x[i] == t)
                              for x in feasible) for t in (0, 1))
            audit = capacity_guard(p, budget, loads, worst)
            self.assertEqual(audit["worst_budget_load"], worst)
            self.assertTrue(audit["certified"])
            if worst[0] > 0:
                self.assertFalse(capacity_guard(p, budget, loads, (worst[0] - 1, worst[1]))["certified"])

    def test_active_capacity_breaks_remote_reversion(self):
        # With one slot per team, a useful change at anchor 0 needs a remote swap.
        old = Problem(((0, 1), (1, 0)), (), (0, 1), (1, 1))
        new = Problem(((4, 0), (1, 0)), (), old.x0, old.recourse)
        labels = list(product((0, 1), repeat=2))
        self.assertEqual(min(old.energy(x) for x in labels), old.energy(old.x0))
        feasible = [x for x in labels if x.count(0) <= 1 and x.count(1) <= 1]
        region = anchored_region(new, (0,), 2)
        restricted = [x for x in feasible if all(x[i] == old.x0[i] for i in range(2) if i not in region)]
        self.assertEqual(min(map(new.energy, feasible)), 1)
        self.assertEqual(min(map(new.energy, restricted)), 4)
        audit = capacity_guard(new, 2, ((1, 1), (1, 1)), (1, 1))
        self.assertFalse(audit["certified"])
        with self.assertRaises(CapacityNotCertified):
            solve_capacity_guarded(old, new, 2, ((1, 1), (1, 1)), (1, 1), regional=True)

    def test_passing_guard_preserves_existing_result_and_loads(self):
        old = Problem(((0, 2), (0, 2)), ((0, 1, 1),), (0, 0), (1, 2))
        new = Problem(((5, 0), (0, 2)), old.edges, old.x0, old.recourse)
        result = solve_capacity_guarded(old, new, 1, ((2, 1), (2, 3)), (4, 1), regional=True)
        self.assertTrue(result["capacity_audit"]["certified"])
        self.assertEqual(result["x"], (1, 0))
        self.assertEqual(result["assigned_load"], (2, 1))
        self.assertLessEqual(result["capacity_guard_seconds"], result["total_seconds"])

    def test_invalid_capacity_inputs_fail_explicitly(self):
        p = Problem(((0, 1),), (), (0,), (1,))
        for budget, loads, caps in [(-1, ((1, 1),), (2, 2)), (1, ((-1, 0),), (2, 2)),
                                    (1, (), (2, 2)), (1, ((1, 1),), (2,))]:
            with self.assertRaises(ValueError):
                capacity_guard(p, budget, loads, caps)


if __name__ == "__main__":
    unittest.main()
