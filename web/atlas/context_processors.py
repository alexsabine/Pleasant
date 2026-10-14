import json
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def _tokens():
    with open(settings.BASE_DIR / "static" / "style" / "tokens.json", encoding="utf8") as fh:
        return json.load(fh)


def site_tokens(request):
    return {"tokens": _tokens(), "private_mode": settings.PC_PRIVATE_MODE,
            "map_center": settings.PC_MAP_CENTER, "map_zoom": settings.PC_MAP_ZOOM}
