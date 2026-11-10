"""
css_builder_gui.py — Tkinter form front-end over css_builder_core.py.

Per CSS_STYLE_BUILDER.md §4: Tkinter (stdlib, no server, no browser) so the
v2 commercial goal ("an integrator runs this on their own Windows laptop with
zero setup") stays true from day one. This file only assembles a form and
calls the proven engine — it does not invent any new CSS technique.

Run: python css_builder_gui.py
"""
import shutil
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageTk

import css_builder_core as core
import css_builder_preview as preview
import efav_presets as presets

ROLE_LABELS = {
    "bg": "Background (bg)",
    "surface": "Surface — button/card fill",
    "surface-hi": "Surface hi — pressed/active fill",
    "text": "Text — display/header",
    "text-dim": "Text dim — body/label",
    "icon": "Icon — idle colour",
    "icon-hi": "Icon hi — on pressed/active surface",
    "accent": "Accent — readout/highlight",
    "fault": "Fault — alarm/mute-active",
}
TYPE_SCALE_LABELS = {
    "display": "Display (px)",
    "header": "Header (px)",
    "label": "Label (px)",
    "body": "Body (px)",
    "readout": "Readout (px)",
    "caption": "Caption (px)",
}
CUSTOM_FONT_LABEL = "Custom…"
INVALID_NAME_CHARS = '<>:"/\\|?*'


def group_for_entry(entry: dict, icons_dir: Path) -> str:
    try:
        rel = entry["path"].relative_to(icons_dir)
    except ValueError:
        return "Custom"
    return rel.parts[0] if len(rel.parts) > 1 else "Other"


class StyleBuilderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EFAV UCI Style Builder")
        self.geometry("1180x760")
        self.minsize(1000, 680)

        # --- scan the stock icon library once ---------------------------
        groups, self.skipped = core.scan_icons(presets.ICONS_DIR, root_for_relpath=presets.ROOT)
        # Exclude files that are only meant to be used as toggle-pair on-state
        # art (efav_presets.TOGGLE_ON_STATE_ART) — see build_icons.py for why.
        groups = {
            slug: [e for e in entries if e["path"] not in presets.EXCLUDED_ICON_FILES]
            for slug, entries in groups.items()
        }
        groups = {slug: entries for slug, entries in groups.items() if entries}
        self.stock_winners, self.dedupe_report = core.resolve_winners(groups, root_for_relpath=presets.ROOT)
        self.custom_icons: dict[str, dict] = {}  # slug -> entry, user-added this session
        self.logo_path: Path | None = None
        self.custom_font_path: Path | None = None
        self._preview_photo = None  # keep a reference so Tk doesn't GC it
        self._icon_thumbnails: dict[str, ImageTk.PhotoImage] = {}  # keep refs so Tk doesn't GC them
        self._preview_regions: dict[str, tuple[int, int, int, int]] = {}
        self._preview_demo_state: dict[str, bool] = {}
        self._preview_tmp_root: Path | None = None  # the mkdtemp'd folder itself, deleted on next build/close
        self._preview_build_dir: Path | None = None  # last full build's out_dir (tmp_root/name), reused for cheap click re-renders
        self._preview_theme: dict | None = None
        self._preview_type_scale: dict | None = None
        self._preview_page_chrome: bool = True
        self._preview_toggle_pairs: list = []

        self.color_vars: dict[str, tk.StringVar] = {
            k: tk.StringVar(value=presets.BLANK_DEFAULT[k]) for k in core.ROLE_KEYS
        }
        self.scale_vars: dict[str, tk.IntVar] = {
            k: tk.IntVar(value=v) for k, v in core.DEFAULT_TYPE_SCALE.items()
        }
        self.name_var = tk.StringVar(value="My New Theme")
        self.start_mode_var = tk.StringVar(value="blank")
        self.duplicate_var = tk.StringVar(value=next(iter(presets.THEMES)))
        self.font_var = tk.StringVar(value=presets.DEFAULT_FONT)
        self.custom_font_family_var = tk.StringVar(value="")
        self.page_chrome_var = tk.BooleanVar(value=True)
        # Individually selectable — confirmed working on hardware, all on by
        # default. Keyed by combined_name (TOGGLE_PAIRS[i][2]).
        self.toggle_pair_vars: dict[str, tk.BooleanVar] = {
            combined: tk.BooleanVar(value=True) for _off, _on, combined in presets.TOGGLE_PAIRS
        }
        self.press_feedback_var = tk.BooleanVar(value=False)
        self.momentary_swap_var = tk.BooleanVar(value=True)  # partially verified — on by default to test
        self.icon_vars: dict[str, tk.BooleanVar] = {
            slug: tk.BooleanVar(value=True) for slug in self.stock_winners
        }

        self._build_layout()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.update_preview()

    def _on_close(self):
        if self._preview_tmp_root is not None:
            shutil.rmtree(self._preview_tmp_root, ignore_errors=True)
        self.destroy()

    # ------------------------------------------------------------------ UI
    def _build_layout(self):
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)

        form_container = ttk.Frame(outer, width=520)
        form_container.pack(side="left", fill="both", expand=False)
        form_container.pack_propagate(False)

        canvas = tk.Canvas(form_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(form_container, orient="vertical", command=canvas.yview)
        self.form = ttk.Frame(canvas)
        self.form.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.form, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        right = ttk.Frame(outer)
        right.pack(side="left", fill="both", expand=True)

        self._build_form(self.form)
        self._build_preview_pane(right)

    def _section(self, parent, title):
        lbl = ttk.Label(parent, text=title, font=("Segoe UI", 11, "bold"))
        lbl.pack(anchor="w", padx=12, pady=(16, 4))
        return lbl

    def _build_form(self, f):
        self._section(f, "Theme")
        row = ttk.Frame(f)
        row.pack(fill="x", padx=12)
        ttk.Label(row, text="Name").pack(side="left")
        ttk.Entry(row, textvariable=self.name_var, width=32).pack(side="left", padx=8)

        self._section(f, "Starting point")
        blank_row = ttk.Frame(f)
        blank_row.pack(fill="x", padx=12)
        ttk.Radiobutton(
            blank_row, text="Build new from scratch (EFAV Navy defaults, edit freely)",
            variable=self.start_mode_var, value="blank", command=self._on_start_mode_change,
        ).pack(anchor="w")
        dup_row = ttk.Frame(f)
        dup_row.pack(fill="x", padx=12, pady=(2, 0))
        ttk.Radiobutton(
            dup_row, text="Duplicate an existing theme:",
            variable=self.start_mode_var, value="duplicate", command=self._on_start_mode_change,
        ).pack(side="left")
        self.duplicate_combo = ttk.Combobox(
            dup_row, textvariable=self.duplicate_var, values=list(presets.THEMES.keys()),
            state="readonly", width=22,
        )
        self.duplicate_combo.pack(side="left", padx=8)
        self.duplicate_combo.bind("<<ComboboxSelected>>", lambda e: self._on_start_mode_change())

        self._section(f, "Colour roles")
        for key in core.ROLE_KEYS:
            self._color_row(f, key)

        self._section(f, "Type scale (size only — weight/colour fixed per role)")
        for key in core.TYPE_SCALE_ROLES:
            row = ttk.Frame(f)
            row.pack(fill="x", padx=12, pady=1)
            ttk.Label(row, text=TYPE_SCALE_LABELS[key], width=26).pack(side="left")
            ttk.Spinbox(row, from_=8, to=72, textvariable=self.scale_vars[key], width=6).pack(side="left")

        self._section(f, "Font")
        font_row = ttk.Frame(f)
        font_row.pack(fill="x", padx=12)
        values = list(presets.FONT_OPTIONS.keys()) + [CUSTOM_FONT_LABEL]
        self.font_combo = ttk.Combobox(font_row, textvariable=self.font_var, values=values, state="readonly", width=24)
        self.font_combo.pack(side="left")
        self.font_combo.bind("<<ComboboxSelected>>", lambda e: self._on_font_change())
        self.custom_font_btn = ttk.Button(font_row, text="Browse…", command=self._browse_custom_font, state="disabled")
        self.custom_font_btn.pack(side="left", padx=8)
        fam_row = ttk.Frame(f)
        fam_row.pack(fill="x", padx=12, pady=(2, 0))
        ttk.Label(fam_row, text="Family name").pack(side="left")
        self.custom_font_family_entry = ttk.Entry(fam_row, textvariable=self.custom_font_family_var, width=24, state="disabled")
        self.custom_font_family_entry.pack(side="left", padx=8)
        ttk.Label(
            f, text="Licensing for a custom font is your responsibility — it's embedded in the output.",
            foreground="#a00",
        ).pack(anchor="w", padx=12, pady=(2, 0))

        self._section(f, "Page chrome")
        ttk.Checkbutton(
            f, text="This theme sets the page/header/footer background\n(uncheck for an icon-colour-only theme, e.g. \"Black Icons\")",
            variable=self.page_chrome_var,
        ).pack(anchor="w", padx=12)

        self._section(f, "Icon set")
        note = ttk.Label(
            f, text=f"{len(self.stock_winners)} icons found in Icons/. Uncheck to omit from this theme.",
            foreground="#555",
        )
        note.pack(anchor="w", padx=12)
        self._icon_checklist(f)
        ttk.Button(f, text="Add custom icon…", command=self._add_custom_icon).pack(anchor="w", padx=12, pady=(4, 0))

        self._section(f, "Toggle classes (CONFIRMED WORKING on hardware — :value(1) background-image swap)")
        for off_slug, on_slug, combined in presets.TOGGLE_PAIRS:
            ttk.Checkbutton(
                f, text=f".icon-{combined}  ({off_slug} → {on_slug}, tinted to `fault`)",
                variable=self.toggle_pair_vars[combined],
                command=self.update_preview,
            ).pack(anchor="w", padx=12)

        ttk.Checkbutton(
            f, text="Icon recolours on state for ordinary (non-toggle) icons\n"
                    "(CONFIRMED on Momentary controls, CONFIRMED NOT on Trigger controls — e.g. most transport buttons)",
            variable=self.momentary_swap_var,
            command=self.update_preview,
        ).pack(anchor="w", padx=12, pady=(4, 0))
        ttk.Checkbutton(
            f, text="Include press-feedback on every icon\n(CONFIRMED NOT WORKING on hardware — kept for reference only, see CSS comments)",
            variable=self.press_feedback_var,
        ).pack(anchor="w", padx=12, pady=(4, 0))

        self._section(f, "Branding logo (optional, not tinted)")
        logo_row = ttk.Frame(f)
        logo_row.pack(fill="x", padx=12)
        self.logo_label = ttk.Label(logo_row, text="(none)")
        self.logo_label.pack(side="left")
        ttk.Button(logo_row, text="Choose…", command=self._browse_logo).pack(side="left", padx=8)
        ttk.Button(logo_row, text="Clear", command=self._clear_logo).pack(side="left")

        ttk.Frame(f, height=20).pack()

    def _color_row(self, parent, key):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=12, pady=1)
        ttk.Label(row, text=ROLE_LABELS[key], width=30).pack(side="left")
        swatch = tk.Label(row, width=3, relief="sunken", bg=self.color_vars[key].get())
        swatch.pack(side="left", padx=4)
        entry = ttk.Entry(row, textvariable=self.color_vars[key], width=9)
        entry.pack(side="left")

        def sync_swatch(*_a, s=swatch, v=self.color_vars[key]):
            val = v.get()
            if len(val) == 7 and val.startswith("#"):
                try:
                    s.configure(bg=val)
                except tk.TclError:
                    pass

        self.color_vars[key].trace_add("write", sync_swatch)

        def pick(s=swatch, v=self.color_vars[key]):
            _rgb, hexval = colorchooser.askcolor(color=v.get(), title=ROLE_LABELS[key])
            if hexval:
                v.set(hexval.upper())

        ttk.Button(row, text="…", width=3, command=pick).pack(side="left", padx=4)

    THUMB_SIZE = 22
    THUMB_TINT = "#404040"  # fixed neutral colour, independent of each source icon's own fill

    def _thumbnail_for(self, entry: dict) -> ImageTk.PhotoImage | None:
        """Small tinted preview image for a checklist row — cached by path so
        re-opening tabs or adding custom icons doesn't re-render existing ones."""
        key = str(entry["path"])
        if key in self._icon_thumbnails:
            return self._icon_thumbnails[key]
        im = preview.load_icon_image(entry["path"])
        if im is None:
            return None
        im = preview.tint_image_inmemory(im, self.THUMB_TINT)
        im.thumbnail((self.THUMB_SIZE, self.THUMB_SIZE), Image.LANCZOS)
        # pad to a fixed square so rows line up regardless of each icon's own aspect ratio
        canvas_im = Image.new("RGBA", (self.THUMB_SIZE, self.THUMB_SIZE), (0, 0, 0, 0))
        ox, oy = (self.THUMB_SIZE - im.width) // 2, (self.THUMB_SIZE - im.height) // 2
        canvas_im.alpha_composite(im, (ox, oy))
        photo = ImageTk.PhotoImage(canvas_im)
        self._icon_thumbnails[key] = photo
        return photo

    def _icon_row(self, parent, slug: str, entry: dict, row: int, col: int):
        cell = ttk.Frame(parent)
        cell.grid(row=row, column=col, sticky="w", padx=6, pady=1)
        thumb = self._thumbnail_for(entry)
        tk.Label(cell, image=thumb, width=self.THUMB_SIZE, height=self.THUMB_SIZE).pack(side="left")
        ttk.Checkbutton(cell, text=slug, variable=self.icon_vars[slug]).pack(side="left")

    def _icon_checklist(self, parent):
        # A ttk.Notebook (tabs) doesn't scroll or wrap — with 17+ icon groups
        # and growing, tabs past the visible width become unreachable, no
        # scroll affordance at all (this was a real bug, not cosmetic). The
        # whole form is already inside a vertically-scrollable Canvas, so a
        # flat list of group headers + icon grids scales to any number of
        # groups for free, instead of fighting Tk's fixed-width tab strip.
        groups: dict[str, list[str]] = {}
        for slug, entry in self.stock_winners.items():
            groups.setdefault(group_for_entry(entry, presets.ICONS_DIR), []).append(slug)

        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="x", padx=12, pady=4)
        for group_name in sorted(groups):
            ttk.Label(list_frame, text=group_name, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 2))
            grid = ttk.Frame(list_frame)
            grid.pack(fill="x")
            for i, slug in enumerate(sorted(groups[group_name])):
                self._icon_row(grid, slug, self.stock_winners[slug], i // 2, i % 2)
        self.custom_icon_frame = ttk.Frame(parent)
        self.custom_icon_frame.pack(fill="x", padx=12)

    def _build_preview_pane(self, parent):
        self.preview_canvas = tk.Canvas(parent, relief="groove", background="#222222", highlightthickness=0)
        self.preview_canvas.pack(padx=16, pady=16, fill="both", expand=True)
        self._preview_image_id = None
        self.preview_canvas.bind("<Button-1>", self._on_preview_click)
        self.preview_canvas.configure(cursor="hand2")

        hint = ttk.Label(
            parent, text="Click a source button or a toggle-pair footer icon in the preview to see its on-state.",
            foreground="#555",
        )
        hint.pack()

        btn_row = ttk.Frame(parent)
        btn_row.pack(pady=(0, 12))
        ttk.Button(btn_row, text="Update Preview", command=self.update_preview).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Install to Q-Sys Designer", command=self.do_install).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Export Package…", command=self.do_export).pack(side="left", padx=6)

        self.status_var = tk.StringVar(value="")
        ttk.Label(parent, textvariable=self.status_var, foreground="#a00").pack(pady=(0, 10))

    # -------------------------------------------------------------- events
    def _on_start_mode_change(self):
        if self.start_mode_var.get() != "duplicate":
            return
        theme = presets.THEMES[self.duplicate_var.get()]
        for key in core.ROLE_KEYS:
            self.color_vars[key].set(theme[key])
        self.page_chrome_var.set(theme["page_chrome"])

    def _on_font_change(self):
        is_custom = self.font_var.get() == CUSTOM_FONT_LABEL
        state = "normal" if is_custom else "disabled"
        self.custom_font_btn.configure(state=state)
        self.custom_font_family_entry.configure(state=state)

    def _browse_custom_font(self):
        path = filedialog.askopenfilename(title="Choose a font file", filetypes=[("Font files", "*.ttf *.otf")])
        if not path:
            return
        self.custom_font_path = Path(path)
        if not self.custom_font_family_var.get():
            self.custom_font_family_var.set(self._detect_family_name(self.custom_font_path))

    @staticmethod
    def _detect_family_name(path: Path) -> str:
        try:
            from fontTools import ttLib
            font = ttLib.TTFont(str(path))
            name = font["name"].getDebugName(1)
            if name:
                return name
        except Exception:
            pass
        return path.stem

    def _add_custom_icon(self):
        paths = filedialog.askopenfilenames(title="Add custom icon(s)", filetypes=[("Icon files", "*.svg *.png")])
        for p in paths:
            path = Path(p)
            slug, res = core.slugify(path.stem)
            if not slug:
                continue
            is_svg = path.suffix.lower() == ".svg"
            width = res if res is not None else (core.png_width(path) if not is_svg else 0)
            entry = {"path": path, "is_svg": is_svg, "width": width, "ext": path.suffix.lower()}
            self.custom_icons[slug] = entry
            var = tk.BooleanVar(value=True)
            self.icon_vars[slug] = var
            cell = ttk.Frame(self.custom_icon_frame)
            cell.pack(anchor="w", pady=1)
            thumb = self._thumbnail_for(entry)
            tk.Label(cell, image=thumb, width=self.THUMB_SIZE, height=self.THUMB_SIZE).pack(side="left")
            ttk.Checkbutton(cell, text=f"{slug} (custom)", variable=var).pack(side="left")

    def _browse_logo(self):
        path = filedialog.askopenfilename(title="Choose a logo image", filetypes=[("Image files", "*.svg *.png")])
        if path:
            self.logo_path = Path(path)
            self.logo_label.configure(text=self.logo_path.name)

    def _clear_logo(self):
        self.logo_path = None
        self.logo_label.configure(text="(none)")

    # --------------------------------------------------------------- build
    def _gather_theme(self) -> dict:
        theme = {k: v.get().upper() for k, v in self.color_vars.items()}
        for k, v in theme.items():
            if len(v) != 7 or not v.startswith("#"):
                raise ValueError(f"'{ROLE_LABELS[k]}' is not a valid #RRGGBB colour: {v!r}")
        return theme

    def _gather_type_scale(self) -> dict:
        return {k: v.get() for k, v in self.scale_vars.items()}

    def _gather_winners(self) -> dict:
        winners = {slug: e for slug, e in self.stock_winners.items() if self.icon_vars[slug].get()}
        for slug, e in self.custom_icons.items():
            if self.icon_vars[slug].get():
                winners[slug] = e
        return winners

    def _gather_toggle_pairs(self) -> list:
        return [
            (off, on, combined) for off, on, combined in presets.TOGGLE_PAIRS
            if self.toggle_pair_vars[combined].get()
        ]

    def _resolve_font(self, tmp_dir: Path) -> tuple[Path, str, Path | None]:
        choice = self.font_var.get()
        if choice == CUSTOM_FONT_LABEL:
            if not self.custom_font_path:
                raise ValueError("Choose a custom font file first.")
            src = self.custom_font_path
            family = self.custom_font_family_var.get().strip() or self._detect_family_name(src)
            license_path = None
        else:
            opt = presets.FONT_OPTIONS[choice]
            src, license_path, family = opt["path"], opt["license"], choice
        subset_path = tmp_dir / f"{src.stem}-subset.ttf"
        core.subset_font(src, subset_path)
        return subset_path, family, license_path

    def _validate_name(self, name: str):
        if not name.strip():
            raise ValueError("Theme name can't be empty.")
        if any(c in name for c in INVALID_NAME_CHARS):
            raise ValueError(f"Theme name can't contain any of: {INVALID_NAME_CHARS}")

    def _build(self, output_root: Path, clean: bool) -> tuple[Path, list[str]]:
        name = self.name_var.get().strip()
        self._validate_name(name)
        theme = self._gather_theme()
        type_scale = self._gather_type_scale()
        winners = self._gather_winners()
        if not winners:
            raise ValueError("At least one icon must be selected.")

        tmp_dir = Path(tempfile.mkdtemp(prefix="css_builder_font_"))
        try:
            font_path, font_family, font_license = self._resolve_font(tmp_dir)
            toggle_pairs = self._gather_toggle_pairs() or None
            out_dir, errors = core.build_theme(
                name=name,
                theme=theme,
                winners=winners,
                output_root=output_root,
                font_path=font_path,
                font_family=font_family,
                font_license_path=font_license,
                type_scale=type_scale,
                include_page_chrome=self.page_chrome_var.get(),
                toggle_pairs=toggle_pairs,
                toggle_on_state_art=presets.TOGGLE_ON_STATE_ART if toggle_pairs else None,
                press_feedback=self.press_feedback_var.get(),
                momentary_icon_swap=self.momentary_swap_var.get(),
                logo_path=self.logo_path,
                clean=clean,
            )
            return out_dir, errors
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # ------------------------------------------------------------ actions
    def update_preview(self):
        """Full rebuild — call after changing colours, icons, font, toggles,
        etc. Keeps the built temp dir + a snapshot of the settings used
        (self._preview_*) alive so clicking inside the preview afterward can
        re-render cheaply via _render_preview_now() without rebuilding, and
        without drifting from whatever the user is mid-editing in the form."""
        self.status_var.set("")
        old_tmp_root = self._preview_tmp_root
        try:
            tmp_root = Path(tempfile.mkdtemp(prefix="css_builder_preview_"))
            out_dir, errors = self._build(tmp_root, clean=False)
            if errors:
                self.status_var.set("Validation failed:\n" + "\n".join(errors))
                shutil.rmtree(tmp_root, ignore_errors=True)
                return
            self._preview_tmp_root = tmp_root
            self._preview_build_dir = out_dir
            self._preview_theme = self._gather_theme()
            self._preview_type_scale = self._gather_type_scale()
            self._preview_page_chrome = self.page_chrome_var.get()
            self._preview_toggle_pairs = self._gather_toggle_pairs()
            self._preview_demo_state = {}
            self._render_preview_now()
        except Exception as e:
            self.status_var.set(f"Preview error: {e}")
        finally:
            if old_tmp_root is not None:
                shutil.rmtree(old_tmp_root, ignore_errors=True)

    def _render_preview_now(self):
        """Fast path: re-render from the LAST successful update_preview()
        build (cached theme/type-scale/toggle-pairs snapshot + already-tinted
        icon files on disk) — no rebuild, safe to call on every click."""
        if self._preview_build_dir is None:
            return
        icons_dir = self._preview_build_dir / "icons"
        winners = {p.stem: p for p in icons_dir.glob("*") if not p.stem.endswith("-fault")}
        font_files = list(self._preview_build_dir.glob("*.ttf"))
        img, regions = preview.render_preview(
            self._preview_theme, winners, font_files[0],
            type_scale=self._preview_type_scale,
            include_page_chrome=self._preview_page_chrome,
            toggle_pairs=self._preview_toggle_pairs or None,
            icons_dir=icons_dir,
            demo_state=self._preview_demo_state,
        )
        self._preview_regions = regions
        self._preview_photo = ImageTk.PhotoImage(img)
        self.preview_canvas.delete("all")
        self.preview_canvas.configure(width=img.width, height=img.height)
        self.preview_canvas.create_image(0, 0, anchor="nw", image=self._preview_photo)

    def _on_preview_click(self, event):
        for key, (x1, y1, x2, y2) in self._preview_regions.items():
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self._preview_demo_state[key] = not self._preview_demo_state.get(key, False)
                self._render_preview_now()
                return

    def do_install(self):
        styles_root = presets.OUTPUT_ROOT
        name = self.name_var.get().strip()
        target = styles_root / name
        if target.exists():
            if not messagebox.askyesno("Overwrite existing style?", f'"{name}" already exists in the Styles folder. Overwrite it?'):
                return
        try:
            styles_root.mkdir(parents=True, exist_ok=True)
            out_dir, errors = self._build(styles_root, clean=True)
            if errors:
                messagebox.showerror("Validation failed", "\n".join(errors))
                return
            messagebox.showinfo("Installed", f"Installed to:\n{out_dir}")
            self.status_var.set(f"Installed to {out_dir}")
        except Exception as e:
            messagebox.showerror("Install failed", str(e))

    def do_export(self):
        dest = filedialog.askdirectory(title="Export to folder")
        if not dest:
            return
        dest_root = Path(dest)
        name = self.name_var.get().strip()
        target = dest_root / name
        if target.exists():
            if not messagebox.askyesno("Overwrite existing folder?", f'"{name}" already exists there. Overwrite it?'):
                return
        try:
            out_dir, errors = self._build(dest_root, clean=True)
            if errors:
                messagebox.showerror("Validation failed", "\n".join(errors))
                return
            messagebox.showinfo("Exported", f"Exported to:\n{out_dir}")
            self.status_var.set(f"Exported to {out_dir}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))


if __name__ == "__main__":
    app = StyleBuilderApp()
    app.mainloop()
