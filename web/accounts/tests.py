"""Onboarding guarantees: anonymous browsing untouched, no child data, skippable
steps, preferences only used with consent, suggestions always moderated."""
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import Client, TestCase
from django.utils import timezone

from atlas.models import AuditEntry, Resource, Submission

from .models import FamilyPreferences, SavedPlace


def make_resource(name, **kw):
    d = dict(category="playground", community="crescent_city", min_age=0, max_age=18, cost_status="free",
             accessibility_status="unknown", location=Point(-124.2, 41.75, srid=4326),
             last_verified_at=timezone.now() - timedelta(days=3), verification_method="official_online")
    d.update(kw)
    r = Resource.objects.create(name=name, **d)
    r.save_revision().publish()
    return r


class Onboarding(TestCase):
    def setUp(self):
        self.c = Client()
        self.park = make_resource("Free Park", min_age=2, max_age=12)
        self.teen = make_resource("Teen Club", category="after_school", min_age=12, max_age=18, cost_status="priced")

    def test_anonymous_can_browse_everything(self):
        for url in ("/", "/explore/", "/explore/?view=map", "/this-week/", "/about/", "/contribute/", f"/resource/{self.park.slug}/"):
            self.assertEqual(self.c.get(url).status_code, 200, url)

    def test_signup_requires_adult_confirmation_and_has_no_child_fields(self):
        r = self.c.post("/accounts/join/", {"username": "carer", "email": "c@example.invalid", "password1": "long-enough-pass-123", "password2": "long-enough-pass-123"})
        self.assertEqual(r.status_code, 200)  # adult box missing -> form error, no account
        self.assertFalse(get_user_model().objects.filter(username="carer").exists())
        r = self.c.post("/accounts/join/", {"username": "carer", "email": "c@example.invalid", "password1": "long-enough-pass-123", "password2": "long-enough-pass-123", "adult": "on"})
        self.assertRedirects(r, "/accounts/welcome/1/")
        page = self.c.get("/accounts/welcome/2/").content.decode().lower()
        for forbidden in ("child's name", "school attended", "home address", "date of birth"):
            self.assertNotIn(forbidden, page)
        self.assertIn("not a child profile", page)
        self.assertTrue(AuditEntry.objects.filter(payload__event="account_created").exists())

    def _join(self):
        self.c.post("/accounts/join/", {"username": "carer", "email": "c@example.invalid", "password1": "long-enough-pass-123", "password2": "long-enough-pass-123", "adult": "on"})
        return get_user_model().objects.get(username="carer")

    def test_every_step_is_skippable(self):
        self._join()
        self.assertRedirects(self.c.post("/accounts/welcome/1/", {"skip": "1"}), "/accounts/welcome/2/")
        self.assertRedirects(self.c.post("/accounts/welcome/2/", {"skip": "1"}), "/accounts/welcome/3/")
        self.assertRedirects(self.c.post("/accounts/welcome/3/", {"skip": "1"}), "/accounts/my-atlas/")
        self.assertTrue(FamilyPreferences.objects.get(user__username="carer").onboarding_done)

    def test_preferences_shape_compass_only_with_consent(self):
        user = self._join()
        prefs = user.family_prefs
        prefs.age_bands = ["0_2", "3_5"]; prefs.budget = "free"; prefs.dosage = "few"; prefs.compass_may_remember = True; prefs.save()
        d = self.c.post("/compass/ask", data=json.dumps({"question": "somewhere to go"}), content_type="application/json").json()
        names = [i["name"] for i in d["items"]]
        self.assertIn("Free Park", names)
        self.assertNotIn("Teen Club", names)
        self.assertTrue(any("saved settings" in m for m in d["provenance"]["memory_used"]))
        prefs.compass_may_remember = False; prefs.save()
        d = self.c.post("/compass/ask", data=json.dumps({"question": "somewhere to go"}), content_type="application/json").json()
        self.assertEqual([m for m in d["provenance"]["memory_used"] if "saved settings" in m], [])

    def test_saved_places_and_contributor_request_are_private_and_moderated(self):
        user = self._join()
        self.c.post(f"/accounts/save/{self.park.id}/")
        self.assertEqual(SavedPlace.objects.filter(user=user).count(), 1)
        self.c.post(f"/accounts/save/{self.park.id}/")
        self.assertEqual(SavedPlace.objects.filter(user=user).count(), 0)
        self.c.post("/accounts/request-contributor/", {"note": "I run the story time"})
        sub = Submission.objects.get(submitter=user)
        self.assertEqual(sub.status, "pending")
        self.assertFalse(user.groups.filter(name="Contributors").exists())  # nothing granted automatically

    def test_compass_prepares_a_moderated_draft_only_for_signed_in_people(self):
        d = self.c.post("/compass/ask", data=json.dumps({"question": "correct: the park closes at dusk now"}), content_type="application/json").json()
        self.assertEqual(d["action"], "ask")
        self.assertEqual(Submission.objects.count(), 0)
        self._join()
        d = self.c.post("/compass/ask", data=json.dumps({"question": "correct: the park closes at dusk now"}), content_type="application/json").json()
        self.assertEqual(d["action"], "prepare")
        sub = Submission.objects.get()
        self.assertEqual(sub.status, "pending")
        self.assertEqual(sub.proposed_payload["via"], "compass")
        self.assertTrue(Resource.objects.get(pk=self.park.pk).live)  # nothing changed publicly
        rec = AuditEntry.objects.get(index=d["provenance"]["audit_index"])
        self.assertEqual(rec.payload["action_proposed"], "prepare_submission")

    def test_public_contribution_form_never_publishes(self):
        r = self.c.post("/contribute/", {"kind": "new", "name": "Fictional Farm", "details": "A farm with a corn maze", "source_url": "https://example.org/x"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Submission.objects.count(), 1)
        self.assertFalse(Resource.objects.filter(name="Fictional Farm").exists())
