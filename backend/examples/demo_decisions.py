"""Reproducible synthetic example. Nothing herein is a real Crescent City listing."""
from pc_core.bayes import (BetaEvidence, FamilyQuery, Resource, eligible_resources,
                           choose_binary_action, expected_value_of_sample_information,
                           binary_test_information_gain)
from pc_core.geometry import fisher_rao_bernoulli
from pc_core.active_inference import binary_risk_ambiguity
from pc_core.history import EventStore, example_event

r = [Resource('fake-p1','Fictional indoor play',0,8,0,'unknown',True,.8),
     Resource('fake-p2','Fictional accessible park',2,18,0,'verified_yes',True,.95),
     Resource('fake-p3','Unverified art class',5,12,15,'verified_yes',False,.9)]
print('Suitable verified and explicitly accessible examples:',
      [x.name for x in eligible_resources(r,FamilyQuery(child_age=6,max_cost_usd=5,requires_accessibility=True))])
print('Illustrative posterior mean after 3 successes/1 failure:',BetaEvidence().update(3,1).mean)
print('Bayes action under assumed utilities at p=.45:',choose_binary_action(.45))
print('Net EVSI of verification under hypothetical test:', round(expected_value_of_sample_information(.45,.95,.95,verification_cost=.05),4))
print('Epistemic mutual information (nats):', round(binary_test_information_gain(.45,.95,.95),4))
print('Fisher-Rao change .45 to .75 (radians):',round(fisher_rao_bernoulli(.45,.75),4))
print('EFE risk+ambiguity toy:',tuple(round(x,4) for x in binary_risk_ambiguity(.45,.95,.05,.8)))
s=EventStore();print('First event stored?',s.append(example_event()));print('Duplicate stored again?',s.append(example_event()))
