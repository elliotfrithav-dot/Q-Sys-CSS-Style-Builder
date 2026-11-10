# CSS_STYLE_BUILDER.md — EFAV UCI Style Builder (GUI front end)

Companion to `UCI_ICONS.md` (spec) and `build_icons.py` (the proven generation
engine, verified against real Q-SYS hardware — see its docstring for why it
uses real referenced files, not base64, contradicting `UCI_ICONS.md` §5/§12's
original assumption). **This doc does not replace either — it wraps them in a
GUI so a theme can be built without hand-editing the `THEMES` dict in Python.**

Where something is marked **UNRESOLVED**, it's open and should be answered/
tried before that part is built.

---

## 1. What this is

A desktop app, run locally on your machine, that lets you fill in a form
(colours, fonts, sizes, icons, logo) and produces a Q-SYS-ready style folder —
either written straight into `Documents\QSC\Q-SYS Designer\Styles\<name>\`, or
exported as a package. It does not invent a new CSS technique — it's a front
end over the exact pipeline `build_icons.py` already proved works on hardware:
real icon files tinted per-theme, a real subset font file, plain
`background-image`/`background-color` rules, no masking, no `:active`.

**Two audiences, one build, phased:**

- **v1 — internal.** You use it to spin up new EFAV themes and one-off client
  themes fast, replacing manual edits to the `THEMES` dict.
- **v2 — commercial.** Same tool, packaged (installer, no hardcoded EFAV
  paths/assets, maybe a licence gate) and sold/given to other Q-SYS
  integrators. Flagged inline below wherever a v1 decision would need to
  change for this.

---

## 2. Scope of user input (the form)

| Field | v1 behaviour |
|---|---|
| **Theme name** | Text field. Becomes the output folder name = the name Designer shows in its Style dropdown. Validated against filesystem-unsafe characters. |
| **9 colour roles** | `bg`, `surface`, `surface-hi`, `text`, `text-dim`, `icon`, `icon-hi`, `accent`, `fault` — full control, one colour picker each (per your answer: no auto-derivation, what you set is what you get). Defaults pre-filled from whichever stock EFAV theme the user starts from (see §3). |
| **Type scale** | Six roles — `txt-display`, `txt-header`, `txt-label`, `txt-body`, `txt-readout`, `txt-caption` — each an editable font-size field (px), defaulting to the current spec (26/20/16/14/20/13). Weight and colour stay wired to the existing rules (weight fixed per role, colour from `text`/`text-dim`/`accent`) — **not** independently editable in v1; flag as a v2 nice-to-have if it turns out to matter. |
| **Font family** | Dropdown of pre-vetted, pre-subset options: IBM Plex Sans (default), Inter, IBM Plex Sans Condensed / Barlow Semi Condensed (long-label variant), IBM Plex Mono. Plus **Custom…** — upload a `.ttf`/`.otf`, the tool runs `pyftsubset` (Latin + digits + the symbol set already pinned in `UCI_ICONS.md` §6) and embeds the result. OFL/licence text bundled automatically for the built-in fonts; a custom font's licence is the user's responsibility — the tool shows a one-line reminder, doesn't try to police it. |
| **Functional icon set** | Checklist of the existing ~38-icon library (grouped Audio / Navigation / Video, matching the `Icons/` folder structure already on disk), all checked by default. Unchecking an icon just omits its `.icon-<slug>` rule and file from this theme's output. **Add custom icon…** lets you drop in extra `.svg`/`.png` files, which go through the same slugify → dedupe → tint pipeline as the stock set. |
| **Company/branding logo** | Separate from the functional icons — a single image upload (svg/png). Per `UCI_ICONS.md`'s existing "monochrome only" rule, a multicolour logo is **not tinted or masked** — copied through at native colour and exposed as a plain `.logo { background-image: url("logo.<ext>"); background-size: contain; background-repeat: no-repeat; }` rule, sized/positioned by whatever UCI element it's assigned to (matches how the spec already treats non-maskable art). |
| **Smart Builder (URL brand pull)** | See §6 — v2, opt-in, pre-fills the form rather than bypassing it. |

---

## 3. Starting point: blank vs. duplicate

The form can start two ways:

- **Blank** — all 9 roles default to EFAV Navy's values (the brand default),
  type scale defaults to spec, IBM Plex Sans selected, all stock icons
  checked, no logo.
- **Duplicate an existing theme** — dropdown of the 8 themes already on disk
  (`EFAV Navy`, `Slate Light`, `Graphite`, `Warm Studio`, `High-Contrast`,
  `Black Icons`, `White Icons`, and any custom ones already built) — loads
  that theme's role colours, icon selection, and font as the starting values,
  which the user then edits and saves under a new name. This is the fast path
  for "same as Graphite but client wants their brand blue" client jobs.

---

## 4. Generation engine (refactor, not rewrite)

`build_icons.py`'s logic is correct and hardware-proven — it should not be
reimplemented, just **generalised and split from its hardcoded `THEMES`
dict** so the GUI can call it with arbitrary values:

```
css_builder_core.py          — the engine, importable, no UI code
  scan_icons() / resolve_winners() / slugify()   (moved, unchanged)
  tint_png() / tint_svg()                        (moved, unchanged)
  build_theme_css(name, theme_dict, type_scale_dict, font_stack, winners,
                   icon_count, logo_entry=None)   (generalised: type_scale
                                                    and font are now params,
                                                    not hardcoded constants;
                                                    optional .logo block)
  validate_css()                                 (moved, unchanged — the
                                                    brace-depth + missing-
                                                    file + banned-construct
                                                    gate still runs on every
                                                    build, GUI or CLI)
  build_theme(...)                               — new: orchestrates one
                                                    full theme build (icons,
                                                    font, logo, css, validate,
                                                    write) for one output dir

build_icons.py                — kept as-is, now just calls css_builder_core
                                 in a loop over its own THEMES dict. Still the
                                 fast way to rebuild all 8 stock EFAV themes
                                 at once; not replaced by the GUI.

css_builder_gui.py            — Tkinter (stdlib, no new dependency — matches
                                 "runs on a bare integrator laptop" for the
                                 v2 commercial path). Form → calls
                                 css_builder_core.build_theme() → shows
                                 validation result → offers Install / Export.
```

**Why Tkinter and not a web-app front end:** the v2 commercial goal is "an
integrator downloads and runs this on their own Windows laptop with zero
setup" — Tkinter ships with Python, no local server, no browser dependency,
packages cleanly with PyInstaller into a single `.exe` later. A local web
app would need to solve "how does a form in a browser tab write a file into
`Documents\QSC\...`" — solvable, but it's solving a problem Tkinter doesn't
have.

---

## 5. Output

Two buttons, always both available:

- **Install** — writes `<ThemeName>/` (style.css + icons/ + font file + OFL.txt
  + logo file if set) directly into
  `Documents\QSC\Q-SYS Designer\Styles\<ThemeName>\` on the machine running
  the app. Runs `validate_css()` first; a failed validation blocks the write
  and shows the specific error(s) in the GUI — never a silent bad file (same
  rule `build_icons.py` already enforces).
- **Export package** — writes the same folder contents to a location the user
  picks (e.g. a zip, or a folder to hand to a client/another integrator).
  This is the only option that makes sense for the v2 commercial case, where
  the person running the builder may not be the person installing it into
  Designer.

Both paths reuse the identical build output — Install is just Export-to-a-
known-path.

**UNRESOLVED:** should Install detect and warn on overwriting a theme name
that already exists in the Styles folder, or just silently replace it (which
is what `build_icons.py` does today for its own `THEMES` keys, note the "never
wipe `OUTPUT_ROOT` wholesale" comment guarding *other* themes it doesn't own)?
Leaning toward: warn with an overwrite confirmation, since a GUI user editing
one theme at a time is a different risk profile than a batch script that only
ever touches its own known keys.

---

## 6. Smart Builder — URL brand pull (v2, opt-in assist)

Requested addition: give the tool a company website URL and have it suggest a
starting theme instead of starting blank/duplicated.

**What it can realistically do:**

1. Fetch the page, pull `<meta name="theme-color">` / any CSS custom
   properties in the linked stylesheet if present — direct colour signal when
   it exists.
2. Pull the site's logo (`og:image`, a `<link rel="icon">`/favicon, or an
   `<img>` with "logo" in its class/alt/filename) and run a dominant-colour
   extraction (Pillow, k-means or a simple histogram) on it as a fallback
   colour source when no explicit theme-color exists.
3. Best-effort font detection from linked Google Fonts / `font-family` in the
   page's CSS — matched against the built-in font dropdown if there's a
   close match, otherwise ignored (no auto font-fetching from arbitrary
   sites — the "no externally-fetched fonts" rule in `UCI_ICONS.md` §11 stays
   a hard constraint regardless of source).
4. **Map extracted colours → the 9 role tokens is a heuristic, not a fact** —
   e.g. darkest extracted colour → `bg`, most saturated → `accent`. Brand
   palettes don't naturally decompose into this 9-role shape (most sites
   don't have a `surface-hi`-equivalent at all). The result is a **pre-filled
   suggestion the user reviews and edits in the same full-control colour
   pickers from §2** — never a bypass of them, and never a direct write.

**Explicitly out of scope for this feature (flag if expectations differ):**
scraping the whole site design, extracting a logo from a JS-rendered page
(static fetch only, no headless browser in v1 of this feature), and any
attempt to auto-pick icon style from a site's visual language — icons stay a
manual pick from §2.

This is the least-proven part of the whole doc — treat it as a v2 stretch
goal to prototype once the core builder (§2–§5) is working and used for a
few real themes, not a day-one requirement.

---

## 7. What this doc deliberately does not change

- The proven CSS technique in `build_icons.py` (real files, no masking, no
  `:active`, no compound selectors) — the GUI targets that pipeline exactly,
  it does not revisit the masking-vs-real-files decision.
- The 9-role token shape, the type-scale role names, the button chrome rule,
  the `:value(N)` fader/knob findings — all settled in `UCI_ICONS.md`, carried
  over unchanged.
- The install location and folder-per-theme / `style.css`-filename-always
  rule (`UCI_ICONS.md` §12) — the GUI automates copying into that folder, it
  doesn't change where Designer looks.

---

## 8. Open questions to settle before coding

1. Overwrite behaviour on Install (§5) — warn-and-confirm vs. silent replace.
2. Type-scale weight/colour per-role overrides — locked to existing rules in
   v1 (per §2) — confirm that's acceptable, or does a client job ever need a
   header in the accent colour instead of `text`?
3. Smart Builder (§6) — build now alongside v1, or park it until the core
   builder has been used on a couple of real jobs?
4. v2 commercial packaging (installer/exe, licence gate, stripping EFAV-
   specific defaults) — not blocking v1 code, but worth a one-line decision
   on whether `css_builder_core.py` should avoid any EFAV-specific hardcoding
   from the start (e.g. the stock 8 themes as swappable presets file rather
   than inline dict) so v2 doesn't need a rewrite.

---

## 9. Upcoming tasks (not started, don't forget)

- **Toggle slider styling.** There's an existing EFAV plugin with toggle
  sliders that should get the same treatment as everything else here (tinted
  per theme, built through the same pipeline). Not scoped or started —
  parked until the core builder + icon/theme workflow settle down. Needs its
  own look at what CSS actually reaches a slider/toggle control on hardware
  (same kind of proven-vs-assumed check this whole project has been doing —
  don't assume `background-image`/`:value(N)` behave on a slider the same
  way they do on a button/graphic just because they do on those).
