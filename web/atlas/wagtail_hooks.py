"""Wagtail admin: resources and events as snippets with drafts, revisions,
locking and moderation workflows; submissions and the audit log read-only-ish."""
from django import forms
from wagtail import hooks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import AuditEntry, CategoryHazard, Claim, Event, Resource, Submission


class ResourceViewSet(SnippetViewSet):
    model = Resource
    icon = "site"
    list_display = ["name", "category", "community", "cost_status", "accessibility_status", "live", "last_verified_at", "verification_method", "is_fictional"]
    list_filter = ["category", "community", "cost_status", "accessibility_status", "is_fictional"]
    search_fields = ["name", "description"]
    panels = [
        MultiFieldPanel([FieldPanel("name"), FieldPanel("slug"), FieldPanel("description"), FieldPanel("address"), FieldPanel("hours_note"), FieldPanel("cost_note"), FieldPanel("verification_method"), FieldPanel("is_fictional")], "Listing"),
        MultiFieldPanel([FieldPanel("category"), FieldPanel("community"), FieldPanel("min_age"), FieldPanel("max_age"),
                         FieldPanel("cost_status"), FieldPanel("cost_usd"), FieldPanel("accessibility_status"), FieldPanel("access_notes")], "Facets"),
        MultiFieldPanel([FieldPanel("geo_source"), FieldPanel("location", widget=forms.TextInput(attrs={"placeholder": "POINT(-124.1865 41.7455)  (lon lat, WGS84)"}),
                                    help_text="Enter WKT: POINT(lon lat). A picker on our own tiles replaces this in the next iteration; "
                                              "the default Django map widget is not used because it loads tiles from openstreetmap.org."),
                         FieldPanel("is_sensitive"), FieldPanel("visibility")], "Location (authoritative point; H3 derived on save)"),
        MultiFieldPanel([FieldPanel("website_url"), FieldPanel("phone_public"), FieldPanel("public_source_url"), FieldPanel("source_note"),
                         FieldPanel("last_verified_at"), FieldPanel("last_material_change_at")], "Source and freshness"),
    ]


class EventViewSet(SnippetViewSet):
    model = Event
    icon = "date"
    list_display = ["title", "start_at", "end_at", "cost_status", "live", "is_fictional"]
    panels = [FieldPanel("title"), FieldPanel("description"), FieldPanel("resource"), FieldPanel("start_at"), FieldPanel("end_at"),
              FieldPanel("recurrence_rule"), FieldPanel("location", widget=forms.TextInput(attrs={"placeholder": "POINT(lon lat)"})), FieldPanel("source_url"), FieldPanel("cost_status"),
              FieldPanel("min_age"), FieldPanel("max_age"), FieldPanel("last_verified_at"), FieldPanel("is_fictional")]


class ClaimViewSet(SnippetViewSet):
    model = Claim
    icon = "doc-full-inverse"
    list_display = ["resource", "attribute", "epistemic_type", "verification_status", "received_at", "verified_by"]
    list_filter = ["epistemic_type", "verification_status"]
    panels = [FieldPanel("resource"), FieldPanel("attribute"), FieldPanel("raw_value"), FieldPanel("epistemic_type"),
              FieldPanel("source_uri"), FieldPanel("source_revision"), FieldPanel("source_observed_at"), FieldPanel("access_level")]


class SubmissionViewSet(SnippetViewSet):
    model = Submission
    icon = "mail"
    list_display = ["__str__", "target_resource", "status", "submitted_at"]
    list_filter = ["status"]
    panels = [FieldPanel("target_resource"), FieldPanel("proposed_payload"), FieldPanel("status"), FieldPanel("review_note")]


class HazardViewSet(SnippetViewSet):
    model = CategoryHazard
    icon = "cog"
    list_display = ["category", "shape", "rate", "changes_observed", "exposure_days", "repair_value", "check_cost"]
    panels = [FieldPanel("category"), FieldPanel("shape"), FieldPanel("rate"), FieldPanel("changes_observed"), FieldPanel("exposure_days"),
              FieldPanel("sensitivity"), FieldPanel("specificity"), FieldPanel("repair_value"), FieldPanel("check_cost"), FieldPanel("notes")]


class AuditViewSet(SnippetViewSet):
    model = AuditEntry
    icon = "lock"
    list_display = ["index", "__str__", "hash", "created_at"]
    panels = [FieldPanel("payload")]
    inspect_view_enabled = True


class AtlasGroup(SnippetViewSetGroup):
    menu_label = "Atlas"
    menu_icon = "globe"
    items = (ResourceViewSet, EventViewSet, ClaimViewSet, SubmissionViewSet, HazardViewSet, AuditViewSet)


register_snippet(AtlasGroup)


@hooks.register("construct_main_menu")
def hide_unused(request, menu_items):
    menu_items[:] = [m for m in menu_items if m.name not in ("explorer",)]
