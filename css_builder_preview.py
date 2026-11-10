"""
css_builder_preview.py — renders a mock "typical UCI" using the REAL built
assets (actual tinted icon files, actual embedded font file), not idealised
placeholders. Pure function of (theme, winners, font_path, ...) -> (a PIL
Image, a dict of named click regions); no Tkinter dependency, so it's usable/
testable standalone. The regions dict is what makes the GUI preview clickable
— render_preview() itself never touches Tk.

Deliberately does NOT round button corners: hardware testing (see
themes/EFAV Fader Probe/style.css) found border-radius has NO EFFECT on the
real Core/panel. A rounded preview would misrepresent what the CSS actually
produces, so every rect here is drawn square-cornered on purpose.

Layout loosely mirrors a real reference UCI screenshot shared during this
project (header bar with menu/title/clock/settings, a "Source Selected"
readout, source buttons with icons, a footer icon row) — familiar shape, but
built entirely from this project's own EFAV icon set.

Interactivity: source buttons demonstrate the PROVEN :value(1) background-
colour tint (click to flip a button's simulated latched state — icon file
stays the same, only the fill colour changes, exactly matching the real CSS
rule). Toggle-pair icons (if enabled for this build) demonstrate the PROVEN
:value(1) background-image swap (click to flip between the off icon and the
fault-tinted on icon). Neither demonstrates the CONFIRMED-NOT-WORKING
`:active` press feedback — there's nothing to show, it doesn't render on
hardware either.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import css_builder_core as core

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
except ImportError:
    svg2rlg = None
    renderPM = None

W, H = 700, 440
HEADER_H = 56
FOOTER_H = 56


def _load_font(font_path: Path, px: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(font_path), px)
    except Exception:
        return ImageFont.load_default()


def _rasterize_svg(path: Path) -> Image.Image | None:
    """Preview-only SVG->raster (the actual shipped CSS ships raw SVG,
    unrasterized — this is purely so the GUI mockup can composite it)."""
    if svg2rlg is None:
        return None
    try:
        drawing = svg2rlg(str(path))
        return renderPM.drawToPIL(drawing, bg=None, backendFmt="RGBA")
    except Exception:
        return None


def load_icon_image(icon_path: Path) -> Image.Image | None:
    """Public: load any stock/tinted icon (svg or raster) as an RGBA PIL
    Image, no compositing — used directly by the GUI for checklist thumbnails
    as well as internally by _paste_icon."""
    if icon_path.suffix.lower() == ".svg":
        return _rasterize_svg(icon_path)
    try:
        return Image.open(icon_path).convert("RGBA")
    except Exception:
        return None


def tint_image_inmemory(im: Image.Image, hex_color: str) -> Image.Image:
    """Same technique as core.tint_png/tint_svg (paint RGB where alpha>0,
    keep alpha as the shape) but on an already-loaded Image, no disk I/O —
    for the GUI's icon checklist thumbnails, which need to tint dozens of
    source icons to one fixed neutral colour just to be visible/legible
    regardless of each source file's own original fill."""
    r, g, b = core.hex_to_rgb(hex_color)
    im = im.convert("RGBA")
    pixels = im.getdata()
    out = Image.new("RGBA", im.size)
    out.putdata([(r, g, b, a) for (_, _, _, a) in pixels])
    return out


def _paste_icon(base: Image.Image, icon_path: Path, box: tuple[int, int, int, int]) -> None:
    """box = (x, y, w, h) to fit the icon into, preserving aspect ratio, centred."""
    x, y, w, h = box
    icon = load_icon_image(icon_path)
    if icon is None:
        return
    icon = icon.copy()
    icon.thumbnail((w, h), Image.LANCZOS)
    ix = x + (w - icon.width) // 2
    iy = y + (h - icon.height) // 2
    base.alpha_composite(icon, (ix, iy))


def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def render_preview(
    theme: dict,
    winners: dict,
    font_path: Path,
    type_scale: dict = None,
    include_page_chrome: bool = True,
    scale: float = 0.5,
    toggle_pairs: list = None,
    icons_dir: Path = None,
    demo_state: dict = None,
) -> tuple[Image.Image, dict]:
    """winners here must already point at TINTED icon files for this theme
    (i.e. pass the same dict of {slug: path} you're about to ship, not the
    raw source-icon winners from resolve_winners — see build_preview_from_theme).

    toggle_pairs + icons_dir: if given, the footer demonstrates each selected
    toggle pair's real on/off icon swap (needs "<on_slug>-fault<ext>" already
    written into icons_dir by the build — build_theme() does this whenever
    toggle_pairs is passed to it).

    demo_state: {"source_<i>": bool, "toggle_<combined_name>": bool} — which
    demo elements are currently shown in their simulated :value(1) latched-on
    state. Pass back the SAME dict (mutated by the caller on click) on the
    next call to keep clicked state across re-renders.

    Returns (image, regions) — regions maps the same keys used in demo_state
    to (x1, y1, x2, y2) click boxes in image coordinates, for a caller (the
    GUI) to hit-test clicks against and flip demo_state itself. This function
    never reads mouse/click input — it only reports where things are."""
    t = theme
    ts = {**core.DEFAULT_TYPE_SCALE, **(type_scale or {})}
    demo_state = demo_state or {}
    regions: dict[str, tuple[int, int, int, int]] = {}
    px = lambda n: max(1, round(n * scale * 2))  # type-scale px are canvas px; preview is half-canvas-ish

    bg = t["bg"] if include_page_chrome else "#808080"
    img = Image.new("RGBA", (W, H), bg)
    draw = ImageDraw.Draw(img)

    if include_page_chrome:
        draw.rectangle([0, 0, W, HEADER_H], fill=t["surface"])
        draw.rectangle([0, H - FOOTER_H, W, H], fill=t["surface"])

        if "menu" in winners:
            _paste_icon(img, winners["menu"], (12, 12, 32, 32))
        elif "hamburger-menu" in winners:
            _paste_icon(img, winners["hamburger-menu"], (12, 12, 32, 32))
        if "settings" in winners:
            _paste_icon(img, winners["settings"], (W - 44, 12, 32, 32))

        header_font = _load_font(font_path, px(ts["header"]))
        draw.text((60, HEADER_H // 2), "UCI Preview", font=header_font, fill=t["text"], anchor="lm")

        label_font_footer = _load_font(font_path, px(ts["caption"]))
        foot_icons = [s for s in ("microphone", "minus", "plus", "voice", "power") if s in winners]

        # Toggle-pair demo icons replace their plain off-state counterpart in
        # the footer row, if that pair is selected for this build.
        toggle_by_off_slug = {}
        if toggle_pairs and icons_dir is not None:
            for off_slug, on_slug, combined in toggle_pairs:
                if off_slug in foot_icons:
                    toggle_by_off_slug[off_slug] = (on_slug, combined)

        n = len(foot_icons)
        if n:
            spacing = W / (n + 1)
            for i, slug in enumerate(foot_icons):
                cx = int(spacing * (i + 1))
                box = (cx - 16, H - FOOTER_H // 2 - 16, 32, 32)
                if slug in toggle_by_off_slug:
                    on_slug, combined = toggle_by_off_slug[slug]
                    key = f"toggle_{combined}"
                    is_on = demo_state.get(key, False)
                    if is_on:
                        on_entry_ext = Path(winners.get(on_slug, Path(f"{on_slug}.png"))).suffix or ".png"
                        art = icons_dir / f"{on_slug}-fault{on_entry_ext}"
                        _paste_icon(img, art if art.exists() else winners[slug], box)
                    else:
                        _paste_icon(img, winners[slug], box)
                    regions[key] = (box[0] - 4, box[1] - 4, box[0] + box[2] + 4, box[1] + box[3] + 4)
                else:
                    _paste_icon(img, winners[slug], box)

    content_top = HEADER_H + 16 if include_page_chrome else 16
    label_font = _load_font(font_path, px(ts["label"]))
    readout_font = _load_font(font_path, px(ts["readout"]))

    draw.text((24, content_top), "Source Selected:", font=label_font, fill=t["text"])
    label_w, _ = _text_size(draw, "Source Selected:", label_font)
    draw.text((24 + label_w + 10, content_top), "Laptop", font=readout_font, fill=t["accent"])

    btn_y = content_top + 44
    btn_w, btn_h = 140, 110
    icon_box = 64
    button_slugs = [s for s in ("laptop", "monitor", "presentation", "hdmi") if s in winners][:3]
    for i, slug in enumerate(button_slugs):
        bx = 24 + i * (btn_w + 24)
        key = f"source_{i}"
        is_on = demo_state.get(key, False)
        fill = t["accent"] if is_on else t["surface"]
        cap_color = t["icon-hi"] if is_on else t["text-dim"]
        draw.rectangle([bx, btn_y, bx + btn_w, btn_y + btn_h], fill=fill)
        _paste_icon(img, winners[slug], (bx + (btn_w - icon_box) // 2, btn_y + 12, icon_box, icon_box))
        cap = slug.title()
        cap_w, _ = _text_size(draw, cap, label_font)
        draw.text((bx + (btn_w - cap_w) // 2, btn_y + btn_h - 26), cap, font=label_font, fill=cap_color)
        regions[key] = (bx, btn_y, bx + btn_w, btn_y + btn_h)

    hint_font = _load_font(font_path, px(ts["caption"]))
    hint = "Click a button or footer icon to preview its on-state"
    hint_w, _ = _text_size(draw, hint, hint_font)
    draw.text((W - hint_w - 12, H - FOOTER_H - 16), hint, font=hint_font, fill=t["text-dim"])

    return img.convert("RGB"), regions


def build_preview_from_theme(
    theme: dict,
    icons_dir: Path,
    font_path: Path,
    type_scale: dict = None,
    include_page_chrome: bool = True,
    included_slugs: set = None,
) -> tuple[Image.Image, dict]:
    """Convenience entry point: scans icons_dir fresh, tints in-memory (writes
    to a throwaway temp dir) for this theme's colours, then renders. Slower
    than reusing an already-built theme's icons/ folder — prefer
    render_preview() directly with winners already pointing at real tinted
    files (e.g. a just-built theme's icons/ dir) when you have one."""
    import tempfile

    groups, _skipped = core.scan_icons(icons_dir)
    raw_winners, _report = core.resolve_winners(groups)
    if included_slugs is not None:
        raw_winners = {s: e for s, e in raw_winners.items() if s in included_slugs}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        tinted = {}
        for slug, entry in raw_winners.items():
            dst = tmp_dir / f"{slug}{entry['ext']}"
            if entry["is_svg"]:
                core.tint_svg(entry["path"], dst, theme["icon"])
            else:
                core.tint_png(entry["path"], dst, theme["icon"])
            tinted[slug] = dst
        return render_preview(
            theme, tinted, font_path, type_scale=type_scale, include_page_chrome=include_page_chrome,
        )
