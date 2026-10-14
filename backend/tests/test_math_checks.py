"""Unit tests for the new reference modules. Run from repo root:
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
"""
import math
import unittest

from pc_core.audit_chain import AuditChain
from pc_core.closure import Claim, PublishedFact, check_operational_closure, simulate_verification_loop
from pc_core.freshness import GammaRate, brier_decomposition, prob_current, review_priority
from pc_core.geometry import (fisher_information_bernoulli, fisher_rao_bernoulli,
                              fisher_rao_bernoulli_via_bhattacharyya, kl_bernoulli)
from pc_core.pomdp import (exact_posterior, freshness_pomdp, kalman_predict, propagate_with_gaps,
                           variational_free_energy)


class TestPOMDP(unittest.TestCase):
    def setUp(self):
        self.m = freshness_pomdp()

    def test_dp_matches_enumeration(self):
        for p in (0.2, 0.5, 0.8):
            b = [p, 1 - p]
            v_dp, _ = self.m.value_dp(b, 2)
            v_best = max(self.m.value_of_policy_tree(b, t) for t in self.m.all_policy_trees(2))
            self.assertAlmostEqual(v_dp, v_best, places=12)

    def test_missing_observation_propagates_only(self):
        b = [0.9, 0.1]
        self.assertEqual(self.m.update(b, "abstain", None), self.m.predict(b, "abstain"))

    def test_efe_identity(self):
        for a in self.m.actions:
            g = self.m.efe([0.4, 0.6], a)
            self.assertAlmostEqual(g["G_risk_ambiguity"], g["G_epistemic_pragmatic"], places=12)

    def test_vfe_bound(self):
        prior, lik = [0.3, 0.7], [0.8, 0.1]
        post = exact_posterior(prior, lik)
        neg_log_ev = -math.log(sum(p * l for p, l in zip(prior, lik)))
        self.assertAlmostEqual(variational_free_energy(post, prior, lik), neg_log_ev, places=12)
        self.assertGreater(variational_free_energy([0.5, 0.5], prior, lik), neg_log_ev)

    def test_kalman_gaps_and_duplicates(self):
        _, var = kalman_predict(0.0, 1.0, 0.5)
        self.assertAlmostEqual(var, 1.5)
        _, v, n = propagate_with_gaps(0.0, 1.0, 0.5, 1.0, [(1.0, "e1"), (1.0, "e1"), (None, None)])
        self.assertEqual(n, 1)
        self.assertGreater(v, 0.5)  # two predict steps after the single real update


class TestGeometry(unittest.TestCase):
    def test_two_formulas_agree(self):
        for p, q in ((0.1, 0.9), (0.3, 0.35), (0.5, 0.5)):
            self.assertAlmostEqual(fisher_rao_bernoulli(p, q), fisher_rao_bernoulli_via_bhattacharyya(p, q), places=10)

    def test_fisher_is_kl_hessian(self):
        p, h = 0.4, 1e-4
        hess = (kl_bernoulli(p, p + h) - 2 * kl_bernoulli(p, p) + kl_bernoulli(p, p - h)) / h ** 2
        self.assertAlmostEqual(hess, fisher_information_bernoulli(p), places=2)


class TestFreshness(unittest.TestCase):
    def test_survival_monotone_and_conjugate(self):
        g = GammaRate(2.0, 100.0)
        self.assertEqual(prob_current(g, 0), 1.0)
        self.assertGreater(prob_current(g, 10), prob_current(g, 100))
        self.assertLess(g.update(0, 500).mean_hazard, g.mean_hazard)
        self.assertGreater(g.update(5, 10).mean_hazard, g.mean_hazard)

    def test_priority_shape(self):
        g = GammaRate(2.0, 200.0)
        vals = [review_priority(g, a, 0.95, 0.95) for a in (0, 31, 1499)]
        self.assertLess(vals[0], 0)
        self.assertGreater(vals[1], 0)
        self.assertLess(vals[2], 0)  # pure EVSI stops valuing checks of long-abandoned listings
        self.assertGreater(review_priority(g, 1499, 0.95, 0.95, repair_value=3.0), 0)

    def test_brier_exact_on_binned(self):
        probs = [0.15, 0.15, 0.85, 0.85, 0.45]
        outs = [0, 1, 1, 1, 0]
        self.assertAlmostEqual(brier_decomposition(probs, outs)["identity_gap"], 0.0, places=12)


class TestGovernance(unittest.TestCase):
    def test_chain_tamper_and_redaction(self):
        c = AuditChain()
        for i in range(3):
            c.append({"i": i})
        self.assertEqual(c.verify(), (True, None))
        c.entries[1].payload["i"] = 99
        self.assertEqual(c.verify()[1], 1)
        c.entries[1].payload["i"] = 1
        c.redact(0, "test")
        self.assertTrue(c.verify()[0])

    def test_decision_record_fields_required(self):
        with self.assertRaises(ValueError):
            AuditChain().append({"request_id": "only"}, require_decision_fields=True)

    def test_operational_closure(self):
        chain = AuditChain()
        h = chain.append({"verify": "c1"}).hash
        claims = {"c1": Claim("c1", "r", "hours", "reported", "editor", h),
                  "c2": Claim("c2", "r", "hours", "generated", "editor", h)}
        ok = check_operational_closure([PublishedFact("r", "hours", ("c1",))], claims, {h})
        bad = check_operational_closure([PublishedFact("r", "hours", ("c2",))], claims, {h})
        self.assertTrue(ok.ok)
        self.assertFalse(bad.ok)

    def test_homeostasis_bounded(self):
        none = simulate_verification_loop(n_listings=50, days=200, checks_per_day=0, policy="none")
        loop = simulate_verification_loop(n_listings=50, days=200, checks_per_day=2, policy="oldest")
        self.assertGreater(none.final_stale_fraction, 0.7)
        self.assertLess(loop.final_stale_fraction, 0.4)


class TestCrescent(unittest.TestCase):
    def test_phase_is_belief(self):
        from pc_core.crescent import fr_theta, illuminated_fraction
        for p in (0.0, 0.2, 0.5, 0.9, 1.0):
            self.assertAlmostEqual(illuminated_fraction(fr_theta(p)), p, places=12)

    def test_venue_cells_hierarchy(self):
        try:
            from pc_core import h3_index as hx
            import h3
        except Exception:
            self.skipTest("h3 not installed")
        lat, lon = 41.7455, -124.1865
        cells = hx.venue_cells(lat, lon)
        self.assertEqual(sorted(cells), [8, 9, 10, 11, 12])
        # Each stored cell is the EXACT containing cell at that resolution. H3 parent
        # chains are only approximately nested (hexagons cannot tile hexagons), so the
        # parent of the res-11 cell is not guaranteed to be the point's res-10 cell;
        # that is precisely why every resolution is stored, not derived.
        for r, c in cells.items():
            self.assertEqual(c, h3.latlng_to_cell(lat, lon, r))
        self.assertEqual(len(hx.cell_polygon(cells[11])), 7)


class TestH3Optional(unittest.TestCase):
    def test_guards(self):
        try:
            from pc_core import h3_index as hx
            import h3  # noqa: F401
        except Exception:
            self.skipTest("h3 not installed")
        with self.assertRaises(ValueError):
            hx.public_aggregate([(41.75, -124.2, False)], res=10)
        agg = hx.public_aggregate([(41.75, -124.2, False)], res=8, k=5)
        self.assertTrue(agg[0].suppressed and agg[0].count == 0)


if __name__ == "__main__":
    unittest.main()
