import unittest
from itertools import product
from barr.core import brute_force,anchored_region,restrict
from barr.stress import StressSetting,generate_stress


class StressFamilyTests(unittest.TestCase):
    def test_old_optimum_and_budget_core_on_small_graphs(self):
        for seed in range(8):
            old,new,d=generate_stress(StressSetting(8,4,seed))
            self.assertEqual(min(old.energy(x) for x in product((0,1),repeat=8)),0)
            optimum,x=brute_force(new,d['budget'])
            self.assertEqual(x[0],1)
            self.assertEqual(sum(x[1:5]),2)
            self.assertTrue(all(v==0 for v in x[5:]))
            p,c,_=restrict(new,anchored_region(new,d['anchors'],d['budget']))
            self.assertEqual(brute_force(p,d['budget'])[0]+c,optimum)


if __name__=='__main__':unittest.main()
