"""Steward trust stays consistent with the Bayes act and treats stewards fairly (see examples/steward_trust.py)."""
import unittest

from pc_core.bayes import choose_binary_action
from pc_core.freshness import GammaRate
from pc_core.steward import PooledPrior, Record, beta_lower, blame_share, prob_current, record_outcome, reliability, shelf_life

PROGRAMMES = GammaRate(2, 360)


class StewardTrust(unittest.TestCase):
    def test_new_steward_starts_at_the_group_level(self):
        prior = PooledPrior.from_records([Record(20, 1), Record(15, 0)])
        self.assertAlmostEqual(reliability(Record(), prior), prior.p)

    def test_same_bayes_act(self):
        for r in (0.6, 0.8, 0.95):
            for t in (0, 30, 90, 400):
                p = prob_current(r, PROGRAMMES, t)
                self.assertEqual(choose_binary_action(p)[0] == "show", p > 0.75)

    def test_shelf_life_hits_the_threshold(self):
        t = shelf_life(0.9, PROGRAMMES)
        self.assertAlmostEqual(prob_current(0.9, PROGRAMMES, t), 0.75, places=9)
        self.assertEqual(shelf_life(0.7, PROGRAMMES), 0.0)

    def test_later_change_is_not_blamed(self):
        self.assertGreater(blame_share(0.9, PROGRAMMES, 7), blame_share(0.9, PROGRAMMES, 400))
        rec, change = record_outcome(Record(), "changed_since", 0.9, PROGRAMMES, 30, evidence_dated=True)
        self.assertEqual((rec.wrong, change), (0.0, 1.0))
        self.assertEqual(record_outcome(Record(), "cant_tell", 0.9, PROGRAMMES, 30)[0], Record())
        with self.assertRaises(ValueError):
            record_outcome(Record(), "popular", 0.9, PROGRAMMES, 30)

    def test_invitation_bound_matches_research_11(self):
        self.assertEqual(round(beta_lower(21, 1), 2), 0.87)
        self.assertEqual(round(beta_lower(21, 3), 2), 0.75)


if __name__ == "__main__":
    unittest.main()
