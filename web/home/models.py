from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class HomePage(Page):
    """Owner-editable home page: hero copy, one optional question, intro."""
    strapline = models.CharField(max_length=160, default="A friendly atlas for families, neighbours and newcomers.", blank=True)
    intro = RichTextField(blank=True)
    optional_question = models.CharField(max_length=120, default="Just show free things?", blank=True)

    content_panels = Page.content_panels + [FieldPanel("strapline"), FieldPanel("intro"), FieldPanel("optional_question")]
    template = "home/home_page.html"
    max_count = 1

    def get_context(self, request, *args, **kwargs):
        from atlas.models import Event, Resource
        from django.utils import timezone
        ctx = super().get_context(request, *args, **kwargs)
        from atlas.models import GROUPS
        ctx["groups"] = GROUPS
        ctx["group_blurbs"] = {
            "parks": "Playgrounds, picnic lawns and the county parks, with access notes where known.",
            "pools": "The municipal pool, indoor play and sports halls for wet days.",
            "attractions": "The lighthouse, the aquarium, the museum and the visitor centres.",
            "water": "River put-ins and swimming holes on the Smith, and the beaches.",
            "nature": "Short redwood and coastal trails that work with children, with warnings stated.",
            "learning": "Schools, preschools, childcare, the college and classes.",
            "arts": "Galleries, music and making, as they are verified.",
            "services": "Libraries and family services with their official sources.",
            "programs": "After-school programmes, youth clubs and the people to call.",
        }
        ctx["featured"] = Resource.objects.filter(live=True, visibility="public").order_by("-last_verified_at")[:4]
        ctx["upcoming"] = Event.objects.filter(live=True, start_at__gte=timezone.now()).order_by("start_at")[:3]
        return ctx
