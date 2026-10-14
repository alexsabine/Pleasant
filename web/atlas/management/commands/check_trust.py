"""Trust-orientation check over the LIVE database and the running code paths.

T1  the hash-chained audit log verifies end to end;
T2  operational closure: every live public listing's published attributes trace to verified
    observed/reported claims, verified by an authorised role, with the verification in the chain
    (pc_core.closure.check_operational_closure);
T3  nothing live is a fixture or unverified; every live listing has a last-verified timestamp;
T4  leakage: drafts, restricted/private and sensitive records never leave the public API
    (resources.json, resources.geojson, h3_venues.geojson); aggregates respect k-anonymity;
T5  every Compass decision record in the chain carries the eleven provenance fields and only
    allow-listed tools;
T6  no non-superuser holds the publish permission on listings; contributor and public submissions
    never auto-publish (every pending submission has no live listing created from it);
T7  no child data: no model field across the project names a child, a date of birth or a school attended;
T8  private mode: templates and our own scripts make no off-origin requests (map, fonts, icons);
T9  acceptance count, stated honestly: listings checked online by the assistant are not human-verified
    and do not count toward the 40.
Writes research/08_trust_check.md.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.test import RequestFactory

from atlas import views
from atlas.models import REQUIRED_DECISION_FIELDS, AuditEntry, Claim, Resource, Submission
from compass.tools import ALLOW_LIST
from pc_core.closure import Claim as CClaim, PublishedFact, check_operational_closure

ROLE_GROUPS = {"editors": "editor", "stewards": "steward", "administrators": "admin", "admins": "admin"}


def role_of(user) -> str | None:
    if user is None:
        return None
    if user.is_superuser:
        return "admin"
    for g in user.groups.all():
        r = ROLE_GROUPS.get(g.name.lower())
        if r:
            return r
    return None


class Command(BaseCommand):
    help = __doc__
    results: list

    def record(self, name, ok, detail):
        self.results.append((name, bool(ok), detail))
        self.stdout.write(f"[TRUST] {'PASS' if ok else 'FAIL'}  {name}\n        {detail}")

    def handle(self, *args, **opts):
        self.results = []
        rf = RequestFactory()

        # T1 audit chain
        ok, bad = AuditEntry.verify_chain()
        self.record("T1 audit chain verifies (RFC 6962-style hash chain over every publish, verification and Compass answer)",
                   ok, f"{AuditEntry.objects.count()} entries; first bad index: {bad}")

        # T2 closure over the live projection
        live = list(Resource.objects.filter(live=True, visibility="public"))
        hashes = set(AuditEntry.objects.values_list("hash", flat=True))
        claims = {}
        for c in Claim.objects.filter(resource__in=live).select_related("verified_by"):
            claims[str(c.pk)] = CClaim(str(c.pk), str(c.resource_id), c.attribute, c.epistemic_type,
                                       role_of(c.verified_by) if c.verification_status == "verified" else None, c.audit_hash or None)
        facts = []
        for r in live:
            attrs = sorted({c.attribute for c in claims.values() if c.resource_id == str(r.pk)})
            if not attrs:
                facts.append(PublishedFact(str(r.pk), "listing", ()))
            for a in attrs:
                facts.append(PublishedFact(str(r.pk), a, tuple(cid for cid, c in claims.items() if c.resource_id == str(r.pk) and c.attribute == a)))
        rep = check_operational_closure(facts, claims, hashes)
        self.record("T2 operational closure: every published attribute of every live listing traces to a verified observed/reported claim by an authorised role, recorded in the chain",
                   rep.ok, f"{len(live)} live listings, {len(facts)} published attributes, {len(claims)} claims; violations: {rep.violations[:5] or 'none'}")

        # T3 nothing unverified live
        fixtures = [r.name for r in live if r.is_fictional or r.verification_method == "none" or r.last_verified_at is None]
        self.record("T3 nothing live is a fixture or unverified; every live listing carries a last-verified timestamp and a verification method",
                   not fixtures, f"offenders: {fixtures or 'none'}")

        # T4 leakage via the public API (the real view functions)
        hidden = set(Resource.objects.exclude(live=True, visibility="public", is_sensitive=False).values_list("pk", flat=True))
        leaked = set()
        for path, view in (("/api/resources.json", views.api_resources), ("/api/resources.geojson", views.api_resources_geojson), ("/api/h3_venues.geojson", views.api_h3_venues)):
            body = json.loads(view(rf.get(path)).content)
            ids = {i["id"] for i in body.get("items", [])} | {f["properties"].get("id") for f in body.get("features", [])}
            leaked |= ids & hidden
        agg = json.loads(views.api_h3_aggregate(rf.get("/api/h3.geojson?res=8&k=5")).content)
        small = [f for f in agg["features"] if not f["properties"]["suppressed"] and f["properties"]["count"] < 5]
        self.record("T4 drafts, restricted and sensitive records never leave the public API; H3 aggregates suppress counts below k",
                   not leaked and not small, f"{len(hidden)} hidden records, leaked ids: {sorted(leaked) or 'none'}; aggregate cells under k shown unsuppressed: {len(small)}")

        # T5 Compass decision records
        recs = [e.payload for e in AuditEntry.objects.filter(payload__policy_version__startswith="compass")]
        incomplete = [r.get("request_id") for r in recs if any(k not in r for k in REQUIRED_DECISION_FIELDS)]
        off_list = [r.get("request_id") for r in recs if any(t not in ALLOW_LIST for t in r.get("retrieval_sources", []))]
        self.record("T5 every Compass decision record has the eleven provenance fields and used only allow-listed read-only tools",
                   not incomplete and not off_list, f"{len(recs)} Compass records; incomplete: {len(incomplete)}; off-allow-list tools: {len(off_list)}")

        # T6 permissions
        User = get_user_model()
        publishers = [u.get_username() for u in User.objects.filter(is_superuser=False) if u.has_perm("atlas.publish_resource")]
        auto = [s.pk for s in Submission.objects.filter(status="pending") if Resource.objects.filter(live=True, name__iexact=(s.proposed_payload.get("name") or "\0")).exists()]
        self.record("T6 no non-superuser can publish listings; pending submissions have produced no live listing",
                   not publishers and not auto, f"non-superusers with publish: {publishers or 'none'}; submissions that auto-published: {auto or 'none'}")

        # T7 no child data fields anywhere
        bad_fields = []
        pat = re.compile(r"child|dob|birth|school_attended|pupil|student_name", re.I)
        for m in apps.get_models():
            if m._meta.app_label in ("atlas", "accounts", "compass", "home"):
                for f in m._meta.get_fields():
                    if getattr(f, "model", m).__module__.startswith("wagtail"):
                        continue  # Wagtail's page-tree bookkeeping (numchild) is not about children
                    if pat.search(f.name):
                        bad_fields.append(f"{m.__name__}.{f.name}")
        self.record("T7 no model field in the project records a child's name, birth date or school attended", not bad_fields, f"fields: {bad_fields or 'none'}")

        # T8 off-origin requests in templates and our own static code
        root = Path(settings.BASE_DIR)
        offenders = []
        tag = re.compile(r"<(script|link|img|iframe|source|video|audio)\b[^>]*\b(src|href)=\"(https?:)?//", re.I)
        for p in list(root.glob("templates/**/*.html")):
            for i, line in enumerate(p.read_text().splitlines(), 1):
                if tag.search(line):
                    offenders.append(f"{p.relative_to(root)}:{i}")
        for p in list(root.glob("static/pc/*.js")) + list(root.glob("static/pc/*.css")) + list(root.glob("static/style/*.json")):
            txt = p.read_text()
            for m in re.finditer(r"https?://[a-z0-9.-]+", txt):
                host = m.group(0).split("//")[1]
                if host not in ("openstreetmap.org", "www.openstreetmap.org", "protomaps.com", "h3geo.org", "www.w3.org"):
                    offenders.append(f"{p.relative_to(root)} -> {host}")
        self.record("T8 private mode: no template tag or first-party script loads anything off-origin (attribution links excepted)",
                   not offenders, f"private mode {'on' if settings.PC_PRIVATE_MODE else 'OFF'}; offenders: {offenders[:6] or 'none'}")

        # T9 acceptance count, honestly
        human = [r for r in live if r.verification_method not in ("official_online", "none")]
        online = [r for r in live if r.verification_method == "official_online"]
        self.record("T9 acceptance count is stated honestly: only human-verified listings count toward the 40",
                   True, f"live: {len(live)}; checked online by the assistant: {len(online)}; human-verified: {len(human)} of 40 required "
                         "(the online checks are a starting point for the stewards' own verification, not a substitute)")

        n_pass = sum(1 for r in self.results if r[1])
        lines = ["# Trust-orientation check (generated)", "",
                 f"Generated by `manage.py check_trust` on {time.strftime('%Y-%m-%d')} over the live database. **{n_pass}/{len(self.results)} checks passed.**", "",
                 "| Check | Result | Detail |", "|---|---|---|"]
        for name, ok, detail in self.results:
            lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail.replace('|', '/')} |")
        out = Path(settings.REPO_ROOT) / "research" / "08_trust_check.md"
        out.write_text("\n".join(lines) + "\n")
        self.stdout.write(f"\n{n_pass}/{len(self.results)} trust checks passed; report written to {out}")
