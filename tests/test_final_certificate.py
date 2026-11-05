"""Certificate/termination checks against enumeration, not timing benchmarks."""
import unittest
from itertools import product
from random import Random
from unittest.mock import patch, MagicMock
from barr.core import Problem, brute_force, solve_repair
from barr.cpsat import solve_cpsat, solve_repair_cpsat
from barr.flow import mincut_fast


class FinalCertificateTests(unittest.TestCase):
    def test_full_region_does_not_pay_positive_old_gap(self):
        old = Problem(((3, 0), (0, 1)), ((0, 1, 1),), (0, 0), (1, 1))
        new = Problem(((5, 0), (0, 1)), old.edges, old.x0, old.recourse)
        r = solve_repair_cpsat(old, new, 2, regional=True, common_fastpath=False)
        self.assertGreater(r['old_epsilon'], 0)
        self.assertEqual(r['region_n'], new.n)
        self.assertEqual((r['lower'], r['upper']), (1, 1))
        self.assertEqual(r['status'], 'OPTIMAL')
        reference = solve_repair(old, new, 2)
        self.assertEqual((reference['lower'], reference['upper'], reference['status']), (1, 1, 'optimal'))

    def test_proper_region_combines_cut_with_transferred_bound(self):
        old = Problem(((3, 0), (10, 0)), (), (0, 0), (1, 2))
        new = Problem(((1, 5), (10, 0)), (), old.x0, old.recourse)
        r = solve_repair_cpsat(old, new, 1, regional=True)
        self.assertEqual(r['region_n'], 1)
        self.assertEqual(r['lower_reduced'] - r['old_epsilon'], -2)
        self.assertEqual((r['lower'], r['upper']), (1, 11))
        self.assertEqual(r['status'], 'EPSILON_CERTIFIED')
        self.assertEqual(brute_force(new, 1)[0], 11)

    def test_unknown_without_incumbent_uses_old_plan_and_offset(self):
        from ortools.sat.python import cp_model
        old = Problem(((3, 0), (10, 0), (-7, -7)), (), (0, 0, 0), (1, 1, 1))
        new = Problem(((1, 5), (10, 0), (-7, -7)), (), old.x0, old.recourse)
        solver = MagicMock()
        solver.Solve.return_value = cp_model.UNKNOWN
        solver.StatusName.return_value = 'UNKNOWN'
        solver.BestObjectiveBound.return_value = 0
        solver.WallTime.return_value = 0
        solver.NumBranches.return_value = solver.NumConflicts.return_value = 0
        with patch.object(cp_model, 'CpSolver', return_value=solver):
            direct = solve_cpsat(new, 1)
            r = solve_repair_cpsat(old, new, 1, regional=True)
        solver.Value.assert_not_called()
        for q in [direct, r]:
            self.assertEqual(q['x'], old.x0)
            self.assertEqual(q['upper'], new.energy(old.x0))
            self.assertEqual(q['recourse_used'], 0)
            self.assertEqual(q['incumbent_source'], 'old_plan_fallback')
            self.assertLessEqual(q['lower'], brute_force(new, 1)[0])
        self.assertEqual(r['upper'], 4)  # local value 1 plus exterior offset 3

    def test_enumerated_mixed_gaps_and_regions(self):
        rng = Random(20261105)
        counts = {'positive': 0, 'full': 0, 'proper': 0, 'cut_strengthened': 0}
        for _ in range(40):
            n = 6
            edges = tuple((i, j, rng.randrange(1, 4)) for i in range(n)
                          for j in range(i+1, n) if rng.random() < .25)
            unary = tuple((rng.randrange(-4, 6), rng.randrange(-4, 6)) for _ in range(n))
            x0 = tuple(rng.randrange(2) for _ in range(n))
            costs = tuple(rng.randrange(1, 4) for _ in range(n))
            old = Problem(unary, edges, x0, costs)
            changed = list(unary); a = rng.randrange(n)
            changed[a] = (unary[a][0] + rng.randrange(1, 5), unary[a][1] - 2)
            new = Problem(tuple(changed), edges, x0, costs)
            for budget in (0, 3, sum(costs)):
                r = solve_repair_cpsat(old, new, budget, regional=True, common_fastpath=False)
                opt = brute_force(new, budget)[0]
                full = r['region_n'] == n
                counts['full' if full else 'proper'] += 1
                counts['positive'] += r['old_epsilon'] > 0
                transferred = r['lower_reduced'] - (0 if full else r['old_epsilon'])
                counts['cut_strengthened'] += r['lower'] > transferred
                self.assertEqual(r['lower'], max(mincut_fast(new)[0], transferred))
                self.assertLessEqual(r['lower'], opt)
                self.assertLessEqual(opt, r['upper'])
                self.assertEqual(new.energy(r['x']), r['upper'])
                self.assertLessEqual(new.resource(r['x']), budget)
                self.assertEqual(r['status'] == 'OPTIMAL', r['lower'] == r['upper'])
                reference = solve_repair(old, new, budget)
                self.assertEqual(reference['lower'], r['lower'])
                self.assertEqual(reference['upper'], r['upper'])
                if full:
                    self.assertEqual(r['lower'], opt)
        self.assertTrue(all(counts.values()), counts)


if __name__ == '__main__':
    unittest.main()
