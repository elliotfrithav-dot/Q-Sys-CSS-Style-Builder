"""
css_builder_core.py — generic Q-SYS UCI style-generation engine.

No EFAV-specific data lives here (no theme names, no hex values, no icon
folder paths) — that's efav_presets.py. This module is the hardware-proven
pipeline itself, generalised so both build_icons.py (loops over the stock
EFAV presets) and css_builder_gui.py (builds one arbitrary theme from a form)
can call the same code.

CSS technique (confirmed on real Q-SYS hardware, see project history): real
icon files in a flat icons/ folder next to style.css, referenced by relative
`background-image: url("icons/name.ext")`. No -webkit-mask-image, no compound
(`.a.b`) or descendant (`.a .b`) selectors, no `:active` (confirmed dead in an
isolated test — see press_feedback below). Icon colour is baked into each
file at build time (tint_png/tint_svg) since background-image can't be
recoloured live the way a mask can. The native `:value(1)` state pseudo IS
proven to work for both background-color (every icon's on-state highlight)
and a background-image swap (`toggle_pairs` — the mic/speaker mute icons,
CONFIRMED WORKING on hardware). `momentary_icon_swap` extends that same
proven swap to every ordinary icon.

CONFIRMED on hardware: `momentary_icon_swap` (:value(1)) fires on a
**Momentary**-type control — it does NOT fire on a **Trigger**-type control.
Trigger controls apparently expose no readable Value at all for CSS to bind
to, so neither `:value(N)` nor `:active` can ever reach one — this is a hard
platform boundary, not a bug to keep chasing. Since transport buttons (play/
pause/stop/etc.) are commonly built as Trigger controls, CSS-driven state
styling does not apply to them; use Q-SYS's native per-button Pressed Image
slot instead (Path A, UCI_ICONS.md §2) — it's driven by the physical press/
release directly, not by a Value, so it works regardless of control type. The
`<slug>-hi<ext>` files `momentary_icon_swap` already generates are exactly
the right asset to assign there by hand per button.
"""
import hashlib
import re
import shutil
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

VALID_EXTS = {".svg", ".png"}
SKIP_EXTS = {".zip", ".gif", ".jpg", ".jpeg", ".bmp"}
ROLE_KEYS = ("bg", "surface", "surface-hi", "text", "text-dim", "icon", "icon-hi", "accent", "fault")
TYPE_SCALE_ROLES = ("display", "header", "label", "body", "readout", "caption")

DUP_SUFFIX_RE = re.compile(r"\s*\(\d+\)$")
COLOR_SUFFIX_RE = re.compile(r"\s*-\s*(black|white|red)$", re.IGNORECASE)
RES_SUFFIX_RE = re.compile(r"-(\d+)$")
NONALNUM_RE = re.compile(r"[^a-z0-9]+")
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def slugify(stem: str) -> tuple[str, int | None]:
    """Return (slug, resolution_from_filename_or_None)."""
    s = DUP_SUFFIX_RE.sub("", stem)  # strip Windows " (1)" duplicate-download marker
    s = COLOR_SUFFIX_RE.sub("", s)  # "Camera - Black"/"Camera - White" -> same slug (we tint anyway)
    s = CAMEL_BOUNDARY_RE.sub("-", s)  # "SettingsService" -> "Settings-Service" (no other separator to split on)
    if s.lower().startswith("icons8-"):
        s = s[len("icons8-"):]
    m = RES_SUFFIX_RE.search(s)
    res = int(m.group(1)) if m else None
    if m:
        s = s[: m.start()]
    slug = NONALNUM_RE.sub("-", s.lower()).strip("-")
    return slug, res


def png_width(path: Path) -> int:
    if Image is None:
        return 0
    try:
        with Image.open(path) as im:
            return im.width
    except Exception:
        return 0


def scan_icons(icons_dir: Path, root_for_relpath: Path | None = None):
    """Recursively collect candidate icon files under icons_dir, grouped by
    slug. root_for_relpath is only used to make report paths readable."""
    root = root_for_relpath or icons_dir
    groups: dict[str, list[dict]] = {}
    skipped: list[Path] = []
    for path in sorted(icons_dir.rglob("*")):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in VALID_EXTS:
            if ext in SKIP_EXTS or ext == "":
                skipped.append(path)
            continue
        slug, res = slugify(path.stem)
        if not slug:
            skipped.append(path)
            continue
        is_svg = ext == ".svg"
        width = res if res is not None else (png_width(path) if not is_svg else 0)
        groups.setdefault(slug, []).append({
            "path": path, "is_svg": is_svg, "width": width, "ext": ext, "root": root,
        })
    return groups, skipped


def resolve_winners(groups: dict[str, list[dict]], root_for_relpath: Path | None = None):
    """Pick one file per slug: SVG beats PNG, then highest width. Returns
    (winners: {slug: entry}, report: list of log lines)."""
    winners = {}
    report = []
    for slug in sorted(groups):
        entries = groups[slug]
        root = entries[0].get("root") or root_for_relpath

        def relpath(p: Path) -> str:
            try:
                return str(p.relative_to(root)) if root else str(p)
            except ValueError:
                return str(p)

        entries.sort(key=lambda e: (not e["is_svg"], -e["width"], str(e["path"])))
        best_rank = (entries[0]["is_svg"], entries[0]["width"])
        top_tier = [e for e in entries if (e["is_svg"], e["width"]) == best_rank]

        if len(top_tier) > 1:
            hashes = {hashlib.sha256(e["path"].read_bytes()).hexdigest() for e in top_tier}
            if len(hashes) > 1:
                report.append(
                    f"CONFLICT  .icon-{slug}: {len(top_tier)} files tie for best "
                    f"(svg={best_rank[0]}, width={best_rank[1]}) with DIFFERENT content "
                    f"— picked {relpath(top_tier[0]['path'])}, review the others:"
                )
                for e in top_tier[1:]:
                    report.append(f"            {relpath(e['path'])}")
            else:
                report.append(
                    f"dup       .icon-{slug}: {len(top_tier)} identical copies, kept "
                    f"{relpath(top_tier[0]['path'])}"
                )

        winner = entries[0]
        winners[slug] = winner
        if len(entries) > 1:
            dropped = [e for e in entries if e is not winner]
            for e in dropped:
                report.append(
                    f"dropped   {relpath(e['path'])}  (lost .icon-{slug} to "
                    f"{relpath(winner['path'])})"
                )
    return winners, report


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def tint_png(src: Path, dst: Path, hex_color: str) -> None:
    """Paint RGB = hex_color everywhere alpha > 0; keep original alpha (shape)."""
    if Image is None:
        raise RuntimeError("Pillow is required to tint PNG icons")
    r, g, b = hex_to_rgb(hex_color)
    im = Image.open(src).convert("RGBA")
    pixels = im.getdata()
    im.putdata([(r, g, b, a) for (_, _, _, a) in pixels])
    im.save(dst)


FILL_ATTR_RE = re.compile(r'(<svg[^>]*\sfill=")[^"]*(")')


def tint_svg(src: Path, dst: Path, hex_color: str) -> None:
    """Set/override a fill attribute on the root <svg> tag (cascades to
    children that don't set their own fill — verify per-source before relying
    on this for a new icon set; the stock EFAV icons carry no inline overrides)."""
    text = src.read_text(encoding="utf-8")
    if FILL_ATTR_RE.search(text):
        text = FILL_ATTR_RE.sub(rf"\g<1>{hex_color}\g<2>", text, count=1)
    else:
        text = text.replace("<svg", f'<svg fill="{hex_color}"', 1)
    dst.write_text(text, encoding="utf-8")


# Latin + digits + punctuation actually used on a UI (dB, Hz, kHz, %, :, etc.)
# fall inside plain printable ASCII, plus the degree sign — matches the subset
# range already proven in the shipped IBM Plex Sans embed.
SUBSET_UNICODES = [ord(c) for c in "".join(chr(i) for i in range(0x20, 0x7F))] + [0xB0]


def subset_font(src: Path, dst: Path) -> None:
    """In-process font subsetting (fontTools API, no shell-out) — used for
    both the built-in font dropdown options and a user-uploaded custom font."""
    from fontTools import ttLib
    from fontTools.subset import Options, Subsetter

    options = Options()
    options.layout_features = []
    options.name_IDs = []
    options.glyph_names = True
    options.hinting = False
    options.recalc_bounds = True
    options.recalc_timestamp = True
    options.desubroutinize = True

    font = ttLib.TTFont(str(src))
    subsetter = Subsetter(options=options)
    subsetter.populate(unicodes=SUBSET_UNICODES)
    subsetter.subset(font)
    font.save(str(dst))


def font_stack(font_family: str) -> str:
    return f'"{font_family}", -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif'


def build_font_face(font_family: str, font_filename: str, weight: int = 500) -> str:
    return (
        "@font-face {\n"
        f'  font-family: "{font_family}";\n'
        f'  src: url("{font_filename}") format("truetype");\n'
        f"  font-weight: {weight};\n"
        "  font-style: normal;\n"
        "  font-display: swap;\n"
        "}\n"
    )


DEFAULT_TYPE_SCALE = {
    "display": 26, "header": 20, "label": 16, "body": 14, "readout": 20, "caption": 13,
}


def build_theme_css(
    name: str,
    theme: dict,
    winners: dict,
    icon_count: int,
    *,
    font_family: str,
    font_filename: str,
    type_scale: dict = None,
    include_page_chrome: bool = True,
    toggle_pairs: list = None,
    toggle_on_state_ext: dict = None,
    press_feedback: bool = False,
    momentary_icon_swap: bool = False,
    logo_entry: dict = None,
) -> str:
    """Generalised CSS builder. type_scale overrides px sizes only — weight
    and colour-role wiring stay fixed per role (v1 decision, CSS_STYLE_BUILDER.md
    §2/§8.2). toggle_pairs: list of (off_slug, on_slug, combined_class_name);
    each 'on' icon must have a '<on_slug>-fault<ext>' file already written to
    this theme's icons/ folder by the caller — toggle_on_state_ext optionally
    maps on_slug -> the actual extension of that file (only needed if the
    caller used different on-state art than winners[on_slug], see build_theme).
    press_feedback: CONFIRMED NOT WORKING on hardware (isolated test, see
    project history: the mute-toggle's :value(1) background-image swap works,
    the identical technique under :active does not — this isolates the
    failure to :active itself, not the pattern). Defaults to False and is not
    shipped in the stock build; kept available (needs '<slug>-active<ext>'
    already written by the caller) only in case a future Q-SYS/firmware
    version changes this. Real per-button press feedback is a native Designer
    property (Icon Color / Pressed image slots, Path A/B in UCI_ICONS.md),
    not something this stylesheet can do.
    momentary_icon_swap: CONFIRMED WORKING on a Momentary-type control,
    CONFIRMED NOT WORKING on a Trigger-type control (hardware test) — reuses
    the exact :value(1) + background-image swap already proven for the mute
    toggle (a latching control), and it turns out Momentary controls expose
    a readable Value the same way, but Trigger controls don't expose one at
    all. So this gives real per-icon press feedback on Momentary buttons for
    free; on Trigger buttons (commonly transport controls — play/pause/stop)
    the rule never matches, harmlessly, and there is currently no CSS path to
    press feedback on those — use the native per-button Pressed Image slot
    instead (Path A, UCI_ICONS.md §2), assigning the same '<slug>-hi<ext>'
    file this generates. Needs '<slug>-hi<ext>' already written by the caller
    (see build_theme).
    logo_entry: {"ext": ".svg"} (or None) — a non-tinted, non-icon `.logo`
    rule pointing at icons/logo.<ext>."""
    t = theme
    scale = {**DEFAULT_TYPE_SCALE, **(type_scale or {})}
    stack = font_stack(font_family)
    lines = []
    lines.append(f"/* Q-SYS UCI CSS — style: {name} */")
    lines.append(f"/* Generated by css_builder_core.py. {icon_count} icons. */")
    lines.append("/* Icon colour is baked into each icons/*.png|svg file at build time for this")
    lines.append("   theme — CSS only sets shape (background-image), size and position. No CSS")
    lines.append("   masking, no compound/descendant selectors, no `:active` — all confirmed")
    lines.append("   unsupported on hardware for this build (isolated test: :value(1) background-")
    lines.append("   image swap works, the identical :active swap does not — see press_feedback")
    lines.append("   in build_theme_css()). Use native Icon Color / Pressed image slots for real")
    lines.append("   press feedback instead. */")
    lines.append("")

    if include_page_chrome:
        lines.append("/* Page background — bare type selector, matches the proven QSC reference. */")
        lines.append("page {")
        lines.append(f"  background-color: {t['bg']};")
        lines.append("}")
        lines.append("")
        lines.append("/* Header/footer chrome bands — assign to a Group Box. Reuses the `surface`")
        lines.append("   role: same requirement as a button fill, must step visibly off `bg`. */")
        lines.append(".header {")
        lines.append(f"  background-color: {t['surface']};")
        lines.append("  border: none;")
        lines.append("}")
        lines.append("")
        lines.append(".footer {")
        lines.append(f"  background-color: {t['surface']};")
        lines.append("  border: none;")
        lines.append("}")
        lines.append("")

    lines.append("/* Icon shapes, alphabetical by slug. Colour is already baked into the file.")
    lines.append("   :value(1) is the native latched-on state (proven) — tints the background")
    if momentary_icon_swap:
        lines.append("   behind the icon on state AND swaps the icon itself to its `icon-hi` tint")
        lines.append("   (background-image swap). CONFIRMED WORKING on Momentary controls, CONFIRMED")
        lines.append("   NOT WORKING on Trigger controls (no readable Value on hardware) — e.g. most")
        lines.append("   transport buttons. For those, use the native Pressed Image slot instead,")
        lines.append("   with the matching icons/<slug>-hi.<ext> file this build already wrote. */")
    else:
        lines.append("   behind the icon on state; the glyph itself is unchanged. */")
    for slug_name in sorted(winners):
        entry = winners[slug_name]
        rel = f"icons/{slug_name}{entry['ext']}"
        lines.append(f".icon-{slug_name} {{")
        lines.append(f'  background-image: url("{rel}");')
        lines.append("  background-color: transparent;")
        lines.append("  background-repeat: no-repeat;")
        lines.append("  background-position: center;")
        lines.append("  background-size: 60%;")
        lines.append("}")
        if momentary_icon_swap:
            hi_rel = f"icons/{slug_name}-hi{entry['ext']}"
            lines.append(
                f'.icon-{slug_name}:value(1) {{ background-color: {t["accent"]}; '
                f'background-image: url("{hi_rel}"); }}'
            )
        else:
            lines.append(f".icon-{slug_name}:value(1) {{ background-color: {t['accent']}; }}")
    lines.append("")

    if press_feedback:
        lines.append("/* ============ CONFIRMED NOT WORKING ON HARDWARE ============")
        lines.append("   Attempted momentary press feedback: swap every icon's background-image to")
        lines.append("   an `icon-hi`-tinted version on `:active`. Isolated test result: the mute-")
        lines.append("   toggle's identical technique (single class, background-image swap) DOES")
        lines.append("   render under :value(1) but does NOT render under :active — so :active is")
        lines.append("   confirmed dead here, not the swap pattern. Left in only for reference; not")
        lines.append("   shipped by default. Use native Icon Color / Pressed image slots instead")
        lines.append("   (Path A/B, UCI_ICONS.md §2) for real per-button press feedback. */")
        for slug_name in sorted(winners):
            entry = winners[slug_name]
            lines.append(f'.icon-{slug_name}:active {{ background-image: url("icons/{slug_name}-active{entry["ext"]}"); }}')
        lines.append("")

    # Each pair is included independently — a pair whose on-state art is
    # missing (no TOGGLE_ON_STATE_ART override and not in winners either)
    # is just skipped on its own, it no longer silently drops every other
    # pair too (that was a real bug: an all-or-nothing gate meant one
    # missing icon disabled every toggle pair, not just its own).
    active_toggle_pairs = [
        (off, on, combined) for off, on, combined in (toggle_pairs or [])
        if off in winners and on in (toggle_on_state_ext or {})
    ]
    if active_toggle_pairs:
        lines.append("/* ============ CONFIRMED WORKING ON HARDWARE ============")
        lines.append("   Single-class on/off icon SWAP via :value(1) changing background-image,")
        lines.append("   not just background-color. Fall back to swapping the CSS Class Name")
        lines.append("   between the two plain .icon-<slug> classes above from your control logic")
        lines.append("   if you'd rather not use this. */")
        for off_slug, on_slug, combined in active_toggle_pairs:
            off_entry = winners[off_slug]
            on_ext = toggle_on_state_ext[on_slug]
            off_rel = f"icons/{off_slug}{off_entry['ext']}"
            on_rel = f"icons/{on_slug}-fault{on_ext}"
            lines.append(f".icon-{combined} {{")
            lines.append(f'  background-image: url("{off_rel}");')
            lines.append("  background-color: transparent;")
            lines.append("  background-repeat: no-repeat;")
            lines.append("  background-position: center;")
            lines.append("  background-size: 60%;")
            lines.append("}")
            lines.append(f'.icon-{combined}:value(1) {{ background-image: url("{on_rel}"); }}')
        lines.append("")

    if logo_entry:
        lines.append("/* Branding logo — multicolour art, not tinted/masked (spec: monochrome-only")
        lines.append("   applies to the functional icon set, not a company logo). */")
        lines.append(".logo {")
        lines.append(f'  background-image: url("icons/logo{logo_entry["ext"]}");')
        lines.append("  background-color: transparent;")
        lines.append("  background-repeat: no-repeat;")
        lines.append("  background-position: center;")
        lines.append("  background-size: contain;")
        lines.append("}")
        lines.append("")

    lines.append("/* Typography — subset font file, referenced by relative path. */")
    lines.append(build_font_face(font_family, font_filename))
    lines.append(f".txt-display  {{ font-family: {stack}; font-size: {scale['display']}px; font-weight: 600; color: {t['text']}; }}")
    lines.append(f".txt-header   {{ font-family: {stack}; font-size: {scale['header']}px; font-weight: 600; color: {t['text']}; }}")
    lines.append(f".txt-label    {{ font-family: {stack}; font-size: {scale['label']}px; font-weight: 500; color: {t['text-dim']}; }}")
    lines.append(f".txt-body     {{ font-family: {stack}; font-size: {scale['body']}px; font-weight: 400; color: {t['text-dim']}; }}")
    lines.append(f".txt-readout  {{ font-family: {stack}; font-size: {scale['readout']}px; font-weight: 500; font-variant-numeric: tabular-nums; color: {t['accent']}; }}")
    lines.append(f".txt-caption  {{ font-family: {stack}; font-size: {scale['caption']}px; font-weight: 400; color: {t['text-dim']}; }}")
    lines.append("")

    lines.append("/* Button chrome — strokeless (flat). Fill carries the edge. */")
    lines.append(".btn {")
    lines.append("  border: none;")
    lines.append("  outline: none;              /* touch-only panel: no keyboard focus ring needed */")
    lines.append("  box-shadow: none;")
    lines.append(f"  background-color: {t['surface']};")
    lines.append(f"  font-family: {stack};")
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


def validate_css(css: str, path: Path, theme_dir: Path) -> list[str]:
    errors = []
    depth = 0
    for ch in css:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                errors.append(f"{path}: brace depth went negative")
                break
    if depth != 0:
        errors.append(f"{path}: brace depth did not return to zero (ended at {depth})")

    for m in re.finditer(r'url\("([^"]*)"\)', css):
        ref = m.group(1)
        if not ref:
            errors.append(f"{path}: empty url() near {m.group(0)[:60]}")
        elif not (theme_dir / ref).exists():
            errors.append(f"{path}: referenced file missing on disk: {ref}")

    # :active is not banned outright — it's a legitimate opt-in (press_feedback,
    # clearly labelled UNVERIFIED in its own comment block). Compound selectors
    # and masking are still never wanted, at any time, for any reason.
    for banned in ("-webkit-mask-image", ".icon.active", ".icon.fault"):
        if banned in css:
            errors.append(f"{path}: contains unproven construct '{banned}' — should have been removed")

    if "@font-face" not in css or "src: url(" not in css:
        errors.append(f"{path}: missing @font-face declaration")

    if path.name != "style.css":
        errors.append(f"{path}: filename must be exactly 'style.css'")

    return errors


def build_theme(
    *,
    name: str,
    theme: dict,
    winners: dict,
    output_root: Path,
    font_path: Path,
    font_family: str,
    font_license_path: Path = None,
    type_scale: dict = None,
    include_page_chrome: bool = True,
    toggle_pairs: list = None,
    toggle_on_state_art: dict = None,
    press_feedback: bool = False,
    momentary_icon_swap: bool = False,
    logo_path: Path = None,
    clean: bool = True,
) -> tuple[Path, list[str]]:
    """Orchestrates one full theme build: tint+copy icons, copy font(+licence)
    and logo, build CSS, validate, write. Returns (out_dir, errors) — errors
    non-empty means style.css was NOT written (validation gate, §9).

    toggle_on_state_art: optional {on_slug: Path} — use this file as the
    on-state shape for that toggle pair instead of winners[on_slug]["path"]
    (e.g. purpose-drawn red mute art instead of the plain off-state icon)."""
    out_dir = output_root / name
    if clean and out_dir.exists():
        shutil.rmtree(out_dir)
    icons_out = out_dir / "icons"
    icons_out.mkdir(parents=True, exist_ok=True)

    for slug_name, entry in winners.items():
        dst = icons_out / f"{slug_name}{entry['ext']}"
        if entry["is_svg"]:
            tint_svg(entry["path"], dst, theme["icon"])
        else:
            tint_png(entry["path"], dst, theme["icon"])

    if press_feedback:
        for slug_name, entry in winners.items():
            dst = icons_out / f"{slug_name}-active{entry['ext']}"
            if entry["is_svg"]:
                tint_svg(entry["path"], dst, theme["icon-hi"])
            else:
                tint_png(entry["path"], dst, theme["icon-hi"])

    if momentary_icon_swap:
        for slug_name, entry in winners.items():
            dst = icons_out / f"{slug_name}-hi{entry['ext']}"
            if entry["is_svg"]:
                tint_svg(entry["path"], dst, theme["icon-hi"])
            else:
                tint_png(entry["path"], dst, theme["icon-hi"])

    toggle_on_state_ext = {}
    for off_slug, on_slug, _combined in (toggle_pairs or []):
        if off_slug not in winners:
            continue  # can't render the off-state at all, skip this pair
        override = (toggle_on_state_art or {}).get(on_slug)
        if override is None and on_slug not in winners:
            continue  # no art source anywhere for the on-state, skip this pair
        src_path = override if override is not None else winners[on_slug]["path"]
        is_svg = src_path.suffix.lower() == ".svg"
        ext = src_path.suffix.lower()
        toggle_on_state_ext[on_slug] = ext
        dst = icons_out / f"{on_slug}-fault{ext}"
        if is_svg:
            tint_svg(src_path, dst, theme["fault"])
        else:
            tint_png(src_path, dst, theme["fault"])

    logo_entry = None
    if logo_path is not None:
        ext = logo_path.suffix.lower()
        logo_entry = {"ext": ext}
        shutil.copyfile(logo_path, icons_out / f"logo{ext}")

    font_filename = font_path.name
    shutil.copyfile(font_path, out_dir / font_filename)
    if font_license_path and font_license_path.exists():
        shutil.copyfile(font_license_path, out_dir / "OFL.txt")

    css = build_theme_css(
        name, theme, winners, len(winners),
        font_family=font_family, font_filename=font_filename, type_scale=type_scale,
        include_page_chrome=include_page_chrome, toggle_pairs=toggle_pairs,
        toggle_on_state_ext=toggle_on_state_ext, press_feedback=press_feedback,
        momentary_icon_swap=momentary_icon_swap, logo_entry=logo_entry,
    )
    errors = validate_css(css, Path("style.css"), out_dir)
    if errors:
        return out_dir, errors

    (out_dir / "style.css").write_text(css, encoding="utf-8")
    return out_dir, []
