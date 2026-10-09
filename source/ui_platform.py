"""Tk window and input behavior shared by Windows and Linux desktops."""


def wheel_direction(event):
    # X11 Tk uses buttons 4/5; Windows (and some newer Tk builds) use delta.
    number = getattr(event, "num", None)
    if number in (8, 9):
        # Tk 9 maps symbolic buttons 4/5 to physical buttons 8/9 on
        # Windows/Aqua. X11 still uses 8/9 for different physical buttons.
        widget = getattr(event, "widget", None)
        if (widget is not None and widget.tk.call("tk", "windowingsystem") in ("win32", "aqua")
                and int(str(widget.tk.call("package", "provide", "Tk")).split(".")[0]) >= 9):
            number -= 4
    if number in (4, 5):
        return 1 if number == 4 else -1
    delta = getattr(event, "delta", 0)
    return (delta > 0) - (delta < 0)


def bind_wheel(widget, callback):
    from . import input_diagnostics as diagnostics
    diagnostics.initialize(widget)

    def dispatch(event, sequence):
        raw_delta = getattr(event, "delta", 0)
        axes = None
        if sequence == "<TouchpadScroll>":
            horizontal, vertical = widget.tk.call("::tk::PreciseScrollDeltas", raw_delta)
            axes = [int(horizontal), int(vertical)]
            event.delta = int(vertical)
            event.precise_scroll = True
        before = diagnostics.snapshot(callback)
        try:
            return callback(event)
        finally:
            diagnostics.record(event, callback, sequence, raw_delta, axes, before)

    for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        widget.bind(sequence, lambda event, seq=sequence: dispatch(event, seq))
    # Newer Tk uses a separate event for touchpads and fine-resolution mice.
    if widget.tk.call("info", "commands", "::tk::PreciseScrollDeltas"):
        widget.bind("<TouchpadScroll>", lambda event: dispatch(event, "<TouchpadScroll>"))


def window_state(root):
    if root.tk.call("tk", "windowingsystem") == "x11":
        return "zoomed" if root.attributes("-zoomed") else root.state()
    return root.state()


def set_window_state(root, state):
    if root.tk.call("tk", "windowingsystem") == "x11":
        # Unlike Windows, X11 does not accept wm state zoomed. The desktop
        # applies this attribute asynchronously and preserves window decorations.
        root.attributes("-zoomed", state == "zoomed")
        root.state("normal" if state == "zoomed" else state)
    else:
        root.state(state)
