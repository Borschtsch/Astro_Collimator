"""Tk review workflow; image analysis itself has no UI or network dependencies."""

from dataclasses import asdict, replace
import json
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from time import monotonic
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont

import cv2
import numpy as np

from .app_options import OptionsStore, TelescopeProfile
from .ui_platform import bind_wheel, wheel_direction
from .feature_detection import (DetectionResult, EdgeCandidate, FEATURE_NAMES,
                               FEATURE_COLORS, required_features, accepts_reference, SOFT_EDGE_WIDTH, analyze_frame, concentric_guides, circle_from_points)
from .setup_dialog import SetupDialog
from .edge_tracking import merge_tracking
from .collimation_guidance import alignment_advice
from .live_detection import SteadyFrameAverage, can_track_locally, detect_live


class ReviewTools:
    def build_review_tools(self, options_store):
        self.options_store = options_store or OptionsStore()
        self.options_error = None
        try:
            self.profile = self.options_store.load()
        except (ValueError, OSError) as error:
            self.profile = TelescopeProfile()
            self.options_error = str(error)
        self.setup_dialog = None
        self.source_mode = "camera"
        self.source_description = "Live camera"
        self.view_frozen = False
        self.detection = None
        self.observations_current = False
        self.selections = {}
        self.confirmed = set()
        self.manual_points = {}
        self.manual_adjustments = {}
        self.manual_references = {}
        self.tracking_active = False
        self.tracking_pending_frame = None
        self.last_analysis_time = 0
        self.last_full_analysis_time = 0
        self.live_average = SteadyFrameAverage()
        self.analysis_mode = "full"
        self.averaged_frames = 1
        self.guide_offset = (0, 0)
        self.tracking_held = ()
        self.alignment = None
        self.radius_editing = False
        self.radius_edit_was_frozen = False
        self.picking_role = None
        self.pick_points = []
        self.analysis_generation = 0
        self.analysis_busy = False
        self.analysis_thread = None
        self.analysis_events = Queue()
        self.sidebar = ttk.Frame(self.root)
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=4, pady=5)
        self.profile_label = tk.Label(self.sidebar, text=self.profile.summary,
                                      wraplength=330, justify="left", anchor="w")
        self.profile_label.pack(fill="x")
        if self.options_error:
            self.profile_label.config(text="Saved options could not be loaded. Open setup to review them.")
        ttk.Button(self.sidebar, text="Telescope setup / Options", command=self.show_options).pack(fill="x", pady=3)
        self.overlays_visible = tk.BooleanVar(value=True)
        self.blink_active = False
        self.fov_crosshair_visible = tk.BooleanVar(value=True)
        self.fov_center_fraction = (0.5, 0.5)
        view_toolbar = ttk.Frame(self.sidebar)
        view_toolbar.pack(fill="x", pady=2)
        self.view_reset_button = ttk.Button(view_toolbar, text="Reset view", command=self.reset_view)
        self.view_reset_button.pack(side="left", padx=(0, 8))
        tk.Checkbutton(view_toolbar, text="Show overlays", variable=self.overlays_visible,
                       command=lambda: self.end_pan()).pack(side="left")
        self.fullscreen_button = ttk.Button(view_toolbar, text="Fullscreen", width=10,
                                             command=self.toggle_fullscreen)
        self.fullscreen_button.pack(side="right")
        fov_toolbar = ttk.Frame(self.sidebar)
        fov_toolbar.pack(fill="x")
        self.fov_checkbox = tk.Checkbutton(fov_toolbar, text="FOV crosshair",
                                            variable=self.fov_crosshair_visible, command=self.end_pan)
        self.fov_checkbox.pack(side="left")
        self.fov_center_button = ttk.Button(fov_toolbar, text="Center FOV", width=10,
                                              command=self.reset_fov_crosshair)
        self.fov_center_button.pack(side="left", padx=4)
        ttk.Label(fov_toolbar, text="Drag its center").pack(side="left")
        self.loading_label = tk.Label(self.sidebar, text="", wraplength=330, justify="left", anchor="w")
        self.loading_label.pack(fill="x", pady=3)
        # Draw our tabs with the portable clam element; retain the native theme
        # for all other controls (including Windows camera widgets).
        style = ttk.Style(self.root)
        if "Collimator.tab" not in style.element_names():
            style.element_create("Collimator.tab", "from", "clam", "tab")
        style.layout("Collimator.TNotebook.Tab", [
            ("Collimator.tab", {"sticky": "nswe", "children": [
                ("Notebook.padding", {"side": "top", "sticky": "nswe", "children": [
                    ("Notebook.focus", {"side": "top", "sticky": "nswe", "children": [
                        ("Notebook.label", {"side": "top", "sticky": ""})]})]})]})])
        self.tab_font = tkfont.nametofont("TkDefaultFont").copy()
        self.tab_font.configure(weight="bold")
        style.configure("Collimator.TNotebook.Tab", font=self.tab_font,
                        padding=(10, 2), borderwidth=1)
        style.map("Collimator.TNotebook.Tab",
                  background=[("selected", "#ffffff"), ("active", "#eaf0f8"), ("!selected", "#dbe2ec")],
                  foreground=[("selected", "#174a85"), ("!selected", "#303b4b")])
        self.notebook = ttk.Notebook(self.sidebar, style="Collimator.TNotebook")
        self.notebook.pack(fill="both", expand=True)
        self.review_panel = ttk.Frame(self.notebook, padding=(5, 2))
        self.manual_panel = ttk.Frame(self.notebook)
        self.camera_panel = ttk.Frame(self.notebook)
        self.notebook.add(self.review_panel, text="Detect & review")
        self.notebook.add(self.manual_panel, text="Manual guides")
        self.notebook.add(self.camera_panel, text="Camera")
        actions = ttk.Frame(self.review_panel)
        actions.pack(fill="x")
        for label, callback in (("Open image", self.open_image), ("Live camera", self.resume_live),
                                ("Save capture", self.save_capture)):
            ttk.Button(actions, text=label, command=callback, width=12).pack(side="left", padx=1)
        self.detect_button = ttk.Button(self.review_panel, text="Detect edges / restart tracking",
                                        command=self.start_detection, state="disabled")
        self.detect_button.pack(fill="x", pady=(4, 2))
        self.track_live = tk.BooleanVar(value=True)
        self.tracking_checkbox = tk.Checkbutton(self.review_panel, text="Track live edges",
                                                variable=self.track_live, command=self.tracking_changed)
        self.tracking_checkbox.pack(anchor="w")
        self.review_status = tk.StringVar(value=self.options_error or
            "Center the camera in the focuser. Show the focuser rim, actual secondary edge, "
            "and full primary reflection. Use even illumination, then detect.")
        self.advice_label = tk.Label(self.review_panel, textvariable=self.review_status,
                                     wraplength=330, justify="left", anchor="nw", height=4)
        self.advice_label.pack(fill="x", pady=2)
        ttk.Label(self.review_panel, text="Click a circle; add missing ones manually").pack(anchor="w", pady=(2, 2))
        self.role_row = ttk.Frame(self.review_panel)
        self.role_row.pack(fill="x")
        self.review_role = tk.StringVar(value=FEATURE_NAMES[0])
        self.role_buttons = {}
        self.role_colors = {role: "#{:02x}{:02x}{:02x}".format(*color)
                            for role, color in zip(FEATURE_NAMES, FEATURE_COLORS)}
        self.role_styles = {}
        self.role_swatches = {}
        style = ttk.Style(self.root)
        # Darker versions of guide hues remain readable on native light buttons.
        text_colors = ("#996000", "#006d83", "#146f32", "#804094", "#a52a2a")
        for index, (role, label) in enumerate(zip(FEATURE_NAMES, ("Focuser", "Secondary", "Primary", "Mark", "Pupil"))):
            style_name = f"Optical{index}.TButton"
            style.configure(style_name, foreground=text_colors[index])
            style.map(style_name, foreground=[("pressed", text_colors[index]), ("active", text_colors[index])])
            style.configure(f"Optical{index}.TEntry", foreground=text_colors[index])
            self.role_styles[role] = style_name
            cell = ttk.Frame(self.role_row)
            cell.grid(row=index // 3, column=index % 3, sticky="ew", padx=1, pady=1)
            swatch = tk.Frame(cell, background=self.role_colors[role], width=7)
            swatch.pack(side="left", fill="y", padx=(0, 2))
            self.role_swatches[role] = swatch
            button = ttk.Button(cell, text=label, style=style_name, cursor="hand2",
                                command=lambda name=role: self.select_review_role(name))
            button.pack(side="left", fill="x", expand=True)
            self.role_buttons[role] = button
        for column in (0, 1, 2):
            self.role_row.columnconfigure(column, weight=1)
        self.alternatives_open = False
        self.edit_row = ttk.Frame(self.review_panel)
        self.edit_row.pack(fill="x", pady=2)
        self.alternative_button = ttk.Button(self.edit_row, text="Change outline", command=self.toggle_alternatives)
        self.alternative_button.pack(side="left", fill="x", expand=True)
        self.shrink_button = ttk.Button(self.edit_row, text="−", width=3,
                                       command=lambda: self.resize_review_circle(-1))
        self.shrink_button.pack(side="left", padx=(3, 0))
        ttk.Label(self.edit_row, text="Radius (px)").pack(side="left", padx=(3, 0))
        self.radius_text = tk.StringVar(value="")
        self.radius_entry = ttk.Entry(self.edit_row, textvariable=self.radius_text, width=5)
        self.radius_entry.pack(side="left", padx=2)
        self.radius_entry.bind("<FocusIn>", self.begin_radius_edit)
        self.radius_entry.bind("<FocusOut>", self.leave_radius_edit)
        self.radius_entry.bind("<Return>", self.commit_review_radius)
        self.radius_entry.bind("<Escape>", self.cancel_radius_edit)
        self.grow_button = ttk.Button(self.edit_row, text="+", width=3,
                                     command=lambda: self.resize_review_circle(1))
        self.grow_button.pack(side="left")
        for widget in (self.shrink_button, self.radius_entry, self.grow_button):
            bind_wheel(widget, lambda event: self.resize_review_circle(wheel_direction(event)) if wheel_direction(event) else "break")
        self.alternative_panel = ttk.Frame(self.review_panel)
        self.candidate_choice = tk.StringVar(value="Not identified")
        ttk.Button(self.alternative_panel, text="‹", width=3, command=lambda: self.cycle_candidate(-1)).pack(side="left")
        ttk.Label(self.alternative_panel, textvariable=self.candidate_choice, anchor="center").pack(side="left", fill="x", expand=True)
        ttk.Button(self.alternative_panel, text="›", width=3, command=lambda: self.cycle_candidate(1)).pack(side="right")
        self.candidate_labels = {}
        self.selection_status = tk.StringVar(value="No image analyzed yet.")
        self.selection_label = tk.Label(self.review_panel, textvariable=self.selection_status,
                                        wraplength=330, justify="left", anchor="nw", height=3)
        self.selection_label.pack(fill="x", pady=2)
        self.pick_button = ttk.Button(self.review_panel, text="Pick edge: 3 points on image",
                                      command=self.begin_manual_pick)
        self.pick_button.pack(fill="x", pady=2)
        row = ttk.Frame(self.review_panel)
        row.pack(fill="x", pady=2)
        ttk.Button(row, text="Clear reference", command=self.clear_reference).pack(side="left", expand=True, fill="x")
        ttk.Button(row, text="Cancel pick", command=self.cancel_pick).pack(side="left", expand=True, fill="x")
        # Raw hypotheses remain internal; normal overlays are one per named role.
        self.show_candidates = tk.BooleanVar(value=False)
        self.review_progress = tk.StringVar(value="0 / 4 required circles present")
        tk.Label(self.review_panel, textvariable=self.review_progress, anchor="w").pack(fill="x", pady=4)
        self.reference_summary = tk.StringVar()
        self.summary_label = tk.Label(self.review_panel, textvariable=self.reference_summary,
                                      wraplength=330, justify="left", anchor="w")
        self.summary_label.pack(fill="x", pady=2)
        self.next_step = tk.StringVar(value="Detect edges; missing circles can be added manually.")
        self.next_step_label = tk.Label(self.review_panel, textvariable=self.next_step,
                                        wraplength=330, justify="left", anchor="w")
        self.next_step_label.pack(fill="x", pady=2)
        self.measurement_text = tk.StringVar()
        self.measurement_label = tk.Label(self.review_panel, textvariable=self.measurement_text,
                                          wraplength=330, justify="left", anchor="w")
        self.measurement_label.pack(fill="x")
        tk.Label(self.review_panel, text="Drag circles: move all · Elsewhere: pan\n"
                 "Wheel: zoom · Ctrl: size · Right: blink",
                 wraplength=330, justify="left", anchor="w").pack(fill="x", pady=2)

    def close_alternatives(self):
        self.alternatives_open = False
        self.alternative_panel.pack_forget()
        self.alternative_button.config(text="Change outline")

    def toggle_alternatives(self):
        self.cancel_pick()
        if self.alternatives_open:
            self.close_alternatives()
        else:
            self.alternatives_open = True
            self.alternative_panel.pack(after=self.edit_row, fill="x")
            self.alternative_button.config(text="Done choosing")
            self.review_status.set("Choose a replacement for this element. Tracking will keep it if no good replacement is found.")

    def refresh_guidance(self):
        states = {role: "missing" if role not in self.selections else
                  "manual" if role in self.tracking_held or role in self.manual_references else "detected"
                  for role in FEATURE_NAMES}
        if "Center mark" not in self.selections and self.profile.center_mark_shape in ("None", "Unknown"):
            states["Center mark"] = "absent" if self.profile.center_mark_shape == "None" else "optional"
        self.reference_summary.set(f"Focuser: {states['Focuser edge']} · Secondary: {states['Secondary edge']}\n"
                                   f"Primary: {states['Primary reflection']} · Pupil: {states['Camera pupil']} · Mark: {states['Center mark']}")
        self.alignment = alignment_advice(self.detection, self.selections, self.profile)
        paused = self.source_mode == "camera" and self.camera_on and not self.tracking_active and self.detection is not None
        self.next_step.set("Tracking off: live image continues; circles hold the last measurements. Enable tracking or Detect to update."
                           if paused else self.alignment.instruction)
        center = self.detection.guide_center if self.detection else None
        self.measurement_text.set(f"Shared guide center: {center[0]:.1f}, {center[1]:.1f} px."
                                  if center is not None else "")

    def tracking_changed(self):
        self.live_average.reset()
        if not self.track_live.get():
            self.analysis_generation += 1
            self.tracking_active = False
            self.tracking_pending_frame = None
            self.view_frozen = (self.source_mode == "image" or self.picking_role is not None
                                or self.radius_editing or self.pan_anchor is not None)
        elif self.source_mode == "camera" and self.camera_on and self.last_frame is not None:
            self.tracking_active = True
            self.view_frozen = self.picking_role is not None or self.radius_editing
            self.tracking_pending_frame = self.last_frame.copy()
            self.maybe_track()
        self.refresh_review_selection()

    def maybe_track(self):
        if (not self.tracking_active or not self.track_live.get() or self.analysis_busy or self.closing
                or self.view_frozen or self.radius_editing or self.picking_role is not None or self.pan_anchor is not None
                or self.tracking_pending_frame is None
                or monotonic() - self.last_analysis_time < (.1 if can_track_locally(self.detection, self.selections) else .35)):
            return
        frame = self.tracking_pending_frame
        self.tracking_pending_frame = None
        self.analysis_generation += 1
        self._submit_analysis(frame, tracking=True)

    def show_options(self):
        if self.setup_dialog is not None and self.setup_dialog.winfo_exists():
            self.setup_dialog.lift()
            return
        if self.options_error:
            messagebox.showinfo("Options could not be loaded",
                f"{self.options_error}\n\nThe existing file has been kept. Saving setup will replace it.",
                parent=self.root)
        self.setup_dialog = SetupDialog(self.root, self.profile, self.options_store, self.profile_saved)

    def profile_saved(self, profile):
        self.profile = profile
        self.options_error = None
        self.profile_label.config(text=profile.summary)
        self.invalidate_review()
        self.review_status.set("Telescope setup saved. Detect again using the new setup.")

    def invalidate_review(self):
        self.finish_radius_edit()
        self.end_pan()
        self.close_alternatives()
        self.analysis_generation += 1
        self.detection = None
        self.observations_current = False
        self.selections = {}
        self.confirmed = set()
        self.manual_points = {}
        self.manual_adjustments = {}
        self.manual_references = {}
        self.tracking_active = False
        self.tracking_pending_frame = None
        self.live_average.reset()
        self.last_full_analysis_time = 0
        self.analysis_mode = "full"
        self.averaged_frames = 1
        self.guide_offset = (0, 0)
        self.tracking_held = ()
        self.picking_role = None
        self.pick_points = []
        self.view_frozen = False
        self.reset_manual_guides()
        self.refresh_review_selection()
        self.review_status.set("Open an image or use the live camera, then detect edges.")

    def freeze_for_review(self):
        if not self.view_frozen:
            self.last_frame = self.last_frame.copy()
            self.view_frozen = True

    def start_detection(self):
        self.live_average.reset()
        self.finish_radius_edit()
        if self.last_frame is None or self.analysis_busy or self.closing:
            return
        self.end_pan()
        self.close_alternatives()
        self.review_role.set(FEATURE_NAMES[0])
        self.overlays_visible.set(True)
        self.freeze_for_review()
        self.detection = None
        self.selections = {}
        if not self.manual_guides_active:
            self.reset_manual_guides()
        self.confirmed = set()
        self.manual_points = {}
        self.manual_adjustments = {}
        self.cancel_pick()
        self.refresh_review_selection()
        self.manual_references = {}
        self.guide_offset = (0, 0)
        self.tracking_held = ()
        self.tracking_active = self.source_mode == "camera" and self.camera_on and self.track_live.get()
        self.view_frozen = not self.tracking_active
        self.analysis_generation += 1
        self.review_status.set("Detecting edges locally…")
        self._submit_analysis(self.last_frame.copy(), tracking=False)

    def _submit_analysis(self, frame, tracking):
        if self.analysis_busy:
            return
        token = (self.session, self.analysis_generation)
        frame, shape = frame.copy(), self.profile.center_mark_shape
        frames = self.live_average.snapshot(monotonic()) if tracking else ()
        frames = frames or (frame,)
        previous, selections = self.detection, dict(self.selections)
        missing = any(role not in selections for role in required_features(shape)) or bool(self.tracking_held)
        force_full = not tracking or monotonic() - self.last_full_analysis_time >= (1.5 if missing else 3)
        full_detector = analyze_frame
        self.analysis_busy = True
        self.last_analysis_time = monotonic()
        self.detect_button.config(state="disabled")
        analysis_events = self.analysis_events

        def analyze():
            try:
                packet = detect_live(frames, previous, selections, shape, full_detector, force_full)
                analysis_events.put((*token, packet.result, None, packet.frame, tracking, packet.mode, packet.averaged_frames))
            except Exception as error:
                analysis_events.put((*token, None, str(error), frame, tracking, "full", 1))

        self.analysis_thread = Thread(target=analyze, daemon=True, name="Optical-edge-analysis")
        self.analysis_thread.start()

    def poll_analysis(self):
        while True:
            try:
                session, generation, result, error, frame, tracking, mode, count = self.analysis_events.get_nowait()
            except Empty:
                break
            self.analysis_busy = False
            if (session, generation) != (self.session, self.analysis_generation):
                continue
            if error:
                self.review_status.set(f"Analysis failed: {error}. Pick edges manually or try a new image.")
                continue
            self.analysis_mode, self.averaged_frames = mode, count
            if mode == "full":
                self.last_full_analysis_time = monotonic()
            if tracking:
                update = merge_tracking(self.detection, result, self.manual_references, self.guide_offset)
                self.detection, self.selections = update.result, update.selections
                self.manual_references, self.tracking_held = update.manual_references, update.held
                self.manual_points = {}
                self.manual_adjustments = {}
            else:
                self.detection = concentric_guides(result)
                self.selections = dict(result.suggested)
            self.last_frame = frame  # Live tracking pairs measurements and visible frames.
            self.observations_current = True
            if self.source_mode == "camera" and self.camera_on and not self.radius_editing and self.picking_role is None and self.pan_anchor is None:
                self.view_frozen = False
            self.confirmed.clear()
            self.review_status.set(self.capture_advice(self.detection))
            self.refresh_review_selection()

    @staticmethod
    def capture_advice(result):
        """Give the next capture action first; retain detailed messages in exports."""
        if not result.candidates:
            return result.messages[0]
        advice = [f"Detected {len(result.suggested)} circles."]
        if any((edge.edge_width or 0) >= SOFT_EDGE_WIDTH for edge in result.candidates):
            advice.append("Improve camera focus; keep camera steady.")
        focuser = result.candidate(result.suggested.get("Focuser edge"))
        if focuser is None or focuser.clipped:
            advice.append("Focuser missing/cropped: reduce camera zoom or use a wider-view camera.")
        elif "Secondary edge" not in result.suggested:
            advice.append("Secondary unclear: improve lighting or pick its actual outer edge.")
        return "\n".join(advice)

    def refresh_review_selection(self):
        role = self.review_role.get()
        for name, button in self.role_buttons.items():
            button.state(["pressed"] if name == role else ["!pressed"])
        self.candidate_labels = {"Not identified": None}
        if self.detection is not None:
            for candidate in self.detection.candidates:
                primary = self.detection.candidate(self.selections.get("Primary reflection"))
                if not accepts_reference(role, candidate, primary):
                    continue
                detail = f"radius {candidate.radius:.0f} px"
                partial = " · partial" if candidate.clipped or candidate.coverage is not None and candidate.coverage < 0.85 else ""
                label = f"Outline {candidate.id} · {detail}{partial}"
                self.candidate_labels[label] = candidate.id
        selected = self.selections.get(role)
        self.candidate_choice.set(next((label for label, candidate_id in self.candidate_labels.items()
                                       if candidate_id == selected), "Not identified"))
        candidate = self.detection.candidate(selected) if self.detection else None
        hints = {"Focuser edge": "Orange: inside focuser rim.",
                 "Secondary edge": "Cyan: actual secondary face, not its dark reflection.",
                 "Primary reflection": "Green: primary reflection rim; clips may interrupt it.",
                 "Center mark": "Purple: optional primary center mark.",
                 "Camera pupil": "Red: reflected lens opening, not the whole secondary shadow."}
        for button in (self.shrink_button, self.grow_button):
            button.config(style=self.role_styles[role], state="normal" if candidate else "disabled")
        self.radius_entry.config(style=f"Optical{FEATURE_NAMES.index(role)}.TEntry",
                                 state="normal" if candidate else "disabled")
        if not self.radius_editing:
            self.radius_text.set(f"{candidate.radius:.0f}" if candidate else "")
        if candidate:
            action = "Click/drag to edit; missing circles can be added manually."
            self.selection_status.set(hints[role] + " " + action)
        else:
            self.selection_status.set(hints[role] + " Not identified; pick it or change outline.")
        self.pick_button.config(text="Pick center: 1 point on image" if role == "Center mark"
                                else "Pick edge: 3 points on image")
        required = required_features(self.profile.center_mark_shape)
        count = sum(role in self.selections and self.detection.candidate(self.selections[role]) is not None
                    for role in required) if self.detection else 0
        self.review_progress.set(f"{count} / {len(required)} required circles present" + (" · tracking" if self.tracking_active else " · tracking off" if self.source_mode == "camera" and self.camera_on else ""))
        self.refresh_guidance()

    def select_review_role(self, role):
        self.review_role.set(role)
        self.review_role_changed()

    def cycle_candidate(self, direction):
        labels = [label for label, candidate_id in self.candidate_labels.items() if candidate_id is not None]
        if not labels:
            return
        current = self.candidate_choice.get()
        index = labels.index(current) if current in labels else (-1 if direction > 0 else 0)
        self.candidate_choice.set(labels[(index + direction) % len(labels)])
        self.choose_candidate()

    def review_role_changed(self, event=None):
        self.finish_radius_edit(restore=True)
        self.close_alternatives()
        self.cancel_pick()
        self.refresh_review_selection()

    def choose_candidate(self):
        self.cancel_pick()
        self.analysis_generation += 1
        role = self.review_role.get()
        candidate_id = self.candidate_labels.get(self.candidate_choice.get())
        self.confirmed.discard(role)
        if candidate_id is None:
            self.selections.pop(role, None)
            self.manual_references.pop(role, None)
        else:
            # One geometric candidate cannot be two different optical references.
            for other in tuple(self.selections):
                if other != role and self.selections[other] == candidate_id:
                    self.selections.pop(other)
                    self.manual_references.pop(other, None)
                    self.confirmed.discard(other)
            self.selections[role] = candidate_id
            reference = next((edge for edge in self.detection.observations if edge.id == candidate_id),
                             self.detection.candidate(candidate_id))
            if role == "Camera pupil" and not reference.kind.startswith("pupil_"):
                reference = replace(reference, kind="pupil_manual")
                self.detection = replace(self.detection,
                    candidates=tuple(replace(edge, kind="pupil_manual") if edge.id == candidate_id else edge for edge in self.detection.candidates),
                    observations=tuple(reference if edge.id == candidate_id else edge for edge in self.detection.observations))
            self.manual_references[role] = reference
        self.reanchor_review_guides()
        self.refresh_review_selection()

    def reanchor_review_guides(self):
        if self.detection is None:
            return
        observations = {edge.id: edge for edge in self.detection.observations}
        selected = [observations.get(value, self.detection.candidate(value)) for value in self.selections.values()]
        boundaries = [edge for edge in selected if edge is not None and edge.kind == "boundary"]
        focuser_id = self.selections.get("Focuser edge")
        anchor = observations.get(focuser_id, self.detection.candidate(focuser_id))
        anchor = anchor or max(boundaries, key=lambda edge: edge.radius, default=None)
        if anchor is not None:
            self.detection = concentric_guides(self.detection,
                tuple(anchor.center[i] + self.guide_offset[i] for i in (0, 1)))
            self.detection = replace(self.detection, guide_master_id=anchor.id)

    def begin_radius_edit(self, event=None):
        if self.detection is None or self.radius_editing:
            return
        self.radius_editing = True
        self.live_average.reset()
        self.radius_edit_was_frozen = self.view_frozen
        self.view_frozen = True
        self.analysis_generation += 1

    def finish_radius_edit(self, restore=False):
        if self.radius_editing:
            self.radius_editing = False
            self.view_frozen = self.radius_edit_was_frozen or self.picking_role is not None
        if restore and hasattr(self, "radius_entry"):
            edge = self.detection.candidate(self.selections.get(self.review_role.get())) if self.detection else None
            self.radius_text.set(f"{edge.radius:.0f}" if edge else "")
        return "break"

    def cancel_radius_edit(self, event=None):
        self.finish_radius_edit(restore=True)
        self.video_label.focus_set()
        return "break"

    def commit_review_radius(self, event=None):
        try:
            self.set_review_radius(int(self.radius_text.get().strip()))
        except ValueError:
            self.review_status.set("Radius (px): enter a valid positive whole-pixel value within the image size limit.")
            return "break"
        self.finish_radius_edit()
        self.video_label.focus_set()
        return "break"

    def leave_radius_edit(self, event=None):
        if not self.radius_editing:
            return
        try:
            self.set_review_radius(int(self.radius_text.get().strip()))
        except ValueError:
            self.review_status.set("Radius unchanged: enter a valid whole-pixel radius.")
        self.finish_radius_edit(restore=True)

    def resize_review_circle(self, direction):
        edge = self.detection.candidate(self.selections.get(self.review_role.get())) if self.detection else None
        if edge is None or not direction:
            return "break"
        minimum = 1 if self.review_role.get() == "Center mark" else 2
        radius = max(minimum, min(max(self.detection.image_size) * 2, round(edge.radius) + int(direction)))
        self.set_review_radius(radius)
        self.radius_text.set(str(radius))
        return "break"

    def set_review_radius(self, radius):
        """Set a whole raw-image radius without changing the shared center."""
        role = self.review_role.get()
        edge = self.detection.candidate(self.selections.get(role)) if self.detection else None
        if edge is None:
            return
        size = self.detection.image_size
        minimum = 1 if role == "Center mark" else 2
        if type(radius) is not int or not minimum <= radius <= max(size) * 2:
            raise ValueError(f"Radius (px): enter a whole number from {minimum} to {max(size) * 2}.")
        if radius == edge.radius:
            return
        self.analysis_generation += 1
        original = next((item for item in self.detection.observations if item.id == edge.id), edge)
        reference = replace(original, axes=(radius, radius), angle_deg=0, provenance="manual_resize",
                            fit_quality=None, residual=None, coverage=None, edge_width=None, support_bins=(),
                            clipped=original.center[0] - radius < 0 or original.center[1] - radius < 0
                            or original.center[0] + radius >= size[0] or original.center[1] + radius >= size[1])
        self.manual_references[role] = reference
        self.tracking_held = tuple(name for name in self.tracking_held if name != role)
        adjusted = replace(edge, axes=(radius, radius), angle_deg=0, provenance="manual_resize",
                           clipped=edge.center[0] - radius < 0 or edge.center[1] - radius < 0
                           or edge.center[0] + radius >= size[0] or edge.center[1] + radius >= size[1])
        candidates = tuple(adjusted if item.id == edge.id else item for item in self.detection.candidates)
        observations = tuple(reference if item.id == edge.id else item for item in self.detection.observations)
        if not any(item.id == edge.id for item in observations):
            observations += (reference,)
        self.detection = replace(self.detection, candidates=candidates, observations=observations)
        self.review_status.set(f"{role}: radius {radius:.0f} px. Other circles keep their sizes and shared center.")
        self.refresh_review_selection()
        return "break"

    def set_review_center(self, center):
        """Move the entire circular guide group; never change original observations."""
        if self.detection is None:
            return
        before = self.detection
        shifted = concentric_guides(before, center)
        candidates = []
        for old, guide in zip(before.candidates, shifted.candidates):
            record = self.manual_adjustments.setdefault(old.id, {"original": asdict(old)})
            record["constraint"] = "shared_circular_guides"
            record["translation"] = [guide.center[i] - record["original"]["center"][i] for i in (0, 1)]
            shift = (guide.center[0] - old.center[0], guide.center[1] - old.center[1])
            if old.id in self.manual_points:
                self.manual_points[old.id] = [(x + shift[0], y + shift[1]) for x, y in self.manual_points[old.id]]
            candidates.append(replace(guide, provenance="manual_drag"))
        self.detection = replace(shifted, candidates=tuple(candidates), suggested={})
        self.guide_offset = tuple(self.guide_offset[i] + shifted.guide_center[i] - before.guide_center[i]
                                  for i in (0, 1)) if before.guide_center is not None else (0, 0)
        self.confirmed.clear()

    def move_review_candidate(self, original, delta, original_points):
        if self.detection is None or self.detection.candidate(original.id) is None:
            return
        self.set_review_center((original.center[0] + delta[0], original.center[1] + delta[1]))
        self.review_status.set("All circles moved together. Check the shared center, or Detect for a fresh best guess.")
        self.refresh_review_selection()

    def clear_reference(self):
        self.cancel_pick()
        role = self.review_role.get()
        self.selections.pop(role, None)
        self.confirmed.discard(role)
        self.manual_references.pop(role, None)
        self.reanchor_review_guides()
        self.refresh_review_selection()

    def cancel_pick(self):
        self.picking_role = None
        self.pick_points = []
        if self.source_mode == "camera" and self.camera_on and not self.radius_editing:
            self.view_frozen = False

    def begin_manual_pick(self):
        self.live_average.reset()
        self.finish_radius_edit(restore=True)
        if self.last_frame is None:
            self.review_status.set("Open an image or connect a camera first.")
            return
        self.freeze_for_review()
        # Invalidate in-flight analysis while keeping existing circles.
        self.analysis_generation += 1
        self.picking_role = self.review_role.get()
        self.pick_points = []
        instruction = ("Click the center of the actual primary center mark." if self.picking_role == "Center mark"
                       else "Click three well-spaced points around its visible edge. This correction fits a circle.")
        self.review_status.set(f"{self.picking_role}: {instruction}")

    def pick_review_point(self, point):
        self.pick_points.append(point)
        required = 1 if self.picking_role == "Center mark" else 3
        if len(self.pick_points) < required:
            self.review_status.set(f"{self.picking_role}: {len(self.pick_points)} / {required} points picked.")
            return
        size = (self.last_frame.shape[1], self.last_frame.shape[0])
        result = self.detection or DetectionResult(size, (), {}, (), 0)
        candidate_id = max((edge.id for edge in result.candidates), default=0) + 1
        try:
            if required == 1:
                edge = EdgeCandidate(candidate_id, tuple(point), (4, 4), 0,
                                     kind="mark_point", provenance="manual_point")
            else:
                edge = circle_from_points(self.pick_points, candidate_id, size)
                if self.picking_role == "Camera pupil":
                    edge = replace(edge, kind="pupil_manual")
        except ValueError as error:
            self.pick_points = []
            self.review_status.set(str(error))
            return
        role = self.picking_role
        self.manual_points[candidate_id] = list(self.pick_points)
        self.detection = replace(result, candidates=result.candidates + (edge,),
                                 observations=(result.observations or result.candidates) + (edge,))
        self.manual_references[role] = edge
        self.selections[role] = candidate_id
        # Adding a secondary/mark does not replace the focuser master center.
        if role == "Focuser edge" or result.guide_center is None:
            self.detection = concentric_guides(self.detection, edge.center)
            self.detection = replace(self.detection, guide_master_id=edge.id)
            self.guide_offset = (0, 0)
        elif "Focuser edge" not in self.selections and edge.radius > max((item.radius for item in result.candidates), default=0):
            self.detection = concentric_guides(self.detection, edge.center)
            self.detection = replace(self.detection, guide_master_id=edge.id)
        else:
            self.detection = concentric_guides(self.detection)
        self.cancel_pick()
        self.review_status.set(f"{role} picked. All circles keep the master center; tracking retains this circle when detection is uncertain.")
        self.refresh_review_selection()

    def open_image(self):
        path = filedialog.askopenfilename(parent=self.root, title="Open focuser-view image",
            filetypes=(("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"), ("All files", "*.*")))
        if path:
            try:
                self.load_image(path)
            except (OSError, ValueError, cv2.error) as error:
                messagebox.showerror("Could not open image", str(error), parent=self.root)

    def load_image(self, path):
        frame = cv2.imdecode(np.frombuffer(Path(path).read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None or min(frame.shape[:2]) < 32:
            raise ValueError("Choose a readable image at least 32 pixels wide and high.")
        self.session += 1
        self.worker.commands.put((self.session, "close", None))
        self.enable_camera_controls(False)
        self.invalidate_review()
        self.source_mode = "image"
        self.source_description = str(Path(path).resolve())
        self.last_frame = frame
        self.view_frozen = True
        self.reset_fov_crosshair()
        self.reset_view()
        self.display_transform = None
        self.reset_crosshair()
        self.refresh_button.config(state="normal")
        self.camera_dropdown.config(state="readonly" if self.camera_list else "disabled")
        self.loading_label.config(text=f"Image: {Path(path).name}")

    def resume_live(self):
        self.source_description = "Live camera"
        if self.selected_camera.get() in self.camera_list:
            self.on_camera_selected(None)
        else:
            self.refresh_cameras()

    def save_capture(self):
        if self.last_frame is None:
            self.review_status.set("There is no image to save yet.")
            return
        path = filedialog.asksaveasfilename(parent=self.root, title="Save raw image and review metadata",
            defaultextension=".png", filetypes=(("PNG image", "*.png"),))
        if path:
            try:
                self.export_capture(path)
                self.review_status.set("Raw image and review metadata saved. The image contains no overlays.")
            except (OSError, ValueError, cv2.error) as error:
                messagebox.showerror("Could not save capture", str(error), parent=self.root)

    def export_capture(self, path):
        if self.last_frame is None:
            raise ValueError("There is no image to save.")
        path = Path(path).with_suffix(".png")
        frame = self.last_frame.copy()
        success, encoded = cv2.imencode(".png", frame)
        if not success:
            raise ValueError("Could not encode the raw image.")
        metadata = {"schema_version": 1, "source": self.source_description,
                    "image_size": [frame.shape[1], frame.shape[0]],
                    "telescope": asdict(self.profile),
                    "detection": self.detection.to_dict() if self.detection else None,
                    "observations_match_image": self.observations_current,
                    "analysis": {"mode": self.analysis_mode, "averaged_frames": self.averaged_frames},
                    "fov_crosshair": {"visible": self.fov_crosshair_visible.get(),
                                     "center_fraction": list(self.fov_center_fraction),
                                     "center_px": list(self.fov_crosshair_center())},
                    "selections": self.selections,
                    "manual_points": self.manual_points,
                    "manual_adjustments": self.manual_adjustments,
                    "manual_references": {role: asdict(edge) for role, edge in self.manual_references.items()},
                    "tracking": {"active": self.tracking_active, "held_manual": list(self.tracking_held), "center_offset": list(self.guide_offset)},
                    "alignment_advice": self.alignment.to_dict() if self.alignment and (self.source_mode != "camera" or self.observations_current) else None,
                    "interpretation": "Concentric circular guides are a best guess, not independent alignment measurements. Original observations drive provisional next-action advice; primary axial alignment is not certified."}
        # Encode metadata before writing either file; preserve original-resolution pixels.
        payload = json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        path.write_bytes(encoded.tobytes())
        try:
            path.with_suffix(".json").write_text(payload, encoding="utf-8", newline="\n")
        except OSError as error:
            raise OSError(f"Image saved at {path}, but metadata could not be saved: {error}") from error
        return path
