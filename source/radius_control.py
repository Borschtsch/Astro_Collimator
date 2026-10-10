"""Whole-pixel radius entry with horizontal coarse/fine dragging."""
from tkinter import ttk


class RadiusControl(ttk.Entry):
    def __init__(self, parent, variable, prepare, resize, finish):
        super().__init__(parent, textvariable=variable, width=5, cursor="sb_h_double_arrow")
        self.prepare = prepare
        self.resize = resize
        self.finish = finish
        self.anchor = None
        self.dragged = False
        self.bind("<ButtonPress-1>", self.begin_drag)
        self.bind("<B1-Motion>", self.drag)
        self.bind("<ButtonRelease-1>", self.end_drag)

    def begin_drag(self, event):
        self.anchor = None
        self.dragged = False
        if self.instate(["disabled"]):
            return "break"
        value = self.prepare()
        if value is not None:
            self.anchor = (event.x_root, float(value))

    def drag(self, event):
        if self.anchor is None or self.instate(["disabled"]):
            return "break"
        distance = event.x_root - self.anchor[0]
        if not self.dragged and abs(distance) < 2:
            return "break"
        self.dragged = True
        value = self.anchor[1] + distance * (.1 if event.state & 1 else 1)
        actual = self.resize(round(value))
        if actual is None:
            self.anchor = None
            return "break"
        # Preserve fractional fine motion; discard overshoot at radius limits.
        self.anchor = (event.x_root, value if abs(value - actual) <= .5 else float(actual))
        return "break"

    def end_drag(self, event):
        self.anchor = None
        if self.dragged:
            self.dragged = False
            self.selection_clear()
            self.finish()
            return "break"
