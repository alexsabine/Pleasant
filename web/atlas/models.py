"""Atlas data model: evidence -> claims -> published projection, with typed
timestamps, epistemic classes and a hash-chained audit log.

Mirrors infrastructure/schema_reference.sql. Wagtail mixins give drafts,
revisions, locking and moderation workflows without custom code.
"""
from __future__ import annotations

import json
from datetime import timedelta

from django.conf import settings
from django.contrib.gis.db import models as gis
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from wagtail.models import DraftStateMixin, LockableMixin, RevisionMixin, WorkflowMixin
from wagtail.search import index

from pc_core.audit_chain import GENESIS, REQUIRED_DECISION_FIELDS, entry_hash
from pc_core.freshness import GammaRate, prob_current, review_priority

CATEGORIES = [
    ("school", "School"), ("preschool", "Preschool and early learning"), ("childcare", "Childcare"), ("college", "College"),
    ("after_school", "After-school and youth"), ("library", "Library and story time"), ("class", "Class or club"),
    ("playground", "Playground"), ("park", "Park"), ("beach", "Beach"), ("river", "River access"), ("trail", "Trail"), ("sport", "Sport and swim"),
    ("attraction", "Attraction"), ("museum", "Museum"), ("visitor_center", "Visitor centre"), ("arts", "Arts"),
    ("indoor_play", "Indoor play"), ("family_service", "Family service"), ("health", "Health and wellbeing"),
    ("food", "Food help"), ("event_venue", "Event venue"),
]
# Kim's launch groups (proposal section 3.2), in her order. Every category maps to exactly one group.
GROUPS = [
    ("parks", "Parks and playgrounds"), ("pools", "Pools and indoor recreation"), ("attractions", "Attractions"),
    ("water", "Rivers and beaches"), ("nature", "Hiking and nature"), ("learning", "Learning and STEM"), ("arts", "Arts"),
    ("services", "Libraries and family services"), ("programs", "Programs, events and people to call"),
]
CATEGORY_GROUP = {
    "playground": "parks", "park": "parks", "sport": "pools", "indoor_play": "pools",
    "attraction": "attractions", "museum": "attractions", "visitor_center": "attractions",
    "beach": "water", "river": "water", "trail": "nature",
    "school": "learning", "preschool": "learning", "childcare": "learning", "college": "learning", "class": "learning",
    "arts": "arts", "library": "services", "family_service": "services", "health": "services", "food": "services",
    "after_school": "programs", "event_venue": "programs",
}
GROUP_LABEL = dict(GROUPS)
VERIFICATION_METHOD = [
    ("official_online", "Checked against official website (not visited)"),
    ("human_site", "Human site visit"),
    ("none", "Not verified"),
]
COMMUNITIES = [
    ("crescent_city", "Crescent City"), ("smith_river", "Smith River"), ("gasquet", "Gasquet"),
    ("klamath", "Klamath"), ("fort_dick", "Fort Dick"), ("hiouchi", "Hiouchi"), ("countywide", "Countywide"),
]
COST_STATUS = [("free", "Free"), ("priced", "Priced"), ("variable", "Variable"), ("unknown", "Unknown")]
ACCESS_STATUS = [("verified_yes", "Verified accessible"), ("verified_no", "Verified not accessible"), ("unknown", "Unknown")]
EPISTEMIC = [("observed", "Observed"), ("reported", "Reported"), ("inferred", "Inferred"),
             ("generated", "Generated"), ("simulated", "Simulated")]
VERIFICATION = [("unverified", "Unverified"), ("verified", "Verified"), ("rejected", "Rejected"), ("superseded", "Superseded")]
VISIBILITY = [("public", "Public"), ("restricted", "Restricted"), ("private", "Private")]


class CategoryHazard(models.Model):
    """Declared freshness model per category: Gamma(shape, rate) prior on the
    daily hazard of a material change, plus the published decision constants.
    A governance body edits these rows; the maths is in pc_core.freshness."""
    category = models.CharField(max_length=32, choices=CATEGORIES, unique=True)
    shape = models.FloatField(default=2.0)
    rate = models.FloatField(default=200.0, help_text="Prior exposure in days; mean hazard = shape/rate per day")
    changes_observed = models.PositiveIntegerField(default=0)
    exposure_days = models.FloatField(default=0.0)
    sensitivity = models.FloatField(default=0.95)
    specificity = models.FloatField(default=0.95)
    repair_value = models.FloatField(default=3.0, help_text="Value of restoring a stale listing; must be > 0 or old listings starve")
    check_cost = models.FloatField(default=0.1)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["category"]

    def __str__(self):
        return f"{self.get_category_display()} hazard"

    def posterior(self) -> GammaRate:
        return GammaRate(self.shape, self.rate).update(self.changes_observed, self.exposure_days)

    @classmethod
    def for_category(cls, category: str) -> "CategoryHazard":
        obj, _ = cls.objects.get_or_create(category=category)
        return obj


class Resource(WorkflowMixin, DraftStateMixin, LockableMixin, RevisionMixin, index.Indexed, models.Model):
    """The published projection of one family resource. `live` is Wagtail's
    published flag; drafts and revisions are managed by the mixins."""
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=32, choices=CATEGORIES)
    community = models.CharField(max_length=32, choices=COMMUNITIES, default="crescent_city")
    min_age = models.PositiveSmallIntegerField(default=0)
    max_age = models.PositiveSmallIntegerField(default=18)
    cost_status = models.CharField(max_length=16, choices=COST_STATUS, default="unknown")
    cost_usd = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    accessibility_status = models.CharField(max_length=16, choices=ACCESS_STATUS, default="unknown")
    access_notes = models.CharField(max_length=300, blank=True)
    location = gis.PointField(srid=4326, null=True, blank=True, help_text="Authoritative point; H3 is derived")
    geo_source = models.CharField(max_length=200, blank=True, help_text="Where the coordinates came from (e.g. CDE directory, NPS page, OSM feature)")
    h3_res_8 = models.CharField(max_length=16, blank=True, editable=False)
    h3_cells = models.JSONField(default=dict, blank=True, editable=False, help_text="Exact containing cells, res 8..12 (public venues only)")
    verification_method = models.CharField(max_length=24, choices=VERIFICATION_METHOD, default="none")
    hours_note = models.CharField(max_length=300, blank=True)
    cost_note = models.CharField(max_length=300, blank=True)
    address = models.CharField(max_length=300, blank=True)
    trail_info = models.JSONField(null=True, blank=True, help_text="length_miles, surface, family_note, warnings")
    website_url = models.URLField(blank=True)
    phone_public = models.CharField(max_length=40, blank=True)
    public_source_url = models.URLField(blank=True)
    source_note = models.CharField(max_length=300, blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    last_material_change_at = models.DateTimeField(null=True, blank=True)
    visibility = models.CharField(max_length=16, choices=VISIBILITY, default="public")
    is_sensitive = models.BooleanField(default=False, help_text="Sensitive places are never shown at fine resolution")
    is_fictional = models.BooleanField(default=False, help_text="Demo fixture; never counts toward the 40 verified listings")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Fail closed: Wagtail's DraftStateMixin defaults `live` to True; nothing here is public until published.
    live = models.BooleanField(default=False, editable=False)

    search_fields = [index.SearchField("name"), index.SearchField("description"), index.FilterField("category")]

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["h3_res_8"], name="atlas_res_h3r8"),                     # cell lookups and public aggregates
            models.Index(fields=["live", "visibility", "is_sensitive"], name="atlas_res_public"),  # the public projection filter
            models.Index(fields=["category", "community"], name="atlas_res_facets"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:160]
        if self.location is not None:
            try:
                from pc_core.h3_index import cell_for, venue_cells
                self.h3_res_8 = cell_for(self.location.y, self.location.x, 8)
                # exact fine cells only for non-sensitive public venues
                self.h3_cells = {} if self.is_sensitive else {str(r): c for r, c in venue_cells(self.location.y, self.location.x).items()}
            except Exception:
                self.h3_res_8 = ""
                self.h3_cells = {}
        else:
            self.h3_cells = {}
        super().save(*args, **kwargs)

    # ---- freshness (declared model, see research/04) ----
    @property
    def group(self) -> str:
        return CATEGORY_GROUP.get(self.category, "attractions")

    @property
    def group_label(self) -> str:
        return GROUP_LABEL[self.group]

    @property
    def age_days(self) -> float | None:
        if not self.last_verified_at:
            return None
        return max(0.0, (timezone.now() - self.last_verified_at).total_seconds() / 86400)

    @property
    def p_current(self) -> float | None:
        if self.age_days is None:
            return None
        return prob_current(CategoryHazard.for_category(self.category).posterior(), self.age_days)

    @property
    def freshness_band(self) -> str:
        p = self.p_current
        if p is None:
            return "unverified"
        if p >= 0.8:
            return "recently_verified"
        if p >= 0.5:
            return "verified_this_season"
        return "needs_recheck"

    @property
    def review_priority(self) -> float | None:
        if self.age_days is None:
            return None
        h = CategoryHazard.for_category(self.category)
        return review_priority(h.posterior(), self.age_days, h.sensitivity, h.specificity,
                               check_cost=h.check_cost, repair_value=h.repair_value)

    def verified_claims(self):
        return self.claims.filter(verification_status="verified", epistemic_type__in=("observed", "reported"))

    def public_dict(self) -> dict:
        return {
            "id": self.pk, "slug": self.slug, "name": self.name, "description": self.description,
            "category": self.category, "category_label": self.get_category_display(),
            "group": self.group, "group_label": self.group_label,
            "community": self.community, "community_label": self.get_community_display(),
            "min_age": self.min_age, "max_age": self.max_age,
            "cost_status": self.cost_status, "cost_usd": float(self.cost_usd) if self.cost_usd is not None else None,
            "accessibility_status": self.accessibility_status, "access_notes": self.access_notes,
            "lon": self.location.x if self.location else None, "lat": self.location.y if self.location else None,
            "website_url": self.website_url, "phone_public": self.phone_public,
            "public_source_url": self.public_source_url, "source_note": self.source_note,
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
            "age_days": round(self.age_days, 1) if self.age_days is not None else None,
            "p_current": round(self.p_current, 3) if self.p_current is not None else None,
            "freshness_band": self.freshness_band, "is_fictional": self.is_fictional,
            "verification_method": self.verification_method, "verification_label": self.get_verification_method_display(),
            "address": self.address, "hours_note": self.hours_note, "cost_note": self.cost_note, "geo_source": self.geo_source,
            "h3_res_8": self.h3_res_8, "h3_res_11": self.h3_cells.get("11", ""), "trail_info": self.trail_info,
            "verified_claim_count": self.verified_claims().count(),
        }


class Claim(models.Model):
    """One typed piece of evidence about one attribute of a resource."""
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="claims")
    attribute = models.CharField(max_length=64)
    raw_value = models.JSONField()
    epistemic_type = models.CharField(max_length=16, choices=EPISTEMIC)
    source_uri = models.URLField(blank=True)
    source_id = models.CharField(max_length=64, blank=True)
    source_revision = models.CharField(max_length=128, blank=True, help_text="ETag/hash; identical bytes are one observation")
    source_observed_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(default=timezone.now)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    verification_status = models.CharField(max_length=16, choices=VERIFICATION, default="unverified")
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    verified_at = models.DateTimeField(null=True, blank=True)
    audit_hash = models.CharField(max_length=64, blank=True, help_text="Hash of the audit entry recording verification")
    access_level = models.CharField(max_length=16, choices=VISIBILITY, default="restricted")
    supports_publication = models.BooleanField(default=False)

    class Meta:
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(fields=["resource", "attribute", "source_revision"], name="one_observation_per_revision",
                                    condition=~models.Q(source_revision="")),
        ]

    def __str__(self):
        return f"{self.resource.name}: {self.attribute} ({self.epistemic_type}, {self.verification_status})"

    def verify(self, user, note: str = "") -> "AuditEntry":
        """Server-side verification by an authorised role; writes the audit entry."""
        if self.epistemic_type not in ("observed", "reported"):
            raise ValueError("only observed/reported claims can be verified as evidence")
        entry = AuditEntry.append({
            "event": "claim_verified", "claim_id": self.pk, "resource_id": self.resource_id,
            "attribute": self.attribute, "epistemic_type": self.epistemic_type,
            "by_user": user.get_username() if user else None, "note": note,
            "timestamp": timezone.now().isoformat(),
        })
        self.verification_status = "verified"
        self.verified_by = user
        self.verified_at = timezone.now()
        self.audit_hash = entry.hash
        self.supports_publication = True
        self.save()
        return entry


class Event(DraftStateMixin, RevisionMixin, models.Model):
    resource = models.ForeignKey(Resource, null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    recurrence_rule = models.CharField(max_length=200, blank=True, help_text="Plain text or RRULE; expiry is by clock time")
    location = gis.PointField(srid=4326, null=True, blank=True)
    source_url = models.URLField(blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    cost_status = models.CharField(max_length=16, choices=COST_STATUS, default="unknown")
    min_age = models.PositiveSmallIntegerField(default=0)
    max_age = models.PositiveSmallIntegerField(default=18)
    is_fictional = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    live = models.BooleanField(default=False, editable=False)  # fail closed, as for Resource

    class Meta:
        ordering = ["start_at"]

    def __str__(self):
        return self.title

    @property
    def is_past(self) -> bool:
        """Clock-time expiry (DraftStateMixin owns the `expired` field)."""
        end = self.end_at or self.start_at + timedelta(hours=2)
        return end < timezone.now()

    def public_dict(self) -> dict:
        return {"id": self.pk, "title": self.title, "description": self.description,
                "start_at": self.start_at.isoformat(), "end_at": self.end_at.isoformat() if self.end_at else None,
                "recurrence_rule": self.recurrence_rule, "is_past": self.is_past,
                "lon": self.location.x if self.location else None, "lat": self.location.y if self.location else None,
                "source_url": self.source_url, "cost_status": self.cost_status,
                "min_age": self.min_age, "max_age": self.max_age, "is_fictional": self.is_fictional,
                "resource_slug": self.resource.slug if self.resource else None,
                "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None}


class Submission(models.Model):
    """A public or contributor suggestion. Never auto-publishes."""
    STATUS = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("needs_clarification", "Needs clarification")]
    target_resource = models.ForeignKey(Resource, null=True, blank=True, on_delete=models.SET_NULL, related_name="submissions")
    submitter = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    proposed_payload = models.JSONField()
    status = models.CharField(max_length=24, choices=STATUS, default="pending")
    review_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Submission {self.pk} ({self.status})"

    def to_claim(self, reviewer) -> Claim:
        """A reviewer turns a submission into an unverified `reported` claim."""
        attribute = self.proposed_payload.get("attribute", "suggestion")
        return Claim.objects.create(
            resource=self.target_resource, attribute=attribute, raw_value=self.proposed_payload,
            epistemic_type="reported", source_uri=self.proposed_payload.get("source_url", ""),
            submitted_by=self.submitter, access_level="restricted",
        )


class StewardEntry(models.Model):
    """What a steward told Lumen, what Lumen drafted, and how the entry held up when re-checked.
    The original-evidence layer for steward trust (pc_core.steward); recorded only under a signed
    steward agreement. Ordinary questions are never stored."""
    OUTCOMES = [("pending", "Not yet re-checked"), ("still_right", "Still right"), ("changed_since", "Changed since"),
                ("wrong_at_entry", "Wrong when entered"), ("cant_tell", "Can't tell")]
    steward = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    steward_name = models.CharField(max_length=150, help_text="Kept with the entry for accountability, even after the steward steps down")
    instruction = models.TextField(help_text="What the steward told Lumen, word for word")
    lumen_draft = models.JSONField(default=dict, blank=True)
    submission = models.ForeignKey(Submission, null=True, blank=True, on_delete=models.SET_NULL, related_name="steward_entries")
    agreement_version = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)
    outcome = models.CharField(max_length=16, choices=OUTCOMES, default="pending")
    outcome_at = models.DateTimeField(null=True, blank=True)
    outcome_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    outcome_evidence_dated = models.BooleanField(default=False, help_text="The checker has dated evidence of when it changed")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.steward_name}: {self.instruction[:60]}"


def member_ref(user) -> str:
    """How a member appears in the sealed log: a number, never a name or email, so deleting
    the account leaves nothing personal behind. Stewards' own decisions stay named."""
    return f"member-{user.pk}"


class AuditEntry(models.Model):
    """Hash-chained, append-only log (pc_core.audit_chain semantics)."""
    index = models.PositiveIntegerField(unique=True)
    prev_hash = models.CharField(max_length=64)
    payload = models.JSONField()
    hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["index"]

    def __str__(self):
        return f"#{self.index} {self.payload.get('event', self.payload.get('action_proposed', ''))}"

    @classmethod
    def append(cls, payload: dict, require_decision_fields: bool = False) -> "AuditEntry":
        if require_decision_fields:
            missing = [k for k in REQUIRED_DECISION_FIELDS if k not in payload]
            if missing:
                raise ValueError(f"decision record missing fields: {missing}")
        payload = json.loads(json.dumps(payload, default=str))
        with transaction.atomic():
            last = cls.objects.select_for_update().order_by("-index").first()
            prev = last.hash if last else GENESIS
            idx = last.index + 1 if last else 0
            return cls.objects.create(index=idx, prev_hash=prev, payload=payload, hash=entry_hash(prev, payload))

    @classmethod
    def verify_chain(cls) -> tuple[bool, int | None]:
        prev = GENESIS
        for i, e in enumerate(cls.objects.order_by("index")):
            if e.index != i or e.prev_hash != prev:
                return False, i
            redacted = e.payload.get("redacted") is True and e.payload.get("original_hash") == e.hash
            if not redacted and entry_hash(prev, e.payload) != e.hash:
                return False, i
            prev = e.hash
        return True, None


class ProjectionVersion(models.Model):
    """Monotonic version of the published projection; bumps on every publish.
    Cache keys and the Compass working context are invalidated by it."""
    version = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def current(cls) -> int:
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj.version

    @classmethod
    def bump(cls) -> int:
        with transaction.atomic():
            obj, _ = cls.objects.select_for_update().get_or_create(pk=1)
            obj.version += 1
            obj.save()
            return obj.version


class ReviewNote(models.Model):
    """A reviewer's reply to one of the 'Questions for Kim'. Private to stewards; never published."""
    question_key = models.CharField(max_length=40)
    reviewer = models.CharField(max_length=80, blank=True)
    response = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reviewer or 'anonymous'} on {self.question_key}"
