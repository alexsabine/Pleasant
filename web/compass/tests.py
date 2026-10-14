"""Honesty and trust guarantees of Crescent Compass, tested end to end against
the published projection. Run: python manage.py test compass atlas"""
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import Client, TestCase
from django.utils import timezone

from atlas.models import AuditEntry, Claim, Event, ProjectionVersion, Resource


def make_resource(name, **kw):
    now = timezone.now()
    defaults = dict(category="playground", community="crescent_city", min_age=0, max_age=18, cost_status="free",
                    accessibility_status="unknown", location=Point(-124.2, 41.75, srid=4326),
                    last_verified_at=now - timedelta(days=kw.pop("days", 5)), is_fictional=True)
    defaults.update(kw)
    r = Resource.objects.create(name=name, **defaults)
    r.save_revision().publish()
    return r


class CompassGuarantees(TestCase):
    def setUp(self):
        self.c = Client()
        self.fresh_access = make_resource("Fresh Accessible Park", accessibility_status="verified_yes", days=3)
        self.fresh_unknown = make_resource("Fresh Unknown Park", accessibility_status="unknown", days=3)
        self.stale = make_resource("Stale Library", category="library", min_age=0, max_age=6, days=90)
        self.draft = Resource.objects.create(name="Draft Only Place", category="playground", location=Point(-124.2, 41.75, srid=4326),
                                             last_verified_at=timezone.now(), is_fictional=True)  # never published
        self.private = make_resource("Private Place", visibility="private", days=1)
        self.sensitive = make_resource("Sensitive Nest Site", is_sensitive=True, days=1)
        Event.objects.create(title="Past Event", start_at=timezone.now() - timedelta(days=2), is_fictional=True).save_revision().publish()
        Event.objects.create(title="Future Event", start_at=timezone.now() + timedelta(days=2), cost_status="free", is_fictional=True).save_revision().publish()

    def ask(self, q):
        r = self.c.post("/compass/ask", data=json.dumps({"question": q}), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content[:200])
        return r.json()

    def test_unknown_access_is_never_presented_as_accessible(self):
        d = self.ask("Where can we go with a wheelchair?")
        names = [i["name"] for i in d["items"]]
        self.assertIn("Fresh Accessible Park", names)
        self.assertNotIn("Fresh Unknown Park", names)
        self.assertNotIn("access unknown", d["text"].split("Fresh Accessible Park")[0])

    def test_unpublished_private_and_sensitive_never_leave_the_server(self):
        d = self.ask("somewhere for a toddler")
        text = json.dumps(d)
        for hidden in ("Draft Only Place", "Private Place", "Sensitive Nest Site"):
            self.assertNotIn(hidden, text)

    def test_stale_listing_is_shown_as_low_confidence_not_recommended(self):
        d = self.ask("story time for a 4 year old")
        self.assertEqual(d["action"], "show_low_confidence")
        self.assertEqual([i["name"] for i in d["withheld"]], ["Stale Library"])
        self.assertIn("not been re-verified recently", d["text"])

    def test_no_match_is_an_honest_unknown_not_an_invention(self):
        Resource.objects.all().delete()
        d = self.ask("Is there a trampoline park?")
        self.assertEqual(d["action"], "explain_unknown")
        self.assertIn("will not guess", d["text"])
        self.assertEqual(d["items"], [])

    def test_expired_events_are_never_returned(self):
        d = self.ask("What's on this week?")
        titles = [e["title"] for e in d["events"]]
        self.assertIn("Future Event", titles)
        self.assertNotIn("Past Event", titles)
        self.assertEqual(d["items"], [])  # an events-only question does not dump the directory

    def test_every_answer_writes_a_complete_chained_decision_record(self):
        before = AuditEntry.objects.count()
        d = self.ask("free playground")
        self.assertEqual(AuditEntry.objects.count(), before + 1)
        rec = AuditEntry.objects.get(index=d["provenance"]["audit_index"])
        for k in ("request_id", "retrieval_sources", "source_versions", "policy_version", "assumptions", "confidence_type",
                  "action_proposed", "user_approval", "action_result", "timestamp", "limitations"):
            self.assertIn(k, rec.payload)
        self.assertEqual(rec.hash, d["provenance"]["audit_hash"])
        self.assertTrue(AuditEntry.verify_chain()[0])

    def test_memory_carries_preferences_and_can_be_forgotten(self):
        self.ask("free things for a 3 year old")
        d = self.ask("anything with wheelchair access?")
        self.assertTrue(any("age" in m for m in d["provenance"]["memory_used"]))
        self.assertEqual(d["provenance"]["intent"]["age"], 3)
        self.assertEqual(self.ask("forget that")["action"], "forget")
        d2 = self.ask("anything with wheelchair access?")
        self.assertEqual(d2["provenance"]["memory_used"], [])

    def test_memory_invalidates_when_projection_changes(self):
        self.ask("free things for a 3 year old")
        make_resource("Newly Published Place", days=1)  # publishing bumps the projection version
        d = self.ask("anything with wheelchair access?")
        self.assertEqual(d["provenance"]["memory_used"], [])

    def test_llm_is_off_by_default_and_tools_are_allow_listed(self):
        d = self.ask("free playground")
        self.assertFalse(d["provenance"]["llm_used"])
        self.assertTrue(set(d["provenance"]["tools"]) <= set(d["provenance"]["allow_list"]))


class PublicationClosure(TestCase):
    def test_generated_claim_cannot_be_verified_as_evidence(self):
        r = make_resource("Any Place")
        c = Claim.objects.create(resource=r, attribute="caption", raw_value={"t": "AI text"}, epistemic_type="generated")
        with self.assertRaises(ValueError):
            c.verify(get_user_model().objects.create(username="ed"))
        self.assertEqual(r.verified_claims().count(), 0)

    def test_verification_is_audited_and_duplicate_revision_is_one_observation(self):
        r = make_resource("Any Place")
        user = get_user_model().objects.create(username="ed")
        c = Claim.objects.create(resource=r, attribute="hours", raw_value={"t": "9-5"}, epistemic_type="reported", source_revision="etag-1")
        entry = c.verify(user)
        self.assertEqual(c.audit_hash, entry.hash)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Claim.objects.create(resource=r, attribute="hours", raw_value={"t": "9-5"}, epistemic_type="reported", source_revision="etag-1")

    def test_publish_bumps_projection_and_audits(self):
        v0, n0 = ProjectionVersion.current(), AuditEntry.objects.count()
        make_resource("Another Place")
        self.assertEqual(ProjectionVersion.current(), v0 + 1)
        self.assertEqual(AuditEntry.objects.count(), n0 + 1)
        self.assertEqual(AuditEntry.objects.latest("index").payload["event"], "published")


class GuideFeedback(TestCase):
    def test_guide_answers_are_stored_for_stewards_and_never_published(self):
        from atlas.models import AuditEntry, ReviewNote
        from django.test import Client
        c = Client()
        panel = c.get("/compass/").content.decode()
        self.assertIn("Help shape Compass", panel)
        self.assertIn("serve_first", panel)
        r = c.post("/compass/feedback", data=json.dumps({"answers": [{"key": "serve_first", "answer": "Newcomers first."}, {"key": "bogus", "answer": "x"}, {"key": "red_lines", "answer": ""}]}), content_type="application/json")
        self.assertEqual(r.json()["saved"], 1)
        note = ReviewNote.objects.get()
        self.assertEqual(note.question_key, "compass:serve_first")
        self.assertTrue(AuditEntry.objects.filter(payload__event="compass_guide_feedback").exists())
        for url in ("/api/resources.json", "/explore/"):
            self.assertNotIn("Newcomers first", c.get(url).content.decode())
        self.assertEqual(c.post("/compass/feedback", data="nope", content_type="application/json").status_code, 400)
