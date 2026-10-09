"""Bounded local wheel diagnostics for investigating hardware input routing."""

from collections import deque
import json
import os
from pathlib import Path
import sys
from time import time

_records = deque(maxlen=40)
_pending = False
_metadata = None


def initialize(widget):
    global _metadata
    if not os.environ.get("ASTRO_COLLIMATOR_INPUT_LOG") or _metadata is not None:
        return
    _metadata = {"interpreter": sys.executable, "python": sys.version,
                 "source": str(Path(__file__).resolve()),
                 "tk": str(widget.tk.call("package", "provide", "Tk")),
                 "window_system": str(widget.tk.call("tk", "windowingsystem"))}
    _flush()


def snapshot(callback):
    if not os.environ.get("ASTRO_COLLIMATOR_INPUT_LOG"):
        return None
    owner = getattr(callback, "__self__", None)
    if owner is None or not hasattr(owner, "zoom_factor"):
        return None
    result = {"zoom": owner.zoom_factor, "view_center": owner.view_center,
              "source_mode": owner.source_mode}
    if owner.display_transform is not None:
        result["crop"] = vars(owner.display_transform)
    if owner.detection is not None:
        result["radii"] = {role: owner.detection.candidate(candidate_id).radius
                           for role, candidate_id in owner.selections.items()
                           if owner.detection.candidate(candidate_id) is not None}
    return result


def record(event, callback, sequence, raw_delta, axes, before):
    global _pending
    if not os.environ.get("ASTRO_COLLIMATOR_INPUT_LOG"):
        return
    root = event.widget.winfo_toplevel()
    _records.append({"time": time(), "sequence": sequence, "raw_delta": raw_delta,
                     "decoded_axes": axes, "delta": getattr(event, "delta", None),
                     "button": getattr(event, "num", None), "state": event.state,
                     "widget": str(event.widget), "widget_class": event.widget.winfo_class(),
                     "focus": str(root.focus_get()),
                     "position": [event.x, event.y],
                     "callback": getattr(callback, "__qualname__", str(callback)),
                     "before": before, "after": snapshot(callback)})
    if not _pending:
        _pending = True
        root.after(100, _flush)


def _flush():
    global _pending
    _pending = False
    path = os.environ.get("ASTRO_COLLIMATOR_INPUT_LOG")
    if not path:
        return
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((json.dumps({"runtime": _metadata, "events": list(_records)},
                                      indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    except OSError:
        pass  # Diagnostics must never interrupt viewing or control input.
