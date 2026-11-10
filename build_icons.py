"""
build_icons.py — batch build of the stock EFAV themes.

Thin CLI wrapper: all actual logic lives in css_builder_core.py (the generic,
hardware-proven engine) and efav_presets.py (the EFAV-specific theme data).
This script just loops css_builder_core.build_theme() over efav_presets.THEMES
— the fast path for rebuilding all 7 stock EFAV themes at once. It is not
replaced by css_builder_gui.py, which builds one arbitrary theme from a form.

Re-run after dropping new files in Icons/ or editing efav_presets.THEMES.
"""
import sys

import css_builder_core as core
import efav_presets as presets


def main():
    if not presets.FONT_PATH.exists():
        print(f"ERROR: font not found at {presets.FONT_PATH} — run the subsetting step first.", file=sys.stderr)
        sys.exit(1)

    groups, skipped = core.scan_icons(presets.ICONS_DIR, root_for_relpath=presets.ROOT)
    # Drop files that are only meant to be used as toggle-pair on-state art
    # (see efav_presets.TOGGLE_ON_STATE_ART) — they'd otherwise also become a
    # redundant ordinary icon class tinted to the plain `icon` colour.
    groups = {
        slug: [e for e in entries if e["path"] not in presets.EXCLUDED_ICON_FILES]
        for slug, entries in groups.items()
    }
    groups = {slug: entries for slug, entries in groups.items() if entries}
    winners, dedupe_report = core.resolve_winners(groups, root_for_relpath=presets.ROOT)

    print(f"Scanned {presets.ICONS_DIR}: {sum(len(v) for v in groups.values()) + len(skipped)} files found, "
          f"{len(winners)} unique icon slugs resolved, {len(skipped)} non-svg/png skipped.\n")

    if dedupe_report:
        print("--- dedupe log ---")
        for line in dedupe_report:
            print(line)
        print()

    if skipped:
        print("--- skipped (not .svg/.png) ---")
        for p in skipped:
            print(p.relative_to(presets.ROOT))
        print()

    all_errors = []
    for name, theme in presets.THEMES.items():
        out_dir, errors = core.build_theme(
            name=name,
            theme=theme,
            winners=winners,
            output_root=presets.OUTPUT_ROOT,
            font_path=presets.FONT_PATH,
            font_family=presets.FONT_FAMILY,
            font_license_path=presets.FONT_LICENSE_PATH,
            include_page_chrome=theme["page_chrome"],
            toggle_pairs=presets.TOGGLE_PAIRS,
            toggle_on_state_art=presets.TOGGLE_ON_STATE_ART,
            # Confirmed NOT working on hardware (isolated :active test) —
            # see css_builder_core.build_theme_css docstring. Off by default.
            press_feedback=False,
            # CONFIRMED WORKING on Momentary controls, CONFIRMED NOT WORKING
            # on Trigger controls (no readable Value on hardware — commonly
            # transport buttons). Still worth shipping on: it's free press
            # feedback wherever a control genuinely is Momentary, and a no-op
            # everywhere else. For Trigger buttons use the native Pressed
            # Image slot with the matching <slug>-hi file instead.
            momentary_icon_swap=True,
            # Only ever touch folders this script owns (its own THEMES keys) —
            # never wipe OUTPUT_ROOT wholesale, it may hold unrelated
            # hand-authored work (e.g. themes/EFAV Fader Probe/, not ours).
            clean=True,
        )
        if errors:
            all_errors.extend(f"{out_dir / 'style.css'}: {e}" for e in errors)
            print(f"FAILED validation, not writing: {out_dir / 'style.css'}")
            for e in errors:
                print(f"  - {e}")
            continue
        css_size = (out_dir / "style.css").stat().st_size
        print(f"wrote {out_dir / 'style.css'}  ({css_size:,} bytes CSS, {len(winners)} icon files, 1 font file)")

    print()
    if all_errors:
        print(f"BUILD FAILED — {len(all_errors)} validation error(s).", file=sys.stderr)
        sys.exit(1)
    print(f"Icon classes: {', '.join('.icon-' + s for s in sorted(winners))}")
    print("Build OK.")


if __name__ == "__main__":
    main()
