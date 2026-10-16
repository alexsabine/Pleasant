"""Load the five FICTIONAL demonstration listings, three events, verified
claims with audit entries, demo users and a moderation workflow.

Every record is flagged is_fictional=True and rendered with a visible badge.
Names are invented; coordinates are public street-level points in Crescent
City chosen only so the map has something to show. None of this counts
toward the 40 human-verified listings.

Usage: python manage.py load_demo [--reset]
Demo passwords come from DEMO_PASSWORD (default printed; change locally).
"""
from __future__ import annotations

import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.utils import timezone

from atlas.models import AuditEntry, CategoryHazard, Claim, Event, ProjectionVersion, Resource, Submission
from home.models import HomePage

DEMO = [
    dict(name="Harbour Play Yard (fictional)", slug="harbour-play-yard-demo", category="playground", community="crescent_city",
         min_age=2, max_age=12, cost_status="free", accessibility_status="verified_yes",
         access_notes="Level rubber surface, accessible parking two bays (fictional).", lon=-124.1865, lat=41.7455,
         description="A fenced playground beside the harbour with toddler swings and a shaded picnic table. Fictional demonstration record.",
         public_source_url="https://example.org/fictional/harbour-play-yard", source_note="Demo fixture, not a real place.",
         verified_days_ago=12, website_url="https://example.org/fictional/harbour-play-yard"),
    dict(name="Rainy Day Story Hour (fictional)", slug="rainy-day-story-hour-demo", category="library", community="crescent_city",
         min_age=0, max_age=6, cost_status="free", accessibility_status="unknown", lon=-124.2012, lat=41.7562,
         description="Weekly story time with songs for babies and preschoolers. Fictional demonstration record.",
         public_source_url="https://example.org/fictional/story-hour", source_note="Demo fixture.", verified_days_ago=40),
    dict(name="Dune Trail Loop (fictional)", slug="dune-trail-loop-demo", category="trail", community="crescent_city",
         min_age=0, max_age=18, cost_status="free", accessibility_status="verified_no",
         access_notes="Sand surface, not suitable for wheels (fictional).", lon=-124.2140, lat=41.7730,
         description="A 1.2 km loop through dunes to the beach; buggies struggle on sand. Fictional demonstration record.",
         public_source_url="https://example.org/fictional/dune-trail", source_note="Demo fixture.", verified_days_ago=30),
    dict(name="Tidepool Explorers Club (fictional)", slug="tidepool-explorers-demo", category="class", community="crescent_city",
         min_age=6, max_age=12, cost_status="priced", cost_usd=15, accessibility_status="unknown", lon=-124.2060, lat=41.7420,
         description="Guided rockpool sessions on low-tide Saturdays. Fictional demonstration record.",
         public_source_url="https://example.org/fictional/tidepool-club", source_note="Demo fixture.", verified_days_ago=75),
    dict(name="Family Resource Hub (fictional)", slug="family-resource-hub-demo", category="family_service", community="crescent_city",
         min_age=0, max_age=18, cost_status="free", accessibility_status="verified_yes", lon=-124.1930, lat=41.7510,
         description="Drop-in advice for caregivers, nappies and a warm room. Fictional demonstration record.",
         public_source_url="https://example.org/fictional/family-hub", source_note="Demo fixture.", verified_days_ago=5,
         phone_public="000-000-0000 (fictional)"),
]


class Command(BaseCommand):
    help = "Load fictional demo data (never real listings)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="delete existing fictional demo records first")

    def handle(self, *args, **opts):
        User = get_user_model()
        pw = os.environ.get("DEMO_PASSWORD", "change-me-locally-123")
        admin, created = User.objects.get_or_create(username="demo_admin", defaults={"is_staff": True, "is_superuser": True, "email": "admin@example.invalid"})
        if created:
            admin.set_password(pw); admin.save()
        editor, created = User.objects.get_or_create(username="demo_editor", defaults={"is_staff": True, "email": "editor@example.invalid"})
        if created:
            editor.set_password(pw); editor.save()
        for gname in ("Editors", "Moderators"):
            g, _ = Group.objects.get_or_create(name=gname)
            if gname == "Editors":
                editor.groups.add(g)
            else:
                admin.groups.add(g)
        self._grant_snippet_perms()

        if opts["reset"]:
            Resource.objects.filter(is_fictional=True).delete()
            Event.objects.filter(is_fictional=True).delete()

        for cat, _ in Resource._meta.get_field("category").choices:
            h = CategoryHazard.for_category(cat)
            if cat in ("event_venue", "class"):
                h.rate = 60.0; h.save()  # more volatile categories: 2/60 per day prior mean hazard

        now = timezone.now()
        created_n = 0
        for d in DEMO:
            d = dict(d)
            days = d.pop("verified_days_ago")
            lon, lat = d.pop("lon"), d.pop("lat")
            r, was_created = Resource.objects.get_or_create(slug=d["slug"], defaults={**d, "is_fictional": True, "location": Point(lon, lat, srid=4326),
                                                                                       "last_verified_at": now - timedelta(days=days)})
            if not was_created:
                continue
            created_n += 1
            # Evidence: a reported claim (contributor) and an observed claim (editor site visit), both verified by the editor.
            c1 = Claim.objects.create(resource=r, attribute="opening_hours", raw_value={"text": "daylight hours (fictional)"},
                                      epistemic_type="reported", source_uri=r.public_source_url, source_revision=f"demo-rev-{r.slug}-1",
                                      source_observed_at=now - timedelta(days=days + 1), submitted_by=editor)
            c1.verify(editor, note="demo verification")
            c2 = Claim.objects.create(resource=r, attribute="accessibility_status", raw_value={"value": r.accessibility_status},
                                      epistemic_type="observed", source_revision=f"demo-rev-{r.slug}-2",
                                      source_observed_at=now - timedelta(days=days), submitted_by=editor)
            c2.verify(editor, note="demo site check")
            # A generated claim that must never support publication (LLM caption draft).
            Claim.objects.create(resource=r, attribute="caption_draft", raw_value={"text": "AI draft caption (fictional)"},
                                 epistemic_type="generated", source_revision=f"demo-rev-{r.slug}-3", access_level="private")
            r.save_revision(user=editor).publish(user=admin)

        if not Event.objects.filter(is_fictional=True).exists():
            hub = Resource.objects.get(slug="family-resource-hub-demo")
            lib = Resource.objects.get(slug="rainy-day-story-hour-demo")
            events = [
                dict(title="Story Hour (fictional)", resource=lib, start_at=self._next_weekday(now, 1, 10, 30), end_at=None, recurrence_rule="Every Tuesday",
                     location=lib.location, cost_status="free", min_age=0, max_age=6, source_url=lib.public_source_url),
                dict(title="Caregiver coffee morning (fictional)", resource=hub, start_at=self._next_weekday(now, 3, 9, 30), end_at=None, recurrence_rule="",
                     location=hub.location, cost_status="free", min_age=0, max_age=18, source_url=hub.public_source_url),
                dict(title="Low-tide rockpool walk (fictional)", resource=None, start_at=self._next_weekday(now, 5, 8, 0), end_at=None, recurrence_rule="",
                     location=Point(-124.2065, 41.7410, srid=4326), cost_status="priced", min_age=6, max_age=12, source_url="https://example.org/fictional/rockpool"),
            ]
            for e in events:
                ev = Event.objects.create(**e, is_fictional=True, last_verified_at=now - timedelta(days=3))
                ev.save_revision(user=editor).publish(user=admin)

        if not Submission.objects.exists():
            Submission.objects.create(target_resource=Resource.objects.get(slug="rainy-day-story-hour-demo"), submitter=None,
                                      proposed_payload={"attribute": "accessibility_status", "value": "verified_yes",
                                                        "note": "There is a ramp at the side door (fictional public suggestion)"})

        self._ensure_workflow()
        self._ensure_homepage()
        ok, bad = AuditEntry.verify_chain()
        self.stdout.write(self.style.SUCCESS(
            f"demo: {created_n} new fictional resources; {Resource.objects.filter(is_fictional=True, live=True).count()} live; "
            f"events {Event.objects.filter(is_fictional=True).count()}; audit entries {AuditEntry.objects.count()} chain ok={ok}; "
            f"projection v{ProjectionVersion.current()}. Users demo_admin / demo_editor (password from DEMO_PASSWORD)."))

    @staticmethod
    def _next_weekday(now, weekday, hour, minute):
        d = now + timedelta(days=(weekday - now.weekday()) % 7 or 7)
        return d.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _grant_snippet_perms(self):
        from django.contrib.auth.models import Permission
        editors = Group.objects.get(name="Editors")
        mods = Group.objects.get(name="Moderators")
        for model in (Resource, Event, Claim, Submission):
            ct = ContentType.objects.get_for_model(model)
            for p in Permission.objects.filter(content_type=ct):
                mods.permissions.add(p)
                # Editors draft and verify; only Moderators (the two organisational admins) publish or delete.
                if p.codename.startswith(("publish_", "delete_")):
                    editors.permissions.remove(p)
                else:
                    editors.permissions.add(p)
        for codename in ("access_admin",):
            for p in Permission.objects.filter(codename=codename):
                editors.permissions.add(p); mods.permissions.add(p)
        for model in (CategoryHazard, AuditEntry):
            ct = ContentType.objects.get_for_model(model)
            for p in Permission.objects.filter(content_type=ct):
                mods.permissions.add(p)

    def _ensure_workflow(self):
        """Resources require Moderators' approval before publication (Wagtail workflow)."""
        from wagtail.models import GroupApprovalTask, Workflow, WorkflowContentType, WorkflowTask
        wf, created = Workflow.objects.get_or_create(name="Moderators approval for listings", defaults={"active": True})
        if created:
            task, _ = GroupApprovalTask.objects.get_or_create(name="Moderator approval")
            task.groups.add(Group.objects.get(name="Moderators"))
            WorkflowTask.objects.create(workflow=wf, task=task, sort_order=0)
        ct = ContentType.objects.get_for_model(Resource)
        WorkflowContentType.objects.get_or_create(workflow=wf, content_type=ct)

    def _ensure_homepage(self):
        from wagtail.models import Page, Site
        if HomePage.objects.exists():
            return
        root = Page.get_first_root_node()
        # Replace Wagtail's default welcome page (slug 'home', not our type).
        for old in Page.objects.filter(depth=2, slug="home").exclude(content_type=ContentType.objects.get_for_model(HomePage)):
            Site.objects.filter(root_page=old).update(root_page=root)
            old.delete()
        home = HomePage(title="Crescent Compass", slug="home", strapline="Things to do with kids in Del Norte County",
                        intro="<p>A calm, verified directory for caregivers of children aged 0 to 18. Every listing shows its source and when it was last checked.</p>",
                        optional_question="Just show free things?")
        root.add_child(instance=home)
        home.save_revision().publish()
        site = Site.objects.filter(is_default_site=True).first()
        if site:
            site.root_page = home; site.save()
        else:
            Site.objects.create(hostname="localhost", port=8000, root_page=home, is_default_site=True)
