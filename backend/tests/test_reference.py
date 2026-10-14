import math
import unittest
from pc_core.bayes import (BetaEvidence, binary_test_information_gain,
                           FamilyQuery, Resource, eligible_resources,
                           choose_binary_action, expected_value_of_sample_information)
from pc_core.geometry import (fisher_rao_bernoulli, arc_from_probabilities,
                              surplus_on_bernoulli_path)
from pc_core.history import EventStore, example_event, exponential_working_summary
from pc_core.active_inference import binary_risk_ambiguity
from pc_core.geo import require_layer_approval
from pc_core.permissions import Principal,ContentObject,can_read,can_publish,can_send_location

class TestMath(unittest.TestCase):
    def test_beta(self): self.assertAlmostEqual(BetaEvidence().update(3,1).mean,4/6)
    def test_duplicate_beta_not_always_independent(self):
        # Calling update twice is explicitly a different assumption; EventStore rejects duplicates.
        s=EventStore(); self.assertTrue(s.append(example_event()));self.assertFalse(s.append(example_event()))
    def test_fr_symmetric(self):
        self.assertAlmostEqual(fisher_rao_bernoulli(.2,.9),fisher_rao_bernoulli(.9,.2))
        self.assertAlmostEqual(fisher_rao_bernoulli(.2,.2),0)
    def test_fr_path_surplus(self):
        pts=[.2,.8,.2]
        self.assertAlmostEqual(arc_from_probabilities(pts),2*fisher_rao_bernoulli(.2,.8))
        self.assertAlmostEqual(surplus_on_bernoulli_path(pts),arc_from_probabilities(pts))
    def test_info_gain(self):
        self.assertAlmostEqual(binary_test_information_gain(.5,.5,.5),0,places=12)
        self.assertAlmostEqual(binary_test_information_gain(.5,1,1),math.log(2),places=12)
    def test_evsi(self):
        self.assertGreater(expected_value_of_sample_information(.5,1,1,verification_cost=0),0)
        self.assertLess(expected_value_of_sample_information(.5,.5,.5,verification_cost=.1),0)
    def test_abstain(self):self.assertEqual(choose_binary_action(.1)[0],'abstain')
    def test_efe_positive(self):
        g,r,a=binary_risk_ambiguity(.5,.9,.1,.8)
        self.assertAlmostEqual(g,r+a)
        self.assertGreaterEqual(g,-1e-12)
    def test_lossy_memory(self):
        # distinct histories can collapse to same working state (q=.5)
        self.assertAlmostEqual(exponential_working_summary([0,1],.5),
                               exponential_working_summary([1,.5],.5))

class TestPolicy(unittest.TestCase):
    def test_hard_accessibility_filter(self):
        r=[Resource('a','A',1,18,0,'unknown',True,.99),
           Resource('b','B',1,18,0,'verified_yes',True,.7),
           Resource('c','C',1,18,0,'verified_yes',False,.99)]
        matches=eligible_resources(r,FamilyQuery(6,5,requires_accessibility=True))
        self.assertEqual([x.identifier for x in matches],['b'])
    def test_geodata_rights(self):
        with self.assertRaises(PermissionError):
            require_layer_approval({'id':'COUNTY','decision':'needs_written_permission'})
        require_layer_approval({'id':'NAIP','decision':'approved_with_metadata'})
    def test_unauthenticated_cannot_publish(self):
        obj=ContentObject('r1','public','draft')
        self.assertFalse(can_publish(Principal(None,'public'),obj))
        self.assertTrue(can_publish(Principal('editor','editor'),obj))
    def test_private_unreadable(self):
        obj=ContentObject('r1','private','approved',owner_id='alice')
        self.assertFalse(can_read(Principal('bob','member'),obj))
        self.assertTrue(can_read(Principal('alice','member'),obj))
    def test_location_requires_approval(self):
        self.assertFalse(can_send_location(Principal('a','member'),True,False))
        self.assertTrue(can_send_location(Principal('a','member'),True,True))

if __name__=='__main__':unittest.main()
