"""Palette optimiser: river, redwood and ocean colours tuned in OKLCH for
WCAG 2.2 contrast, written to web/static/style/tokens.json.

Anchors (the owner can change the hue/chroma anchors; lightness is solved):
- river   : Smith River water, the clear emerald-teal of a clean gravel-bed river
- redwood : bark, a deep warm red-brown; needles, a muted forest green
- ocean   : the cold Pacific, blue-grey; foam/fog for surfaces
- sand/gravel: warm neutrals for land

Method: colours are expressed in OKLCH (perceptually uniform; Bjorn Ottosson
2020). For each text/background pair we keep hue and chroma fixed and solve
lightness by bisection until the WCAG 2.2 contrast ratio meets the target
(7:1 primary text, 4.5:1 secondary text and UI, 3:1 large text/graphics).
The map palette keeps water as the only blue family, parks the only green
family, and verifies that land/water/park/road are pairwise distinguishable
(ΔE_OK >= 0.04). Run: python web/tools/palette.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "static" / "style" / "tokens.json"


# ---- colour maths ---------------------------------------------------------------
def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def oklch_to_rgb(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(linear_to_srgb(x) for x in (r, g, bb))


def rgb_to_oklab(r, g, b):
    r, g, b = (srgb_to_linear(x) for x in (r, g, b))
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def hexstr(rgb):
    return "#%02x%02x%02x" % tuple(round(max(0, min(1, c)) * 255) for c in rgb)


def luminance(rgb):
    r, g, b = (srgb_to_linear(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def delta_e(a, b):
    la, lb = rgb_to_oklab(*a), rgb_to_oklab(*b)
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(la, lb)))


def solve_lightness(C, h, bg, target, darker=True):
    """Bisection on L so that contrast(oklch(L,C,h), bg) >= target, as light (or dark) as allowed."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        ok = contrast(oklch_to_rgb(mid, C, h), bg) >= target
        if darker:
            # we want the lightest L that still passes (text on light bg): passing means we can go lighter
            lo, hi = (mid, hi) if ok else (lo, mid)
        else:
            lo, hi = (lo, mid) if ok else (mid, hi)
    L = lo if darker else hi
    return oklch_to_rgb(L, C, h), L


# ---- anchors ----------------------------------------------------------------------
# Anchors re-measured from the owner's photographs (chroma-weighted hue histograms, 14 Oct 2026):
# Smith River pools ~250 (sky-reflecting blue), river-bank and canopy greens 110-120, ocean/fog ~262,
# sunset gold 75-90, sand and shells 60-90. The accent stays a teal between river and green.
H = {"river": 245.0, "emerald": 160.0, "ocean": 262.0, "bark": 32.0, "needle": 112.0, "sand": 80.0, "fog": 240.0, "kelp": 120.0, "teal": 200.0}

light_bg = oklch_to_rgb(0.962, 0.012, H["sand"])        # warm paper page (space-zero-informed)
surface = (1.0, 1.0, 1.0)
land = oklch_to_rgb(0.952, 0.014, H["sand"])            # warm sand-grey land
dark_bg = oklch_to_rgb(0.21, 0.02, H["ocean"])          # night ocean
dark_surface = oklch_to_rgb(0.26, 0.02, H["ocean"])

ink, _ = solve_lightness(0.03, H["ocean"], light_bg, 10.5)             # primary text: deep ocean ink
ink2, _ = solve_lightness(0.03, H["ocean"], light_bg, 5.5)            # secondary
accent, _ = solve_lightness(0.11, H["teal"], surface, 4.5)            # teal between river blue and canopy green (AA on white)
accent_on = (1.0, 1.0, 1.0)
emerald, _ = solve_lightness(0.12, H["emerald"], surface, 4.5)        # river-emerald for "free"/verified
bark, _ = solve_lightness(0.08, H["bark"], surface, 4.5)              # redwood bark for warnings/stale
needle, _ = solve_lightness(0.08, H["needle"], surface, 4.5)          # needle green secondary accent
sensitive, _ = solve_lightness(0.10, 20.0, surface, 4.5)
unknown, _ = solve_lightness(0.015, H["fog"], surface, 4.5)

d_ink, _ = solve_lightness(0.02, H["fog"], dark_bg, 7.0, darker=False)
d_ink2, _ = solve_lightness(0.02, H["fog"], dark_bg, 4.5, darker=False)
d_accent, _ = solve_lightness(0.10, H["teal"], dark_surface, 4.5, darker=False)
d_emerald, _ = solve_lightness(0.11, H["emerald"], dark_surface, 4.5, darker=False)
d_bark, _ = solve_lightness(0.09, H["bark"], dark_surface, 4.5, darker=False)

# map (light): water is the only blue family, parks the only green family
water = oklch_to_rgb(0.90, 0.040, H["river"])
water_deep = oklch_to_rgb(0.86, 0.055, H["ocean"])
park = oklch_to_rgb(0.90, 0.055, H["needle"])
park_light = oklch_to_rgb(0.94, 0.035, H["needle"])
wood = oklch_to_rgb(0.88, 0.055, H["kelp"])
wood_light = oklch_to_rgb(0.93, 0.035, H["kelp"])
sand = oklch_to_rgb(0.95, 0.03, H["sand"])
road = (1.0, 1.0, 1.0)
road_major = oklch_to_rgb(0.985, 0.02, H["sand"])
road_minor = oklch_to_rgb(0.985, 0.006, H["sand"])
road_casing = oklch_to_rgb(0.86, 0.02, H["sand"])
buildings = oklch_to_rgb(0.91, 0.015, H["bark"])
civic = oklch_to_rgb(0.93, 0.015, H["bark"])
label, _ = solve_lightness(0.03, H["ocean"], land, 4.5)
label_muted, _ = solve_lightness(0.02, H["ocean"], land, 3.0)
boundary = oklch_to_rgb(0.70, 0.06, H["bark"])
hill_shadow = oklch_to_rgb(0.55, 0.05, H["bark"])
water_label, _ = solve_lightness(0.08, H["ocean"], water, 4.5)

checks = {
    "ink_on_bg": contrast(ink, light_bg), "ink2_on_bg": contrast(ink2, light_bg), "accent_on_surface": contrast(accent, surface),
    "white_on_accent": contrast(accent_on, accent), "emerald_on_surface": contrast(emerald, surface), "bark_on_surface": contrast(bark, surface),
    "label_on_land": contrast(label, land), "water_label_on_water": contrast(water_label, water),
    "dark_ink_on_bg": contrast(d_ink, dark_bg), "dark_accent_on_surface": contrast(d_accent, dark_surface),
    "dE_land_water": delta_e(land, water), "dE_land_park": delta_e(land, park), "dE_water_park": delta_e(water, park),
    "dE_road_land": delta_e(road, land), "dE_park_wood": delta_e(park, wood),
}
assert checks["ink_on_bg"] >= 10 and checks["ink2_on_bg"] >= 5.5 and checks["accent_on_surface"] >= 4.5, checks
assert checks["white_on_accent"] >= 4.5 and checks["label_on_land"] >= 4.5, checks
assert min(checks["dE_land_water"], checks["dE_land_park"], checks["dE_water_park"], checks["dE_road_land"]) >= 0.04, checks

# Categorical colours for Kim's nine groups: hue spread around the wheel starting at the river hue,
# fixed lightness/chroma so no group shouts; checked for pairwise separation and white-stroke contrast.
GROUP_ORDER = ["parks", "pools", "attractions", "water", "nature", "learning", "arts", "services", "programs"]
GROUP_HUES = {"parks": 145, "pools": 212, "attractions": 40, "water": 248, "nature": 108, "learning": 285, "arts": 338, "services": 310, "programs": 72}
GROUP_L = {"parks": 0.52, "pools": 0.55, "attractions": 0.60, "water": 0.63, "nature": 0.45, "learning": 0.55, "arts": 0.58, "services": 0.49, "programs": 0.62}
group_rgb = {g: oklch_to_rgb(GROUP_L[g], 0.12, GROUP_HUES[g]) for g in GROUP_ORDER}
_min_de = min(delta_e(group_rgb[a], group_rgb[b]) for i, a in enumerate(GROUP_ORDER) for b in GROUP_ORDER[i + 1:])
_min_white = min(contrast(group_rgb[g], (1, 1, 1)) for g in GROUP_ORDER)
checks["dE_min_between_groups"] = _min_de
checks["min_group_on_white"] = _min_white
assert _min_de >= 0.05 and _min_white >= 3.0, (_min_de, _min_white)

tokens = {
    "name": "Pleasant Crescent palette v3: anchors measured from the owner's photographs; OKLCH-solved for WCAG 2.2",
    "method": "hue/chroma anchors fixed; lightness solved by bisection for contrast targets; see web/tools/palette.py",
    "anchors_oklch_hue": H,
    "contrast_checks": {k: round(v, 3) for k, v in checks.items()},
    "ui": {
        "bg": hexstr(light_bg), "surface": hexstr(surface), "ink": hexstr(ink), "ink_2": hexstr(ink2),
        "accent": hexstr(accent), "accent_on": hexstr(accent_on), "accent_2": hexstr(bark), "free": hexstr(emerald), "verified": hexstr(emerald),
        "stale": hexstr(bark), "needle": hexstr(needle), "unknown": hexstr(unknown), "sensitive": hexstr(sensitive),
        "paper": hexstr(light_bg),
        "radius": "14px", "font_ui": "system-ui, -apple-system, 'Segoe UI', Roboto, Inter, sans-serif",
    },
    "ui_dark": {
        "bg": hexstr(dark_bg), "surface": hexstr(dark_surface), "ink": hexstr(d_ink), "ink_2": hexstr(d_ink2),
        "accent": hexstr(d_accent), "accent_on": hexstr(dark_bg), "accent_2": hexstr(d_bark), "free": hexstr(d_emerald), "verified": hexstr(d_emerald),
        "stale": hexstr(d_bark), "unknown": hexstr(d_ink2), "sensitive": hexstr(d_bark),
    },
    "map": {
        "land": hexstr(land), "water": hexstr(water), "water_deep": hexstr(water_deep), "water_label": hexstr(water_label),
        "park": hexstr(park), "park_light": hexstr(park_light), "wood": hexstr(wood), "wood_light": hexstr(wood_light),
        "sand": hexstr(sand), "urban": hexstr(oklch_to_rgb(0.94, 0.012, H["sand"])), "farmland": hexstr(oklch_to_rgb(0.94, 0.03, H["kelp"])),
        "civic": hexstr(civic), "industrial": hexstr(oklch_to_rgb(0.92, 0.01, H["fog"])), "pedestrian": hexstr(oklch_to_rgb(0.95, 0.012, H["sand"])),
        "buildings": hexstr(buildings), "boundary": hexstr(boundary), "railway": hexstr(oklch_to_rgb(0.75, 0.01, H["fog"])),
        "road": hexstr(road), "road_major": hexstr(road_major), "road_minor": hexstr(road_minor), "road_casing": hexstr(road_casing),
        "label": hexstr(label), "label_muted": hexstr(label_muted), "hill_shadow": hexstr(hill_shadow), "hill_light": "#ffffff",
        "pois": {"blue": hexstr(accent), "green": hexstr(emerald), "lapis": hexstr(oklch_to_rgb(0.5, 0.11, H["ocean"])),
                 "pink": hexstr(oklch_to_rgb(0.55, 0.10, 350)), "red": hexstr(bark), "slategray": hexstr(ink2),
                 "tangerine": hexstr(oklch_to_rgb(0.58, 0.12, 55)), "turquoise": hexstr(oklch_to_rgb(0.58, 0.10, H["teal"]))},
        "hex_venue": hexstr(accent), "hex_venue_fill": hexstr(oklch_to_rgb(0.75, 0.09, H["teal"])),
    },
    "groups": {g: {"color": hexstr(group_rgb[g]), "fill": hexstr(oklch_to_rgb(0.80, 0.07, GROUP_HUES[g])),
                   "dark": hexstr(oklch_to_rgb(0.72, 0.11, GROUP_HUES[g]))} for g in GROUP_ORDER},
    "logo": {"disc": hexstr(oklch_to_rgb(0.80, 0.10, 75)), "shadow": hexstr(oklch_to_rgb(0.40, 0.06, H["ocean"])),
             "ring": hexstr(accent), "glow": hexstr(oklch_to_rgb(0.92, 0.05, H["river"]))},
    "sprite_url": "/static/sprites/light",
}
OUT.write_text(json.dumps(tokens, indent=1) + "\n")
print("wrote", OUT)
for k, v in checks.items():
    print(f"  {k:28} {v:.2f}")
print("ui:", {k: v for k, v in tokens["ui"].items() if k not in ("radius", "font_ui")})
