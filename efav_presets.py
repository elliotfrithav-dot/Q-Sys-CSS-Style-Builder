"""
efav_presets.py — EFAV-specific data for the generic css_builder_core engine.

Nothing here is load-bearing for the engine itself (css_builder_core.py has
no knowledge of EFAV, theme names, or hex values) — this is the swappable
preset layer both build_icons.py (the stock-theme batch build) and
css_builder_gui.py (the "duplicate an existing theme" starting point) import.
Kept separate from the start so v2 commercial packaging (CSS_STYLE_BUILDER.md
§7/§8.4) doesn't need to extract EFAV specifics out of the engine later.
"""
import sys
from pathlib import Path

# When packaged with PyInstaller (see PACKAGING.md), bundled resources land
# in sys._MEIPASS at runtime, not next to this .py file — this file itself
# is compiled into the exe, so __file__ can't locate Icons/ or fonts/ there.
if getattr(sys, "frozen", False):
    ROOT = Path(sys._MEIPASS)
else:
    ROOT = Path(__file__).parent
ICONS_DIR = ROOT / "Icons"
FONT_PATH = ROOT / "fonts" / "IBMPlexSans-Medium-subset.ttf"
FONT_FAMILY = "IBM Plex Sans"
FONT_LICENSE_PATH = ROOT / "fonts" / "IBM_Plex_Sans" / "OFL.txt"
# Builds go straight into the real Designer Styles folder — no more manual
# copy step. Matches the GUI's Install target exactly (css_builder_gui.py).
# Note the real folder is "Q-Sys Designer" (mixed case), not "Q-SYS Designer".
OUTPUT_ROOT = Path.home() / "Documents" / "QSC" / "Q-Sys Designer" / "Styles"

# Dict key = folder name = the style name Q-SYS Designer shows in its style
# dropdown. Each theme also carries "page_chrome": whether this theme owns
# page/header/footer background (False for the icon-only themes, which are
# meant to layer icon colour onto whatever page background the UCI already
# has via a different installed theme, not to also own the page).
THEMES = {
    "EFAV Navy": {
        "page_chrome": True,
        "bg": "#0D1B2A", "surface": "#1E3A5F", "surface-hi": "#2E86AB",
        "text": "#E8EEF4", "text-dim": "#8DA3BC",
        "icon": "#CBD8E6", "icon-hi": "#FFFFFF",
        "accent": "#3DA5CE", "fault": "#E63946",
    },
    "EFAV Slate Light": {
        "page_chrome": True,
        "bg": "#FFFFFF", "surface": "#E7EDF3", "surface-hi": "#2E86AB",
        "text": "#0D1B2A", "text-dim": "#5A6B7E",
        "icon": "#1E3A5F", "icon-hi": "#FFFFFF",
        "accent": "#2E86AB", "fault": "#D62839",
    },
    "EFAV Black Icons": {
        # Same as EFAV Slate Light, icon AND text colour forced to pure black.
        "page_chrome": False,
        "bg": "#FFFFFF", "surface": "#E7EDF3", "surface-hi": "#2E86AB",
        "text": "#000000", "text-dim": "#000000",
        "icon": "#000000", "icon-hi": "#FFFFFF",
        "accent": "#2E86AB", "fault": "#D62839",
    },
    "EFAV White Icons": {
        # Same as EFAV Navy, icon colour forced to pure white — needs a dark
        # backdrop to read, unlike Black Icons which is light-based.
        "page_chrome": False,
        "bg": "#0D1B2A", "surface": "#1E3A5F", "surface-hi": "#2E86AB",
        "text": "#E8EEF4", "text-dim": "#8DA3BC",
        "icon": "#FFFFFF", "icon-hi": "#FFFFFF",
        "accent": "#3DA5CE", "fault": "#E63946",
    },
    "EFAV Graphite": {
        "page_chrome": True,
        "bg": "#17181A", "surface": "#2C2F34", "surface-hi": "#E0A458",
        "text": "#F2F3F5", "text-dim": "#9BA0A8",
        "icon": "#C7CBD1", "icon-hi": "#201A0E",
        "accent": "#E0A458", "fault": "#E5544B",
    },
    "EFAV Warm Studio": {
        "page_chrome": True,
        "bg": "#FFFFFF", "surface": "#F0E8DB", "surface-hi": "#C2703D",
        "text": "#33291F", "text-dim": "#7A6E5E",
        "icon": "#5C4A34", "icon-hi": "#FFFFFF",
        "accent": "#C2703D", "fault": "#B23A2E",
    },
    "EFAV High-Contrast": {
        "page_chrome": True,
        "bg": "#000000", "surface": "#1C1F24", "surface-hi": "#00A3E0",
        "text": "#FFFFFF", "text-dim": "#B8BFC7",
        "icon": "#FFFFFF", "icon-hi": "#000000",
        "accent": "#00C2FF", "fault": "#FF4D4D",
    },
    # Indigo/Rust/Teal were originally built one-off through the GUI (Install
    # button, saved straight to the real Styles folder) before this preset
    # dict existed for them — promoted here so build_icons.py now manages and
    # protects them like every other stock theme. bg/surface/text/text-dim/
    # accent are recovered exactly from the already-installed style.css.
    # icon/icon-hi/surface-hi/fault are NOT recoverable — that build's CSS
    # never emitted those roles — so they're derived here using the same
    # formula the other themes already follow (surface-hi = accent, icon = a
    # 70% blend from text-dim toward text, icon-hi = the theme's own bg,
    # fault = the standard alarm red used elsewhere). Adjust freely in the
    # GUI's colour pickers if these derived four don't look right.
    "EFAV Indigo": {
        "page_chrome": True,
        "bg": "#1B1430", "surface": "#3D2E63", "surface-hi": "#4FBFAE",
        "text": "#EDEAF6", "text-dim": "#A79BC4",
        "icon": "#D8D2E7", "icon-hi": "#1B1430",
        "accent": "#4FBFAE", "fault": "#E63946",
    },
    "EFAV Rust": {
        "page_chrome": True,
        "bg": "#1E120C", "surface": "#4A2417", "surface-hi": "#D07D53",
        "text": "#F5EDE6", "text-dim": "#B39A88",
        "icon": "#E1D4CA", "icon-hi": "#1E120C",
        "accent": "#D07D53", "fault": "#E63946",
    },
    "EFAV Teal": {
        "page_chrome": True,
        "bg": "#0F211D", "surface": "#1B4A41", "surface-hi": "#E0932E",
        "text": "#E8F2EF", "text-dim": "#8FB0A8",
        "icon": "#CDDEDA", "icon-hi": "#0F211D",
        "accent": "#E0932E", "fault": "#E63946",
    },
}

# The "blank" GUI starting point (CSS_STYLE_BUILDER.md §3): all 9 roles
# default to EFAV Navy's values. Kept as an explicit name rather than reusing
# THEMES["EFAV Navy"] directly so callers can tell "blank start" apart from
# "user explicitly picked to duplicate EFAV Navy" if that distinction ever
# matters (e.g. analytics, or diverging the blank default from the Navy brand
# theme later without touching the real Navy preset).
BLANK_DEFAULT = {k: v for k, v in THEMES["EFAV Navy"].items() if k != "page_chrome"}

# Combined on/off icon-swap classes — UNVERIFIED, see css_builder_core.py
# docstring. Each pair is (off_slug, on_slug, combined_class_name).
TOGGLE_PAIRS = [
    ("microphone", "mic-muted", "mic-toggle"),
    ("voice", "mute", "speaker-toggle"),
]

def _find_icon_file(filename: str) -> Path:
    """Search Icons/ recursively for an exact filename. The folder gets
    reorganised periodically (folders renamed/merged) — searching by name
    instead of hardcoding a subfolder path survives that; a hardcoded path
    already broke once (see project history) when "New icons/" was dissolved
    and its contents redistributed into per-concept folders."""
    matches = list(ICONS_DIR.rglob(filename))
    if not matches:
        raise FileNotFoundError(
            f"efav_presets: expected icon file '{filename}' not found anywhere under {ICONS_DIR} "
            "— it may have been renamed or moved outside Icons/. Update TOGGLE_ON_STATE_ART."
        )
    if len(matches) > 1:
        raise FileNotFoundError(
            f"efav_presets: '{filename}' matches more than one file under {ICONS_DIR}: "
            f"{[str(m) for m in matches]} — TOGGLE_ON_STATE_ART needs an unambiguous name."
        )
    return matches[0]


# Purpose-drawn on-state art for the toggle pairs above — used instead of the
# plain off-state icon (which would just get tinted to the ordinary `icon`
# colour, losing the point of having dedicated mute art). Still tinted to
# each theme's `fault` role at build time, just from a better base shape.
# Keyed by on_slug (matches TOGGLE_PAIRS' second element). Resolved by
# filename search (_find_icon_file), not a hardcoded folder — see its
# docstring for why.
TOGGLE_ON_STATE_ART = {
    "mic-muted": _find_icon_file("Mic Muted - Red.png"),
    "mute": _find_icon_file("Speaker Muted - Red.png"),
}

# These two files are ONLY used via TOGGLE_ON_STATE_ART above (tinted to
# `fault` per theme) — excluded from the generic icon scan so they don't also
# become a redundant ordinary .icon-<slug> class tinted to the plain `icon`
# colour, which would defeat the point of having purpose-drawn mute art.
# "Mic Muted 2 - Red.png" is deliberately NOT excluded — it becomes an
# ordinary icon class like everything else (per-job decision, not a rule).
EXCLUDED_ICON_FILES = set(TOGGLE_ON_STATE_ART.values())

# Pre-vetted font dropdown (CSS_STYLE_BUILDER.md §2). Each entry points at a
# Medium-weight source TTF; css_builder_core.subset_font() subsets it on
# demand at build time — these are the FULL source files, not pre-subset.
FONT_DIR = ROOT / "fonts"
FONT_OPTIONS = {
    "IBM Plex Sans": {
        "path": FONT_DIR / "IBM_Plex_Sans" / "static" / "IBMPlexSans-Medium.ttf",
        "license": FONT_DIR / "IBM_Plex_Sans" / "OFL.txt",
    },
    "Inter": {
        "path": FONT_DIR / "Inter" / "Inter-Medium.ttf",
        "license": FONT_DIR / "Inter" / "OFL.txt",
    },
    "IBM Plex Sans Condensed": {
        "path": FONT_DIR / "IBM_Plex_Sans" / "static" / "IBMPlexSans_Condensed-Medium.ttf",
        "license": FONT_DIR / "IBM_Plex_Sans" / "OFL.txt",
    },
    "Barlow Semi Condensed": {
        "path": FONT_DIR / "Barlow_Semi_Condensed,IBM_Plex_Sans" / "Barlow_Semi_Condensed" / "BarlowSemiCondensed-Medium.ttf",
        "license": FONT_DIR / "Barlow_Semi_Condensed,IBM_Plex_Sans" / "Barlow_Semi_Condensed" / "OFL.txt",
    },
    "IBM Plex Mono": {
        "path": FONT_DIR / "IBM_Plex_Mono" / "IBMPlexMono-Medium.ttf",
        "license": FONT_DIR / "IBM_Plex_Mono" / "OFL.txt",
    },
}
DEFAULT_FONT = "IBM Plex Sans"
