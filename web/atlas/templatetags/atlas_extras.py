import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def get_item(d, key):
    try:
        return d.get(key)
    except AttributeError:
        return None


@register.filter
def tojson(value):
    return mark_safe(json.dumps(value).replace("<", "\\u003c"))
