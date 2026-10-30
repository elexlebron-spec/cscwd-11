import unittest
from itertools import product
from random import Random
from barr.core import Problem, anchored_region, brute_force, budget_bnb, mincut, restrict, solve_repair
from barr.generate import generate


class TheoryTests(unittest.TestCase):
    def test_mincut_and_conditional_lagrangian_against_enumeration(self):
        rng = Random(810)
        for seed in range(12):
            _, p = generate(7, seed, topology="grid")
            # Include negative unary costs and a non-optimal mixed baseline.
            p = Problem(tuple((a - 13, b - 9) for a, b in p.unary), p.edges,
                        tuple(rng.randrange(2) for _ in range(7)), p.recourse)
            for lam in (0, 1, 7):
                for fixed in ({}, {0: 0, 3: 1}):
                    value, _ = mincut(p, lam, fixed)
                    expected = min(p.energy(x) + lam * p.resource(x)
                                   for x in product((0, 1), repeat=p.n)
                                   if all(x[i] == v for i, v in fixed.items()))
                    self.assertEqual(value, expected)

    def test_exact_locality_and_solver_for_every_budget(self):
        for seed in range(16):
            old, new = generate(9, seed, topology=("chain", "grid")[seed % 2], shock_count=1 + seed % 2)
            for budget in range(7):
                oracle, _ = brute_force(new, budget)
                result = solve_repair(old, new, budget, 10)
                self.assertEqual(result["upper"], oracle)
                self.assertEqual(result["lower"], oracle)
                self.assertEqual(result["old_epsilon"], 0)

    def test_epsilon_bound_for_arbitrary_old_plan(self):
        rng = Random(315)
        for seed in range(10):
            old, new = generate(8, seed)
            x0 = tuple(rng.randrange(2) for _ in range(8))
            old = Problem(old.unary, old.edges, x0, old.recourse)
            new = Problem(new.unary, new.edges, x0, new.recourse)
            for budget in range(5):
                optimum, _ = brute_force(new, budget)
                result = solve_repair(old, new, budget, 10)
                self.assertLessEqual(result["upper"], optimum + result["old_epsilon"])
                self.assertLessEqual(result["lower"], optimum)

    def test_boundary_absorption_exact_for_all_assignments(self):
        _, p = generate(8, 2, topology="grid")
        for region in ((), (1,), (0, 2, 3, 5), tuple(range(8))):
            reduced, constant, ids = restrict(p, region)
            for labels in product((0, 1), repeat=len(ids)):
                x = list(p.x0)
                for k, i in enumerate(ids):
                    x[i] = labels[k]
                self.assertEqual(p.energy(x), reduced.energy(labels) + constant)

    def test_weighted_path_includes_anchor_and_target(self):
        p = Problem(((0, 1),) * 4, ((0, 1, 1), (1, 2, 1), (2, 3, 1)), (0,) * 4, (3, 2, 1, 4))
        self.assertEqual(anchored_region(p, (0,), 2), ())
        self.assertEqual(anchored_region(p, (0,), 5), (0, 1))
        self.assertEqual(anchored_region(p, (0,), 6), (0, 1, 2))

    def test_unsafe_locality_counterexample_if_epsilon_ignored(self):
        # Distant component was already suboptimal before the shock.
        old = Problem(((0, 5), (10, 0)), (), (0, 0), (1, 1))
        new = Problem(((1, 5), (10, 0)), (), (0, 0), (1, 1))
        result = solve_repair(old, new, 1)
        optimum, _ = brute_force(new, 1)
        self.assertGreater(result["upper"], optimum)
        self.assertEqual(result["upper"] - optimum, result["old_epsilon"])

    def test_timeout_certificate_is_valid(self):
        for seed in range(8):
            _, p = generate(10, seed, topology="grid")
            optimum, _ = brute_force(p, 4)
            result = budget_bnb(p, 4, seconds=0)
            self.assertLessEqual(result["lower"], optimum)
            self.assertGreaterEqual(result["upper"], optimum)
            self.assertLessEqual(p.resource(result["x"]), 4)

    def test_no_shock_zero_budget_and_expensive_anchor(self):
        old, new = generate(7, 5)
        for p, budget in ((old, 5), (new, 0)):
            result = solve_repair(old, p, budget)
            self.assertEqual(result["x"], old.x0)


if __name__ == "__main__":
    unittest.main()
