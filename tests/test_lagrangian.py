import random
import unittest
from fractions import Fraction
from itertools import product
from barr.core import Problem
from barr.lagrangian import rational_cut,restore_budget,solve_lagrangian_repair

class LagrangianTests(unittest.TestCase):
    def test_rational_bounds_and_primal_recovery_against_enumeration(self):
        rng=random.Random(711)
        for _ in range(50):
            n=rng.randrange(2,8)
            p=Problem(tuple((rng.randrange(-5,9),rng.randrange(-5,9)) for i in range(n)),
                tuple((i,j,rng.randrange(0,6)) for i in range(n) for j in range(i+1,n) if rng.random()<.4),
                tuple(rng.randrange(2) for i in range(n)),tuple(rng.randrange(1,4) for i in range(n)))
            budget=rng.randrange(sum(p.recourse)+1);xs=list(product((0,1),repeat=n))
            optimum=min(p.energy(x) for x in xs if p.resource(x)<=budget)
            for lam in [Fraction(0),Fraction(1,3),Fraction(7,4)]:
                value,x=rational_cut(p,lam)
                self.assertEqual(value,min(Fraction(p.energy(y))+lam*p.resource(y) for y in xs))
                self.assertLessEqual(value-lam*budget,optimum)
                repaired=restore_budget(p,x,budget)
                self.assertLessEqual(p.resource(repaired),budget)
            result=solve_lagrangian_repair(p,budget,2)
            self.assertLessEqual(result['lower'],optimum)
            self.assertGreaterEqual(result['upper'],optimum)
            self.assertEqual(result['upper'],p.energy(result['x']))
            self.assertLessEqual(p.resource(result['x']),budget)
