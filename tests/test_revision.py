import unittest
from itertools import product
from random import Random
from barr.core import Problem, brute_force, budget_bnb, mincut
from barr.generate import generate


class EarlyTerminationTests(unittest.TestCase):
    def test_feasible_unrestricted_cut_stops_after_one_call(self):
        p = Problem(((0, 4), (0, 3)), ((0, 1, 2),), (0, 0), (1, 1))
        result = budget_bnb(p, 1)
        self.assertEqual(result["cut_calls"], 1)
        self.assertEqual(result["upper"], result["lower"])


try:
    import ortools
    HAVE_ORTOOLS = True
except ImportError:
    HAVE_ORTOOLS = False


@unittest.skipUnless(HAVE_ORTOOLS, "requires project .venv with ortools")
class StrongBackendTests(unittest.TestCase):
    def test_weighted_region_is_subset_of_safe_hop_region(self):
        from barr.core import anchored_region, hop_region
        from barr.cpsat import solve_repair_cpsat
        for seed in range(12):
            old, new = generate(8, seed, "grid", 2)
            anchors = [i for i in range(new.n) if old.unary[i] != new.unary[i]]
            for budget in (0, 2, 5):
                weighted = set(anchored_region(new, anchors, budget))
                hop = set(hop_region(new, anchors, budget))
                self.assertLessEqual(weighted, hop)
                optimum, _ = brute_force(new, budget)
                result = solve_repair_cpsat(old, new, budget, 2, True, False, region_mode="hop")
                self.assertEqual(result["upper"], optimum)
                self.assertEqual(result["lower"], optimum)

    def test_classical_baselines_match_energy_and_valid_bounds(self):
        from barr.baselines import greedy_delta, penalty_scan
        from barr.core import greedy
        for seed in range(10):
            _, p = generate(8, seed, "grid", 2)
            for budget in (0, 3, 6):
                oracle, _ = brute_force(p, budget)
                self.assertEqual(greedy_delta(p, budget), greedy(p, budget))
                result = penalty_scan(p, budget)
                self.assertLessEqual(result["lower"], oracle)
                self.assertGreaterEqual(result["upper"], oracle)

    def test_fast_flow_against_bruteforce_including_fixed_labels(self):
        from barr.flow import mincut_fast
        for seed in range(12):
            _, p = generate(8, seed, "grid")
            p = Problem(tuple((a-11, b-9) for a, b in p.unary), p.edges, p.x0, p.recourse)
            for lam in (0, 3, 11):
                fixed = {0: seed % 2, 5: (seed // 2) % 2}
                expected = min(p.energy(x)+lam*p.resource(x)
                               for x in product((0, 1), repeat=p.n)
                               if all(x[i] == v for i, v in fixed.items()))
                self.assertEqual(mincut_fast(p, lam, fixed)[0], expected)
        empty = Problem((), (), (), ())
        self.assertEqual(mincut_fast(empty), (0, ()))

    def test_cpsat_full_and_region_vs_oracle(self):
        from barr.cpsat import solve_cpsat, solve_repair_cpsat
        for seed in range(10):
            old, new = generate(8, seed, "grid", 2)
            if seed % 2:
                x0 = tuple((v ^ (i == 0)) for i, v in enumerate(old.x0))
                old = Problem(old.unary, old.edges, x0, old.recourse)
                new = Problem(new.unary, new.edges, x0, new.recourse)
            eps = old.energy(old.x0) - mincut(old)[0]
            for budget in (0, 2, 5):
                oracle, _ = brute_force(new, budget)
                full = solve_cpsat(new, budget, 2)
                self.assertEqual(full["upper"], oracle)
                self.assertEqual(full["lower"], oracle)
                for shortcut in (False, True):
                    region = solve_repair_cpsat(old, new, budget, 2, True, shortcut)
                    self.assertLessEqual(region["upper"], oracle + eps)
                    self.assertLessEqual(region["lower"], oracle)

    def test_large_flow_does_not_use_recursion(self):
        from barr.flow import mincut_fast
        n = 1500
        p = Problem(((0, 2),) * n, tuple((i, i+1, 1) for i in range(n-1)), (0,)*n, (1,)*n)
        self.assertEqual(mincut_fast(p)[0], 0)


if __name__ == "__main__":
    unittest.main()
