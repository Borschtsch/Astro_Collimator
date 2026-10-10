"""Portable drag-to-adjust angle entry without spinbox arrows."""
from tkinter import ttk


class AngleControl(ttk.Entry):
    def __init__(self, parent, variable, apply):
        super().__init__(parent, textvariable=variable, width=7, cursor="sb_h_double_arrow")
        self.variable = variable
        self.apply = apply
        self.anchor = None
        self.dragged = False
        self.bind("<ButtonPress-1>", self.begin_drag)
        self.bind("<B1-Motion>", self.drag)
        self.bind("<ButtonRelease-1>", self.end_drag)
        self.bind("<Return>", lambda event: self.apply_if_enabled())
        self.bind("<FocusOut>", lambda event: self.apply_if_enabled())

    def apply_if_enabled(self):
        if not self.instate(["disabled"]):
            return self.apply()
        return "break"

    def begin_drag(self, event):
        if self.instate(["disabled"]):
            return "break"
        self.apply()
        self.anchor = (event.x_root, float(self.variable.get()))
        self.dragged = False

    def drag(self, event):
        if self.anchor is None or self.instate(["disabled"]):
            return "break"
        distance = event.x_root - self.anchor[0]
        if not self.dragged and abs(distance) < 2:
            return "break"
        self.dragged = True
        step = .01 if event.state & 0x0001 else .1
        self.variable.set(f"{self.anchor[1] + distance * step:.2f}")
        self.apply()
        self.anchor = (event.x_root, float(self.variable.get()))
        return "break"

    def end_drag(self, event):
        self.anchor = None
        if self.dragged:
            self.selection_clear()
            return "break"
