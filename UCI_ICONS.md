# UCI_ICONS.md — EFAV Q-SYS UCI Icon + Typography CSS

Build spec for the icon/typography stylesheet layer of EFAV Q-SYS UCIs.
Handoff target: Claude Code. Deliverables are a **repeatable Python build
script** and its emitted **`style.css`**.

Where something is marked **UNRESOLVED / VERIFY**, it is genuinely open and must
be confirmed on hardware or in Designer before that part is relied on — do not
guess and do not build the dependent path until it's answered.

---

## 1. Scope

Three things live in this stylesheet, and only these:

1. **Icons** — collate a folder of monochrome AV icons (SVG + PNG) into `style.css`
   as recolourable elements. Recolour is done in CSS, not by shipping a coloured
   copy of every icon.
2. **Typography** — one embedded (subset) font plus the size/weight/colour type-scale
   roles for the UCI's text (the *Text Style* half of the Designer button panel and
   any free text elements).
3. **Button chrome** — the no-stroke (flat) button default (§7).

Everything else about the UCI (layout, controls, DSP) is out of scope here.

---

## 2. Q-SYS rendering paths — read this before building

Q-SYS gives a button **three** independent ways to carry an icon. They do not
overlap on a single button — pick one path per control. Confirmed from the
Designer panel serialization (`ControlStyle` object).

### Path A — Native Image slots (the 2×2 in the button panel)

```
                 Released              Pressed (finger down)
   Off      _OffImageData          _PressedOffImageData
   On       _OnImageData           _PressedOnImageData
```

- Q-SYS swaps the slot bitmap on state/press **natively**. No CSS.
- Colour is **baked per file** — recolour or glyph-swap = a different file per slot.
- This is how latching on/off state is rendered natively.

### Path B — Native per-state **style strings** + native icon colour

The `ControlStyle` object also carries a per-state style string for every cell of
the same 2×2, plus a **native recolourable icon field**:

```
_LocalStyleString          (off, released — base)
_LocalOnStyleString        (on, released — latched)
_LocalPressedStyleString   (off, pressed — momentary)
_LocalPressedOnStyleString (on, pressed — momentary while latched)

_IconType / _IconData / _IconString / _IconColor / _IconAlignment
```

- `_IconColor` means Q-SYS **tints a native icon itself** — recolour with no mask,
  no CSS, no build step. If it is settable per state, momentary-recolour and
  latching-recolour both fall out of native properties.
- The per-state style strings are Q-SYS's officially-exposed hook for styling a
  button *by state*. State is therefore **not** blind to styling — there is a
  dedicated `On` string (latch) and a dedicated `Pressed` string (momentary).

### Path C — CSS masking (own the paint)

Render the icon as a CSS element whose `background-color` is the icon colour and
whose shape is a `-webkit-mask-image`. Recolour = swap `background-color`. See §4.

> **The build script only produces Path C assets (`style.css`) and the Path A
> files.** Path B is a Designer-side native capability, not something the script
> emits — but it may make part of Path C redundant (see §3, §10). Do not delete the
> masking path until the Path B verification in §10 is done.

---

## 3. Confirmed architecture decisions

| Control | State type | Rendering | Assets |
|---|---|---|---|
| **All momentary icons** — volume ±, navigation (`nav`, `return`, page-open/hide), source/mode select, and any press-and-release control | Momentary | **CSS mask** (Path C), `background-color` invert on press — see §4 | One monochrome icon each; recoloured in CSS |
| **Mute** (`mute` / `voice`) | Latching | Discrete per-state icons (user supplies both) | Two icons: muted + unmuted |
| On/off latching state generally | Latching | User handles natively (Path A slots) | — |

- **Every momentary icon inverts via masking on press** — this is a blanket rule,
  not a per-icon decision. Any icon sitting on a momentary or trigger control gets
  the exact-colour invert-on-press from the shared `:active` rule in §4; nothing
  per-icon is written. Momentary controls in the reference panel that this covers:
  `Audio`, `Video`, `Camera`, `Lights`, `Blinds`, `Comp`, `EQ` (Momentary) and
  `Nav`, `NavHide`, `Settings`, `FXHide`, `FXShow`, `Audio_rtn` (Trigger).
- **Masking, not `filter: invert()`** — the invert must land on an *exact* brand
  colour on press, which `filter: invert()`'s photographic negative can't give.
- **Mute is a glyph swap** (speaker ↔ speaker-slash), not a recolour — `_IconColor`
  can't change shape, so it needs two icons. User **has** both
  (`icons8-mute-100.png`, `icons8-voice-100.png`).
- **One icon, many colours.** Because a CSS mask reads shape/alpha only and ignores
  the source's own fill, the existing **black** icons *are already* the light-theme
  icons — recolour is `background-color`, no second asset set, no per-theme export.

### Theme

- Light theme default: icon `background-color` = **NAVY `#0D1B2A`** (reads on light).
- Dark theme: one override recolours the whole set — `.theme-dark .icon { background-color: #E0E6ED; }`.
- **UNRESOLVED (from prior discussion):** is the theme a *runtime toggle* on one
  shared UCI, or *fixed* per UCI?
  - Runtime toggle → single `style.css`, `.theme-dark .icon {}` overrides.
  - Fixed → one **folder** per theme (`<name>/style.css` — filename always
    `style.css`), same mask/structure, differing role hex. The full theme set + role
    tokens live in **§8**.
  - **Default assumption for the build: single switchable `style.css`.** Flip if
    the toggle isn't available.

---

## 4. Icon CSS technique (Path C — masking)

```css
/* Base — every icon inherits this. Colour = background-color; shape = mask. */
.icon {
  display: inline-block;
  width: 32px;                    /* px DEFAULT for standalone icons (not in a button) */
  height: 32px;
  background-color: #0D1B2A;      /* NAVY — icon colour (light theme) */
  -webkit-mask-repeat: no-repeat;
  -webkit-mask-position: center;
  -webkit-mask-size: contain;     /* fits shape to the box at ANY size, crisp (vector) */
}

/* Button icons scale WITH the button — % of container, not fixed px.
   A new button size needs NO new icon rule; the icon just fits. */
.btn .icon { width: 60%; height: 60%; }

/* Per-icon — shape only, as a base64 data URI (see §5). */
.icon-plus  { -webkit-mask-image: url("data:image/svg+xml;base64,…"); }
.icon-minus { -webkit-mask-image: url("data:image/svg+xml;base64,…"); }
.icon-mute  { -webkit-mask-image: url("data:image/png;base64,…"); }
.icon-voice { -webkit-mask-image: url("data:image/png;base64,…"); }

/* Recolour = background-color. State/theme classes. */
.theme-dark .icon        { background-color: #E0E6ED; }   /* soft white idle */
.icon.active             { background-color: #2E86AB; }   /* ACCENT */
.icon.fault              { background-color: #E63946; }   /* alarm (adjust) */

/* Momentary press — BLANKET rule for every masked icon on a momentary/trigger
   control. One shared rule; nothing per-icon. Exact-colour invert while finger
   down, releases on lift. Icon and button swap colours (colour-invert, not alpha). */
.btn:active .icon        { background-color: #E0E6ED; }   /* icon → light */
.btn:active              { background-color: #2E86AB; }   /* button → ACCENT */
```

The invert applies to **all** momentary icons by virtue of the shared `.btn:active`
selector — do not author a press rule per icon. Whatever class Q-SYS puts on the
button element (the `.btn` placeholder here) carries it for the whole set at once.
Pick the pressed colours once; every momentary icon obeys.

Rules:

- **`-webkit-` prefix is mandatory.** Unprefixed `mask-image` is not reliable on
  the Core's WebKit build. Use the prefixed properties only.
- **SVG preferred as mask source** — vector, so `mask-size: contain` stays crisp at
  any UCI scale. PNG works but **pixelates** when scaled up; only use PNG where no
  SVG exists.
- **Monochrome silhouettes only.** A multicolour logo has no single shape to paint
  and cannot be masked — it stays a `background-image` at native colour (out of
  scope for the recolour pipeline; flag any such file, don't mask it).
- Source fill colour is **irrelevant** — do not pre-process the SVGs to normalise
  colour. Black-on-transparent, white-on-transparent, either masks identically.
- Outline-style icons (e.g. the plus-in-circle) mask fine — the stroke alpha is the
  painted shape; "invert" here means colour-swap, never literal alpha inversion.
- **Size is not fixed.** The px in `.icon` is only a default for standalone icons;
  button icons use `% of container` and scale with the button (no per-size rule).
  Because the mask is vector, one icon stays crisp from a 24px nav glyph to a 48px
  main button — the payoff over a fixed-resolution PNG in a native slot. Override per
  icon or context anytime; the later rule wins.

---

## 5. Build script — `build_icons.py`

Python + **Pillow** (already in the EFAV stack). New dependencies only if needed:
**fonttools** (`pyftsubset`) for font subsetting (§6), and a rasteriser (cairosvg /
resvg) only if SVG must be rasterised for Image slots (§10). Repeatable: drop icons in
the folder, re-run.

### Inputs

- `icons/` — a flat folder of `.svg` and `.png` source icons.

### Behaviour

1. Scan `icons/` for `*.svg` and `*.png`.
2. **Slugify** each filename to a class name:
   - Strip vendor prefix `icons8-`.
   - Strip a trailing resolution suffix `-<digits>` (e.g. `-100`, `-256`, `-64`).
   - Strip extension.
   - Lower-case, kebab-case any remaining separators.
   - `icons8-mute-100.png` → `mute` → `.icon-mute`.
3. **Deduplicate** slugs (the folder has real collisions —
   `icons8-minus-100.png` and `icons8-minus-64.png`; `icons8-plus-100.svg` and
   `icons8-plus-256.png`). Resolution order, best first:
   1. **SVG wins** over PNG (vector).
   2. Between PNGs, **highest resolution wins** (largest `-<digits>`, or largest
      pixel dimensions if unlabelled).
   Emit one class per slug; log the dropped duplicates.
4. **Base64-encode** the chosen file. Embed inline as a data URI — **no external
   asset references** (single-file philosophy; must work on `file://`):
   - SVG → `data:image/svg+xml;base64,…`
   - PNG → `data:image/png;base64,…`
5. **Emit `style.css`** in a stable, sorted order (alphabetical by slug) so re-runs
   produce clean diffs:
   - The base `.icon` block (§4).
   - The brand state/theme colour classes (§4) — palette from §8.
   - One `.icon-<slug> { -webkit-mask-image: url("data:…") }` per icon.
   - The typography block (§6): the embedded `@font-face` (subset font, base64) +
     the `.txt-*` type-scale roles + no-stroke `.btn` chrome (§7).
6. **Validate** before writing final output (§9): brace-depth counter must balance;
   fail loudly and do not emit a broken file.

### Output

- **Filename is ALWAYS `style.css`** — Q-SYS requires it, no other name is accepted.
  Never emit `style-navy.css` or similar.
- **Themes (§8):** loop over the per-theme palette dicts and emit one folder per
  theme, each containing a `style.css` — `themes/EFAV Navy/style.css`,
  `themes/EFAV Slate Light/style.css`, … The **folder name is the user-facing style
  name** (§12); the file inside is always `style.css`. Icon mask data and all
  `.txt-*` / `.btn` structure are identical across files; only the nine role hex
  values change.
- A single switchable `style.css` (§3) is the alternative when the UCI can toggle a
  `.theme-*` class at runtime.
- Output root: `/mnt/user-data/outputs/`.

### Determinism

- Sort icons by slug before emitting. Same inputs → byte-identical output.
- Keep the generated file header commented with source count + build timestamp
  **only if** it doesn't defeat diff stability — prefer count only, no timestamp.

---

## 6. Typography

Emitted into the same `style.css`. Two parts: the **embedded font** and the
**type scale**.

### Font — one embedded, subset

Q-SYS UCI CSS accepts **one embedded font**. The standing EFAV "no external fonts"
rule means no font *fetched from a URL* — those won't load offline on the Core. An
**embedded** font (base64 `@font-face`, self-contained in `style.css`) is a
different thing and is the sanctioned single exception — this is the plan, **pending
the hardware check in §10.**

- **One `@font-face` = one font *file*.** The real leverage is whether that file is
  one *weight* or a *variable* font. A **variable font is still one file** but carries
  the whole weight axis — Regular through Bold from a single embed. **If the Core's
  WebKit renders variable fonts (VERIFY, §10), embed one variable file and use weight
  freely.** If not, embed **one static weight** — base it on **Medium / 500** (labels
  hold up at a glance) — and build hierarchy from size + colour, not weight.

- **Recommended family: IBM Plex Sans.** Engineered/technical pedigree, clean and
  modern without being anonymous, excellent **tabular numerals**, OFL (commercial
  embedding fine), part of a superfamily (Sans / Mono / Condensed) if the layout ever
  grows. Reads "instrument" more than a neutral UI face — fits EFAV.
  - **Swap-ready alternatives** (change one embed, nothing else changes): **Inter** if
    you want the type to disappear and let icons/graphs carry the look; **IBM Plex
    Mono / JetBrains Mono** to let the readout/rack-instrument character dominate the
    whole UI (every numeral tabular by definition).
  - **Long labels → IBM Plex Sans Condensed** (or **Barlow Semi Condensed**). On a
    small panel with long labels ("Speech Conditioner", "Priority Ducker"), condensed
    buys label width without dropping point size — see the touch-target note below.
  - *Family is a recommendation, not finalised. Plex Sans is the specced default; if
    labels routinely run long, switch to the condensed variant. Swapping is one embed.*

- **Numerals: tabular lining figures.** UCIs show live dB / Hz / time / fader values.
  Tabular (monospaced) figures keep a readout from changing width as digits change
  (`4.7` → `11.2` must not shift the layout). All recommended families support this;
  it's pinned on the readout role below.

- **Subset before embedding.** A full font is 150–400 KB base64'd into `style.css`;
  the UCI uses ~100 glyphs. Run **`pyftsubset`** (fonttools) to keep Latin + digits +
  the symbols actually used (`. , - + % : dB Hz kHz` etc.), then base64 the subset.
  Cuts the embed by an order of magnitude and keeps the single-file stylesheet lean.
  One extra build step (see §5). **fonttools is a new dependency** — not currently in
  the EFAV stack.

- **Licensing (OFL).** All recommended families are SIL Open Font License — embedding
  and commercial use permitted, but you must **bundle the `OFL.txt`** and not sell the
  font itself. Keep it alongside the font source and reference it. EFAV ships
  commercial product, so do this cleanly.

### Type scale — roles, sized for a 10" panel

Q-SYS UCIs author to a **fixed canvas** (10" 16:10 ≈ **1280×800**); every device —
the 10" panel *and* the iPad — scales that same logical layout. So **one scale**
serves both: size for the 10" panel (the limiting case) and the iPad inherits it
equal-or-crisper. Sizes are canvas px.

```css
.txt-display  { font-size: 26px; font-weight: 600; }   /* page title, once */
.txt-header   { font-size: 20px; font-weight: 600; }   /* section headers */
.txt-label    { font-size: 16px; font-weight: 500; }   /* button labels — workhorse */
.txt-body     { font-size: 14px; font-weight: 400; }   /* descriptions, help */
.txt-readout  { font-size: 20px; font-weight: 500; font-variant-numeric: tabular-nums; }
.txt-caption  { font-size: 13px; font-weight: 400; }   /* units, footnotes only */
```

- **Readout is its own role** — carries `tabular-nums`; the number *is* the content.
- **Weight is an enhancement, not the load-bearing axis.** The `font-weight` steps are
  real only if the variable font renders (§10). Build the scale to **degrade to size +
  colour**: display/header larger and full **NAVY**, body smaller and **STEEL**-grey,
  readout on **ACCENT** — hierarchy survives even at one static weight. Do not let
  hierarchy *depend* on weight.
- **Touch targets constrain the small end.** A comfortable target is ~44–48 canvas px
  (≈7–8 mm here) and the label must fit *inside* it. At ~150 PPI, don't drop readable
  text below ~13 px — that floor is what pushes long labels toward a condensed face.
- Centred section headers with rules are the EFAV house pattern where headers appear.

---

## 7. Buttons — no stroke (flat)

EFAV UCIs use **strokeless** (no-outline) buttons — the flat-instrument look. Two
ways to get there; prefer the native one.

- **Preferred — native.** Stroke is a native button property (`_StrokeColor`,
  `_StrokeWidth`, confirmed in the panel dump). Set **`_StrokeWidth = 0`** in Designer.
  Cleanest — nothing to fight in CSS.
- **CSS fallback** (if driving chrome from the stylesheet):
  ```css
  .btn {
    border: none;
    outline: none;              /* also removes the focus ring — see note */
    box-shadow: none;           /* WebKit sometimes draws a default */
    background-color: #1E3A5F;  /* STEEL — the fill defines the button, not an edge */
  }
  ```

**Design consequence — the fill now carries the edge.** With no stroke, the button's
boundary reads entirely from **fill-to-background contrast**. A strokeless STEEL
button on a NAVY panel reads (real tonal separation); a strokeless navy button on a
navy panel *vanishes*. So no-stroke is paired with a **minimum fill/background
contrast** requirement — corner radius + internal padding then signal "pressable,"
since the edge no longer announces it.

**Focus-ring note.** `outline: none` also kills the keyboard-focus indicator. Moot on
a pure touch panel (no focus ring is ever seen), but if a UCI is ever driven by a
connected keyboard or the Designer preview, this removes the only focus cue. Leave a
CSS comment saying *why* it's off, so it isn't a silent surprise later.

---

## 8. Palette + themes

### EFAV brand (fixed)

| Token | Hex | Use |
|---|---|---|
| NAVY | `#0D1B2A` | Dark backgrounds, dark-on-light text/icons |
| STEEL | `#1E3A5F` | Secondary fills, panel chrome |
| ACCENT | `#2E86AB` | Active / pressed / selected |

The brand three are fixed EFAV identity. The **EFAV Navy** theme below is that
identity rendered into the role tokens; other themes are the sellable multi-theme
system for jobs/clients that don't want EFAV blue.

### Role tokens (every theme fills these nine)

A theme is a dict of nine semantic roles. Same keys, different hex per theme — the
build substitutes them and emits one file per theme (see below).

| Token | Role |
|---|---|
| `bg` | Panel background |
| `surface` | Button / card fill — **must step visibly off `bg`** (strokeless buttons, §7) |
| `surface-hi` | Pressed / active / selected button fill |
| `text` | Display + header text |
| `text-dim` | Body + label text |
| `icon` | Idle icon colour (on `surface`) |
| `icon-hi` | Icon on a pressed/active surface (the invert target) |
| `accent` | Readout, highlight, selection |
| `fault` | Alarm / mute-active |

These are **build-time substitution keys**, not runtime `var()` — the emitted CSS
carries literal hex, so there's no CSS-custom-property dependency on the Core's
WebKit. `icon`/`icon-hi` must each contrast the surface they sit on; where a theme's
`surface-hi` is light (amber, terracotta), `icon-hi` goes **dark**, not white.

### Themes

| Token | EFAV Navy | Slate Light | Graphite | Warm Studio | High-Contrast |
|---|---|---|---|---|---|
| folder | `EFAV Navy/` | `EFAV Slate Light/` | `EFAV Graphite/` | `EFAV Warm Studio/` | `EFAV High-Contrast/` |
| `bg` | `#0D1B2A` | `#FFFFFF` | `#17181A` | `#FFFFFF` | `#000000` |
| `surface` | `#1E3A5F` | `#E7EDF3` | `#2C2F34` | `#F0E8DB` | `#1C1F24` |
| `surface-hi` | `#2E86AB` | `#2E86AB` | `#E0A458` | `#C2703D` | `#00A3E0` |
| `text` | `#E8EEF4` | `#0D1B2A` | `#F2F3F5` | `#33291F` | `#FFFFFF` |
| `text-dim` | `#8DA3BC` | `#5A6B7E` | `#9BA0A8` | `#7A6E5E` | `#B8BFC7` |
| `icon` | `#CBD8E6` | `#1E3A5F` | `#C7CBD1` | `#5C4A34` | `#FFFFFF` |
| `icon-hi` | `#FFFFFF` | `#FFFFFF` | `#201A0E` | `#FFFFFF` | `#000000` |
| `accent` | `#3DA5CE` | `#2E86AB` | `#E0A458` | `#C2703D` | `#00C2FF` |
| `fault` | `#E63946` | `#D62839` | `#E5544B` | `#B23A2E` | `#FF4D4D` |

- **EFAV Navy** is the brand; its `bg → surface` step is deliberately subtle (rack-
  instrument look) — the least forgiving for strokeless buttons, so lean on
  `surface-hi` / corner radius to signal pressability there.
- **Slate Light** is the light counterpart; **Graphite** / **Warm Studio** are the
  no-blue (neutral dark / neutral light) options; **High-Contrast** is the bright-
  room / accessibility fallback.
- These hex sets are the specced defaults — adjust per job, but keep the nine-token
  shape so the build stays a simple dict swap.

### Family-branded themes (added 2026-08-20)

Three more themes, each tied directly to an existing plugin's confirmed body/
mascot colour from `THEME.md` rather than a new invented palette — dark-bodied
like Navy/Graphite, with the *mascot* accent (not the pedal body colour) doing
duty as `surface-hi`/`accent` so pressed/readout states pop against the dark
body.

| Token | EFAV Teal | EFAV Indigo | EFAV Rust |
|---|---|---|---|
| folder | `EFAV Teal/` | `EFAV Indigo/` | `EFAV Rust/` |
| matches | Dynamics/Ducker (teal body, duck accent) | Speech Enhancer (indigo/plum body, parrot accent) | De-esser (rust/terracotta body, snake accent) |
| `bg` | `#0F211D` | `#1B1430` | `#1E120C` |
| `surface` | `#1B4A41` | `#3D2E63` | `#4A2417` |
| `surface-hi` | `#E0932E` | `#D6A24B` | `#8FBF3F` |
| `text` | `#E8F2EF` | `#EDEAF6` | `#F5EDE6` |
| `text-dim` | `#8FB0A8` | `#A79BC4` | `#B39A88` |
| `icon` | `#B9D6CD` | `#C9BEDF` | `#D9C4B4` |
| `icon-hi` | `#201505` | `#2A1D05` | `#16210A` |
| `accent` | `#E0932E` | `#4FBFAE` | `#D07D53` |
| `fault` | `#E5544B` | `#E5484D` | `#C23B2E` |

- **EFAV Teal** — duck yellow-orange mascot accent carries both `surface-hi`
  (button pop) and `accent` (readout).
- **EFAV Indigo** — the parrot mascot is "tropical teal-gold-red"; gold is
  `surface-hi`, teal is `accent`, so both mascot notes stay present instead of
  collapsing to one hue.
- **EFAV Rust** — deliberately the *dark* counterpart to Warm Studio (which
  already owns the light terracotta pairing). Lime-green snake accent as
  `surface-hi` for high pop against the warm-dark body; rust-orange as
  `accent` keeps the rust identity in the readout colour.
- Built with the **current** `build_icons.py` (see note below) — includes the
  `:value(1)` latched-on background tint and the unverified `TOGGLE_PAIRS`
  icon-swap classes. **The other 8 themes above were built with an earlier
  version of the script that has neither** — they're now stale relative to
  the generator. Re-run `build_icons.py` for all themes once `:value(1)` /
  `TOGGLE_PAIRS` are confirmed on hardware (§10) to bring them back in sync,
  rather than assuming the installed Navy/Graphite/etc. `style.css` already
  has these features.

### Build: one folder per theme

**The emitted filename is ALWAYS `style.css` — Q-SYS accepts no other name.** Themes
are separated by **folder**, never by filename. The **folder name becomes the style's
name in the Designer dropdown** (§12), so it must be presentable, not a slug. The
theme system is a **palette dict per theme**; the emitter (§5) loops over them and
writes:

```
themes/
  EFAV Navy/style.css
  EFAV Slate Light/style.css
  EFAV Graphite/style.css
  EFAV Warm Studio/style.css
  EFAV High-Contrast/style.css
  EFAV Teal/style.css
  EFAV Indigo/style.css
  EFAV Rust/style.css
```

The folder name is the user-facing style name; the file inside is always
`style.css`. Icon mask
data and all `.txt-*` / `.btn` structure are identical across every file — only the
nine role hex values change. This generalises §5's fixed-theme branch to N themes
with no extra machinery, and never violates the filename rule.

---

## 9. Validation gate (pre-deploy — standing EFAV rule)

- **CSS brace-depth counter** (Python): walk the emitted `style.css`, track `{`/`}`
  depth, assert it returns to zero and never goes negative. Fail the build on
  imbalance — never emit an unbalanced stylesheet.
- Confirm every `.icon-<slug>` has a non-empty data URI (no truncated base64).
- Confirm **every** emitted file is named exactly `style.css` — themes differ by
  folder, never by filename. A renamed file (`style-navy.css`) is a build failure.

---

## 10. UNRESOLVED / VERIFY before relying on it

1. **Path B vs Path C for recolour (5-min Designer test).** Can a per-state style
   string set `-webkit-mask-image` / `background-color` on the **icon glyph**, or
   does icon recolour only work through the native `_IconColor` property?
   - If style strings reach the icon → the mask + `:active` momentary path (§4)
     works as specced.
   - If only `_IconColor` recolours → volume momentary-recolour may be **native**
     (pressed style string + pressed icon colour), and the masking layer for volume
     becomes redundant. Test before committing the interaction to CSS.
   - Panel dump shows these style strings **empty** in the reference export
     (nothing authored), so their capability is inferred from field names, not
     proven.

2. **Does `:active` fire on the Core's touch panel?** Reliable on desktop WebKit;
   on touch WebKit it sometimes needs a touch listener / `cursor: pointer`, and
   Q-SYS may intercept the touch before the native press state sets. If `:active`
   does not fire, CSS momentary is off the table and the native Pressed slot/style
   string is the only route. Confirm with a throwaway `:active { }` button.

3. **Do the Image slots accept SVG, or PNG only?** Screenshot showed PNGs. If SVG
   isn't accepted in slots, any SVG destined for a slot must be rasterised — and if
   the build script must rasterise SVG at all, add **cairosvg** (or Pillow +
   resvg) to the pipeline. Masking (Path C) does **not** need this — data-URI SVG
   masks fine.

4. **Font embedding — two checks, both on hardware (§6).**
   - **Does base64 `@font-face` render at all** on the locked Core WebKit? If not,
     typography falls back to a WebKit-safe system stack (`-apple-system, "Helvetica
     Neue", Helvetica, Arial, sans-serif`) and the embed is dropped.
   - **Does the Core's WebKit render a *variable* font?** If yes, embed one variable
     file and use the weight steps in the scale. If no, embed one static weight
     (Medium/500) and let the scale degrade to size + colour (§6). Decide this before
     choosing which font file to subset and embed.

---

## 11. Conventions

- Output: `/mnt/user-data/outputs/`. Build script scratch: `/home/claude/`.
- Emitted stylesheet filename: **always exactly `style.css`** (Q-SYS requirement).
  Multiple themes are separate folders each holding a `style.css` — never renamed
  files (§8).
- WebKit constraint checklist (all apply): no `aspect-ratio`, no `backdrop-filter`,
  no external (URL-fetched) fonts — **one embedded/subset `@font-face` is allowed**
  (§6, verify §10), no CSS custom properties inside `@keyframes`, `-webkit-` prefix on
  mask properties, graceful on `file://`.
- Re-runnable build, deterministic output, sorted for clean diffs.

---

## 12. Install location (Q-SYS Designer)

Where the emitted files go and how they get applied. This is why the filename is
fixed and themes are folders.

### The Styles directory

Q-SYS Designer scans a fixed directory for installable styles:

```
\Users\<user-name>\Documents\QSC\Q-SYS Designer\Styles\
```

Inside it, **one folder per style; the folder name IS the style name** shown in
Designer's dropdown. Each folder contains a file named exactly **`style.css`**.

The build emits into `themes/` (§8) with exactly this shape — copy each theme folder
straight into the Styles directory:

```
…\Q-SYS Designer\Styles\
  EFAV Navy\style.css
  EFAV Slate Light\style.css
  EFAV Graphite\style.css
  EFAV Warm Studio\style.css
  EFAV High-Contrast\style.css
  EFAV Teal\style.css
  EFAV Indigo\style.css
  EFAV Rust\style.css
```

**Correction (per `build_icons.py`'s own docstring, superseding the base64 plan
below):** base64-embedded icons/font were tried on hardware and rendered
nothing — the actual shipping build uses **real files** (`icons/<slug>.<ext>`,
`IBMPlexSans-Medium-subset.ttf`, `OFL.txt`) referenced by relative path
alongside `style.css`, matching the proven Teams-package pattern. Each theme
folder therefore needs to be copied **whole**, not just its `style.css`. The
paragraph immediately below describes the originally-planned base64 approach
and is kept for history — do not follow it for the copy step.

Because icons and the font were originally planned as inlined base64 data URIs (see correction above), **each folder needs only
`style.css`** — no image or font files to copy alongside, nothing to path-break.
(Standard Q-SYS styles keep supporting images/fonts in the folder and reference them
by subpath; the embed approach removes that entirely.)

### Install + apply

1. **Install to the design:** in Designer, `Tools > Design Resources` (labelled
   *Manage UCI Styles* in some versions) → select the style from the Available list →
   **Install Style**. Editing `style.css` later prompts Designer to update the
   installed copy (or enable `Tools > Auto Update Styles`).
2. **Apply to a UCI:** select the UCI under *User Control Interfaces* → set **Style**
   in the UCI Properties pane. Use each element's **CSS Class Name** property to
   attach the `.icon-*`, `.txt-*`, `.btn` classes from `style.css`.

### Caveat

The **web-browser UCI viewer in Q-SYS Core Manager does not render CSS UCI styles**
(per current QSC docs). The styling shows on hardware touch panels, the iOS app, and
in Designer — **do not judge a theme from the Core Manager browser preview.** This is
distinct from the `:active` / variable-font hardware checks in §10; it's a viewer
limitation, not a rendering unknown.

## Fader / knob CSS capability — measured, not assumed (2026-08-19)

Probed with a purpose-built diagnostic stylesheet (`themes/EFAV Fader Probe/`),
one property per class so each result is unambiguous. Run against a real UCI.

| property | on a FADER |
|---|---|
| `background-color` | **works** |
| `color` | **works** |
| `border` | **works** |
| `border-radius` | **no effect** |
| `background-image` | **NO EFFECT** |
| `:value(N)` | **works**, and updates as the fader is adjusted |

**CSS reaches a fader's COLOURS but never its GEOMETRY.** A fader cap cannot
be given custom artwork through CSS whatever class it carries — including the
`level-knob` class Q-SYS auto-assigns. That class is a styling handle, not a
route into the control's internals.

Buttons and LEDs behave differently: `background-image` is proven there (it is
how the icon themes work), so **state-based controls can be fully styled in
CSS while continuous ones cannot**. That is the line the control arsenal
splits along:

- **toggle / button / LED → CSS class** (`:value(N)` covers every state)
- **fader / knob / meter → plugin artwork** (`EFAV Family/_lib/efav_controls.lua`)

The one thing CSS cannot do even for buttons is **tween between states** —
`:value(1)` swaps instantly. An animated sliding toggle therefore stays a
plugin control.

### What `:value(N)` matches — settled

**`N` is the control's VALUE, not its position.** Established by varying the
range: on a Float 0–100 fader the value and the percentage of travel are
numerically identical, so early results could not tell them apart. On a
−100…+20 dB fader the colours change **only above 0 dB** — precisely where
non-negative integers begin. Position is ruled out.

So a control's usable CSS states are **the integers inside its own range**:

| control range | usable `:value(N)` states |
|---|---|
| Float 0–100 | 101 |
| Float 0–4 (a 5-way selector) | 5 |
| Toggle button | 2 |
| Gain fader, −100…+20 dB | only the top 20 — useless for the working range |

**Practical rule: anything intended for CSS state styling should be declared
with a 0..N FLOAT range, not dB.** Buttons and toggles are unaffected — 0/1
is already what they are.

**Negative values DO parse.** Confirmed on a −100…+20 dB gain fader: a
14-step ladder from −80 dB upward changes colour through the negative range,
and a lone `:value(-40)` rule fires at −40. So the earlier "nothing below
0 dB" was simply the absence of matching rules, not a parser limit.

**Consequence: any control range works, dB included.** A gain fader can be
colour-coded across its whole working travel in pure CSS, with no conversion
layer and no need to redeclare it as a 0..N float. The fallback noted in the
probe stylesheet is not required.

**Matching is EQUALITY, not threshold.** A sparse ladder leaves base-colour
gaps between its steps — confirmed on a meter, which showed grey between the
coloured bands.

**Consequence: a continuous ladder needs one rule per integer value.** For a
−100…+20 dB control that is 121 rules. Verbose to hand-write, trivial to
generate — and since the rules are pure colour, a build script can emit them
from a ramp definition per theme, exactly as it already bakes icon tints.

### Summary — what CSS can and cannot do to a UCI control

| | CSS | plugin artwork |
|---|---|---|
| colour by value (any range, dB included) | ✅ | ✅ |
| custom cap / pointer / geometry | ❌ | ✅ |
| animation / tweening between states | ❌ | ✅ |
| icons and button states | ✅ | — |

So the split for the control arsenal is by *what changes*, not by control
type: **colour responds to value in CSS; anything that moves or is shaped
needs the plugin.**
