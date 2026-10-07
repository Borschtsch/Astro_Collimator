"""Integrated local setup editor, separate from the optical-analysis engine."""

import tkinter as tk
from tkinter import ttk

from .app_options import CENTER_MARK_SHAPES, TelescopeProfile


PROFILE_FIELDS = (
    ("name", "Telescope model / name", False),
    ("aperture_mm", "Primary aperture (mm)", True),
    ("focal_length_mm", "Focal length (mm)", True),
    ("secondary_minor_axis_mm", "Secondary minor axis (mm)", True),
    ("focuser_inner_diameter_mm", "Focuser inside diameter (mm)", True),
    ("secondary_offset_mm", "Known secondary offset (mm)", True),
    ("camera_description", "Camera and lens", False),
    ("mounting_notes", "Camera mounting / orientation notes", False),
)


class SetupDialog(tk.Toplevel):
    def __init__(self, root, profile, store, on_saved):
        super().__init__(root)
        self.title("Newtonian setup / options")
        self.transient(root)
        self.resizable(False, False)
        self.store = store
        self.on_saved = on_saved
        self.variables = {}
        host = ttk.Frame(self, padding=12)
        host.grid()
        ttk.Label(host, text="Enter known dimensions; leave unknown values blank.").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        for row, (key, label, numeric) in enumerate(PROFILE_FIELDS, 1):
            value = getattr(profile, key)
            variable = tk.StringVar(value="" if value is None else f"{value:g}" if numeric else value)
            self.variables[key] = variable
            ttk.Label(host, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=3)
            entry = ttk.Entry(host, textvariable=variable, width=34)
            entry.grid(row=row, column=1, sticky="ew", pady=3)
            if row == 1:
                entry.focus_set()
        row = len(PROFILE_FIELDS) + 1
        self.mark_shape = tk.StringVar(value=profile.center_mark_shape)
        ttk.Label(host, text="Primary center mark (None if absent)").grid(row=row, column=0, sticky="w")
        ttk.Combobox(host, textvariable=self.mark_shape, values=CENTER_MARK_SHAPES,
                     state="readonly", width=31).grid(row=row, column=1)
        ttk.Label(host, text="All guides are circles with one shared center. Drag any guide to move the group.",
                  wraplength=480).grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=4)
        row += 1
        self.ratio = tk.StringVar()
        for key in ("aperture_mm", "focal_length_mm"):
            self.variables[key].trace_add("write", lambda *args: self.update_ratio())
        ttk.Label(host, textvariable=self.ratio).grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=6)
        self.update_ratio()
        self.error = tk.StringVar()
        ttk.Label(host, textvariable=self.error, foreground="#b22222", wraplength=440).grid(
            row=row + 2, column=0, columnspan=2, sticky="w")
        actions = ttk.Frame(host)
        actions.grid(row=row + 3, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(actions, text="Cancel", command=self.destroy).grid(row=0, column=0, padx=4)
        ttk.Button(actions, text="Save options", command=self.save).grid(row=0, column=1)
        self.bind("<Escape>", lambda event: self.destroy())
        self.grab_set()

    def update_ratio(self):
        try:
            aperture = float(self.variables["aperture_mm"].get())
            focal_length = float(self.variables["focal_length_mm"].get())
            text = f"Focal ratio: f/{focal_length / aperture:g}" if aperture > 0 and focal_length > 0 else ""
        except (ValueError, ZeroDivisionError):
            text = "Focal ratio: enter aperture and focal length."
        self.ratio.set(text)

    def save(self):
        try:
            values = {}
            for key, label, numeric in PROFILE_FIELDS:
                text = self.variables[key].get().strip()
                if numeric:
                    try:
                        values[key] = float(text) if text else None
                    except ValueError as error:
                        raise ValueError(f"{label}: enter a number or leave blank.") from error
                else:
                    values[key] = text
            profile = TelescopeProfile(**values, center_mark_shape=self.mark_shape.get()).validate()
            self.store.save(profile)
        except (ValueError, OSError) as error:
            self.error.set(str(error))
            return
        self.on_saved(profile)
        self.destroy()
