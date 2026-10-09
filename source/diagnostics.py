"""Release smoke workflow through the real application, without camera hardware."""

import json
import os
import sys
from pathlib import Path
import tempfile
import time


def smoke_test(report_path):
    import tkinter as tk
    import cv2
    import numpy as np
    from PIL import ImageTk
    from .app import WebcamApp
    from .ui_platform import window_state, set_window_state
    from .app_options import OptionsStore, TelescopeProfile, default_options_path
    from . import app as app_module, __version__

    class UnavailableCamera:
        def isOpened(self):
            return False

        def release(self):
            pass

    result = {"version": __version__, "status": "failed",
              "settings_path": str(default_options_path()),
              "python_executable": sys.executable,
              "process_id": os.getpid(),
              "virtual_environment": sys.prefix != sys.base_prefix,
              "console_attached": sys.stdout is not None}
    if sys.platform == "win32":
        import ctypes as ct
        kernel, user = ct.WinDLL("kernel32"), ct.WinDLL("user32")
        kernel.GetConsoleWindow.restype = ct.c_void_p
        user.IsWindowVisible.argtypes = (ct.c_void_p,)
        user.IsWindowVisible.restype = ct.c_int
        console = kernel.GetConsoleWindow()
        result["console_window_visible"] = bool(console and user.IsWindowVisible(console))
    root = app = None
    old_factory = app_module.open_camera
    try:
        # Only the unavailable physical camera is substituted. Tk, options,
        # detection worker, rendering and PNG/JSON exports are production code.
        app_module.open_camera = lambda index: UnavailableCamera()
        with tempfile.TemporaryDirectory(prefix="astro-collimator-check-") as directory:
            directory = Path(directory)
            root = tk.Tk()
            root.attributes("-alpha", 0)
            app = WebcamApp(root, OptionsStore(directory / "options.json"))
            deadline = time.monotonic() + 3
            while window_state(root) != "zoomed" and time.monotonic() < deadline:
                root.update()
                time.sleep(.01)
            assert window_state(root) == "zoomed", "Desktop window manager did not maximize the application"
            assert not root.attributes("-fullscreen")
            set_window_state(root, "normal")
            root.geometry("1024x768")
            app.fov_crosshair_visible.set(False)
            app.notebook.select(app.review_panel)
            # A generated optical scene avoids shipping third-party sample photos.
            frame = np.full((600, 800, 3), 25, np.uint8)
            for radius, value in ((250, 120), (200, 40), (160, 190)):
                cv2.circle(frame, (400, 300), radius, (value,) * 3, -1, cv2.LINE_AA)
            cv2.circle(frame, (405, 285), 36, (24,) * 3, -1, cv2.LINE_AA)
            cv2.circle(frame, (405, 285), 12, (160,) * 3, -1, cv2.LINE_AA)
            profile = TelescopeProfile(name="Release check", aperture_mm=200,
                                       focal_length_mm=1000, center_mark_shape="None")
            app.options_store.save(profile)
            app.profile_saved(app.options_store.load())
            ok, encoded = cv2.imencode(".png", frame)
            assert ok
            source = directory / "focuser-é.png"
            source.write_bytes(encoded.tobytes())
            app.load_image(source)
            app.start_detection()
            deadline = time.monotonic() + 15
            while app.detection is None or app.video_label.image is None:
                if time.monotonic() > deadline:
                    raise TimeoutError("Application detection/render workflow timed out")
                root.update()
                time.sleep(.005)
            assert {"Focuser edge", "Secondary edge", "Primary reflection", "Camera pupil"} <= set(app.selections)
            assert ImageTk.getimage(app.video_label.image).width > 0
            output = app.export_capture(directory / "capture.png")
            np.testing.assert_array_equal(cv2.imdecode(np.frombuffer(output.read_bytes(), np.uint8), 1), frame)
            metadata = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
            assert metadata["observations_match_image"]
            assert metadata["telescope"]["name"] == "Release check"
            assert metadata["alignment_advice"]["stage"] == "primary_tilt"
            result.update(status="passed", checks=["decorated maximized startup", "Tk rendering",
                          "setup persistence", "Unicode image import", "optical role detection",
                          "alignment guidance", "matched raw PNG and JSON export"],
                          roles=list(app.selections))
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        app_module.open_camera = old_factory
        if app is not None:
            if not app.closing:
                app.on_closing()
            app.worker.join(3)
            if app.analysis_thread:
                app.analysis_thread.join(3)
            if app.worker.is_alive() or app.analysis_thread and app.analysis_thread.is_alive():
                result.update(status="failed", error="Application worker did not close")
        elif root is not None:
            root.destroy()
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_bytes(payload.encode("utf-8"))
    return 0 if result["status"] == "passed" else 1
