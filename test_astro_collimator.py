from dataclasses import replace
import gc
import threading
import time
import tkinter as tk
import unittest
import tempfile
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np
from PIL import ImageTk

from astro_collimator import CameraWorker, WebcamApp, prepare_frame
from camera_properties import PropertyInfo
from app_options import OptionsStore, TelescopeProfile
from test_feature_detection import optical_fixture


class FakeCapture:
    def __init__(self, index, opened=True, read_ok=True, setting="accept"):
        self.index = index
        self.opened = opened
        self.read_ok = read_ok
        self.setting = setting
        self.released = False
        self.owner = threading.get_ident()
        self.values = {cv2.CAP_PROP_GAIN: 500.5, cv2.CAP_PROP_EXPOSURE: 12.25}
        self.set_calls = []
        self.frame = np.zeros((90, 160, 3), dtype=np.uint8)

    def check_owner(self):
        if self.owner != threading.get_ident():
            raise AssertionError("Camera accessed from another thread")

    def isOpened(self):
        self.check_owner()
        return self.opened and not self.released

    def get(self, prop):
        self.check_owner()
        return self.values.get(prop, 0)

    def set(self, prop, value):
        self.check_owner()
        self.set_calls.append((prop, value))
        if self.setting == "reject":
            return False
        if self.setting == "error":
            raise cv2.error("Unsupported property")
        self.values[prop] = min(value, 20) if self.setting == "clamp" else value
        return True

    def read(self):
        self.check_owner()
        if self.released:
            raise AssertionError("Read after release")
        return self.read_ok, self.frame.copy() if self.read_ok else None

    def release(self):
        self.check_owner()
        self.released = True


class WorkerTests(unittest.TestCase):
    def start_worker(self, factory, capability_provider=None):
        worker = CameraWorker(factory, max_cameras=4, capability_provider=capability_provider)
        worker.start()
        self.addCleanup(self.stop_worker, worker)
        return worker

    def stop_worker(self, worker):
        worker.stop_event.set()
        worker.join(2)
        self.assertFalse(worker.is_alive())

    def event(self, worker, kind):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            session, actual_kind, data = worker.events.get(timeout=2)
            if actual_kind == kind:
                return session, data
        self.fail(f"Missing {kind} event")

    def test_discovery_checks_gaps_and_releases_all_probes(self):
        captures = []

        def factory(index):
            cap = FakeCapture(index, opened=index in (0, 2))
            captures.append(cap)
            return cap

        worker = self.start_worker(factory)
        worker.commands.put((1, "scan", None))
        session, cameras = self.event(worker, "cameras")
        self.assertEqual((session, cameras), (1, [0, 2]))
        self.assertEqual(len(captures), 4)
        self.assertTrue(all(cap.released for cap in captures))

    def test_open_failure_and_disconnect_release_device(self):
        captures = []

        def factory(index):
            cap = FakeCapture(index, opened=index != 0, read_ok=False)
            captures.append(cap)
            return cap

        worker = self.start_worker(factory)
        worker.commands.put((1, "open", 0))
        self.assertIn("Failed to open", self.event(worker, "error")[1])
        worker.commands.put((2, "open", 1))
        self.event(worker, "opened")
        self.assertEqual(self.event(worker, "disconnected")[0], 2)
        self.assertTrue(all(cap.released for cap in captures))

    def test_switches_and_properties_stay_on_one_thread(self):
        captures = []

        def factory(index):
            cap = FakeCapture(index)
            captures.append(cap)
            return cap

        worker = self.start_worker(factory)
        worker.commands.put((1, "open", 0))
        self.event(worker, "opened")
        for session in range(2, 12):
            worker.commands.put((session, "open", session))
        worker.commands.put((1, "set", (cv2.CAP_PROP_GAIN, 99)))
        worker.commands.put((11, "set", (cv2.CAP_PROP_GAIN, 123.5)))
        session, (prop, actual, message) = self.event(worker, "property")
        self.assertEqual((session, actual), (11, 123.5))
        self.assertTrue(all(cap.released for cap in captures[:-1]))
        self.assertTrue(all(not cap.set_calls for cap in captures[:-1]))
        self.assertEqual(captures[-1].set_calls, [(cv2.CAP_PROP_GAIN, 123.5)])
        self.assertEqual(len({cap.owner for cap in captures}), 1)
        self.stop_worker(worker)
        self.assertTrue(captures[-1].released)

    def test_rejected_clamped_and_exceptional_controls(self):
        for setting, expected in (("reject", "rejected"), ("clamp", "adjusted or ignored"),
                                  ("error", "operation failed")):
            with self.subTest(setting=setting):
                worker = self.start_worker(lambda index: FakeCapture(index, setting=setting))
                worker.commands.put((1, "open", 0))
                self.event(worker, "opened")
                worker.commands.put((1, "set", (cv2.CAP_PROP_GAIN, 100)))
                _, data = self.event(worker, "error" if setting == "error" else "property")
                self.assertIn(expected, data if isinstance(data, str) else data[2])
                self.stop_worker(worker)

    def test_shutdown_during_blocked_read_keeps_release_on_owner_thread(self):
        reading = threading.Event()
        unblock = threading.Event()
        captures = []

        class BlockingCapture(FakeCapture):
            def read(self):
                reading.set()
                unblock.wait(2)
                return super().read()

        def factory(index):
            cap = BlockingCapture(index)
            captures.append(cap)
            return cap

        worker = self.start_worker(factory)
        worker.commands.put((1, "open", 0))
        self.assertTrue(reading.wait(2))
        worker.stop_event.set()
        self.assertFalse(captures[0].released)
        unblock.set()
        self.stop_worker(worker)
        self.assertTrue(captures[0].released)

    def test_capabilities_are_queried_before_open_and_enforced(self):
        order = []
        captures = []
        ranges = {"Gain": PropertyInfo("supported", 3, 19, 4, 7, 2),
                  "Zoom": PropertyInfo("unsupported"),
                  "Focus": PropertyInfo("supported", 0, 100, 1, 50, 1)}

        def query(index):
            order.append("query")
            return ranges

        def factory(index):
            order.append("open")
            cap = FakeCapture(index)
            captures.append(cap)
            return cap

        worker = self.start_worker(factory, query)
        worker.commands.put((1, "open", 0))
        _, (values, capabilities) = self.event(worker, "opened")
        self.assertEqual(order, ["query", "open"])
        self.assertEqual(capabilities[cv2.CAP_PROP_GAIN], ranges["Gain"])
        self.assertEqual(captures[0].set_calls, [])
        for prop in (cv2.CAP_PROP_ZOOM, cv2.CAP_PROP_FOCUS):
            worker.commands.put((1, "set", (prop, 50)))
            self.assertIn("unavailable", self.event(worker, "property")[1][2])
        worker.commands.put((1, "set", (cv2.CAP_PROP_GAIN, 14)))
        self.assertEqual(self.event(worker, "property")[1][1], 15)
        self.assertEqual(captures[0].set_calls, [(cv2.CAP_PROP_GAIN, 15)])


class FrameTests(unittest.TestCase):
    def test_aspect_ratio_and_color_are_preserved(self):
        for height, width in ((720, 1280), (480, 640), (1280, 720)):
            for zoom in (1, 2, 3):
                with self.subTest(size=(width, height), zoom=zoom):
                    frame = np.zeros((height, width, 3), dtype=np.uint8)
                    frame[:, :] = (10, 20, 30)
                    result = prepare_frame(frame, zoom, 960, 720)
                    h, w = result.shape[:2]
                    self.assertLessEqual(w, 960)
                    self.assertLessEqual(h, 720)
                    self.assertAlmostEqual(w / h, width / height, delta=0.01)
                    np.testing.assert_array_equal(result[h // 2, w // 2], (30, 20, 10))

    def test_zoom_crops_center_instead_of_stretching(self):
        frame = np.zeros((120, 120, 3), dtype=np.uint8)
        frame[40:80, 40:80] = (0, 0, 255)
        result = prepare_frame(frame, 3, 120, 120)
        self.assertTrue(np.all(result[:, :, 0] == 255))
        self.assertTrue(np.all(result[:, :, 1:] == 0))


class GuiTests(unittest.TestCase):
    def make_app(self, factory, capabilities=None, saved_options=None, live_tracking=False):
        root = tk.Tk()
        # Map widgets invisibly so Tk exercises real Scale idle callbacks.
        root.attributes("-alpha", 0.0)
        self.root = root
        self.callback_errors = []
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.options_store = OptionsStore(Path(directory.name) / "options.json")
        if isinstance(saved_options, TelescopeProfile):
            self.options_store.save(saved_options)
        elif saved_options is not None:
            self.options_store.path.write_bytes(saved_options)
        root.report_callback_exception = lambda *error: self.callback_errors.append(error)
        with patch("astro_collimator.open_camera", side_effect=factory), \
                patch("astro_collimator.query_camera_properties", return_value=capabilities or {}):
            self.app = WebcamApp(root, self.options_store)
        self.startup_fullscreen = bool(root.attributes("-fullscreen"))
        self.startup_window_state = root.state()
        self.app.set_fullscreen(False)
        root.state("normal")
        self.startup_fov_crosshair = self.app.fov_crosshair_visible.get()
        self.app.fov_crosshair_visible.set(False)
        self.app.track_live.set(live_tracking)
        self.app.notebook.select(self.app.camera_panel)
        self.addCleanup(self.close_app)
        return self.app

    def close_app(self):
        if not self.app.closing:
            self.app.on_closing()
        self.app.worker.join(2)
        self.assertFalse(self.app.worker.is_alive())
        if self.app.analysis_thread:
            self.app.analysis_thread.join(2)
            self.assertFalse(self.app.analysis_thread.is_alive())
        self.assertEqual(self.callback_errors, [])
        # Retire closed test windows on Tk's owning thread, before the next
        # analysis worker can trigger collection of their widget/variable cycles.
        self.app = None
        self.root = None
        gc.collect()

    def wait_until(self, predicate):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            self.root.update()
            if predicate():
                return
            time.sleep(0.005)
        self.fail("Timed out waiting for UI state")

    def test_maximized_startup_and_optional_fullscreen_keep_source_and_view(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.assertFalse(self.startup_fullscreen)
        self.assertEqual(self.startup_window_state, "zoomed")
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.zoom_factor = 2
        session = app.session
        self.assertTrue(self.root.bind("<F11>"))
        self.assertTrue(self.root.bind("<Escape>"))
        app.fullscreen_button.invoke()
        self.root.update_idletasks()
        self.assertTrue(self.root.attributes("-fullscreen"))
        self.assertEqual(app.fullscreen_button.cget("text"), "Windowed")
        app.exit_fullscreen()
        self.root.update_idletasks()
        self.assertFalse(self.root.attributes("-fullscreen"))
        self.assertEqual(app.fullscreen_button.cget("text"), "Fullscreen")
        self.assertEqual(app.zoom_factor, 2)
        self.assertEqual(app.session, session)
        np.testing.assert_array_equal(app.last_frame, optical_fixture())

    def test_changing_detection_messages_keeps_interactive_controls_still(self):
        from feature_detection import analyze_frame
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.notebook.select(app.review_panel)
        controls = [app.tracking_checkbox, app.radius_entry, app.pick_button,
                    *app.role_buttons.values()]
        frames = [optical_fixture(), np.zeros((600, 800, 3), np.uint8),
                  cv2.GaussianBlur(optical_fixture(), (0, 0), 10)]
        for size in ("1280x720", "1024x768"):
            self.root.geometry(size)
            self.root.update()
            positions = None
            for frame in frames * 2:
                app.last_frame = frame
                app.detection = analyze_frame(frame)
                app.selections = dict(app.detection.suggested)
                app.review_status.set(app.capture_advice(app.detection))
                app.refresh_review_selection()
                self.root.update_idletasks()
                current = [(widget.winfo_rootx(), widget.winfo_rooty()) for widget in controls]
                if positions is None:
                    positions = current
                self.assertEqual(current, positions)
                self.assertLess(app.tracking_checkbox.winfo_rooty(), app.advice_label.winfo_rooty())
                self.assertEqual(app.advice_label.winfo_height(), app.advice_label.winfo_reqheight())
                for widget in app.review_panel.winfo_children():
                    self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                         self.root.winfo_rooty() + self.root.winfo_height())

    def test_startup_fov_crosshair_toggle_blink_and_visibility_are_independent(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.assertTrue(self.startup_fov_crosshair)
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = np.zeros((600, 800, 3), np.uint8)
        app.view_frozen = True
        app.guides_visible.set(False)
        app.on_guide_visibility_changed()
        self.wait_until(lambda: app.video_label.image is not None)
        app.fov_checkbox.invoke()
        def rendered():
            return np.array(ImageTk.getimage(app.video_label.image))
        self.wait_until(lambda: rendered()[:, app.video_width // 2, 0].max() == 255)
        transform = app.display_transform
        center = tuple(round(v) for v in transform.to_display(app.fov_crosshair_center()))
        reference = rendered()
        self.assertEqual(tuple(reference[15, center[0], :3]), (255, 0, 0))
        self.assertEqual(tuple(reference[center[1], 15, :3]), (255, 0, 0))
        app.fov_checkbox.invoke()
        self.wait_until(lambda: not rendered()[:, :, :3].any())
        app.fov_checkbox.invoke()
        self.wait_until(lambda: rendered()[15, center[0], 0] == 255)
        app.begin_blink()
        self.wait_until(lambda: not rendered()[:, :, :3].any())
        self.assertIsNone(app.circle_at(center))
        app.end_blink()
        self.wait_until(lambda: rendered()[15, center[0], 0] == 255)
        app.overlays_visible.set(False)
        self.wait_until(lambda: not rendered()[:, :, :3].any())
        self.assertTrue(app.fov_crosshair_visible.get())
        app.overlays_visible.set(True)
        for panel in (app.review_panel, app.manual_panel, app.camera_panel):
            app.notebook.select(panel)
            self.root.update()
            self.assertTrue(app.fov_checkbox.winfo_ismapped())
            self.assertTrue(app.fov_center_button.winfo_ismapped())

    def test_fov_drag_keeps_optical_guides_fixed_and_follows_full_frame_through_view_changes(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        app.fov_checkbox.invoke()
        self.assertEqual(app.fov_crosshair_center(), (400, 300))
        detection = app.detection
        master = detection.guide_center
        transform = app.display_transform
        point = transform.to_display(app.fov_crosshair_center())
        ox = (app.video_label.winfo_width() - app.video_width) // 2
        oy = (app.video_label.winfo_height() - app.video_height) // 2
        start = SimpleNamespace(x=round(ox + point[0] + 8), y=round(oy + point[1]), num=1)
        app.hover_image(start)
        self.assertEqual(app.video_label.cget("cursor"), "fleur")
        app.begin_pan(start)
        self.assertEqual(app.circle_drag["kind"], "fov")
        end = SimpleNamespace(x=start.x + 48, y=start.y - 24, num=1)
        app.pan_image(end)
        app.end_pan(end)
        expected = (400 + 48 * transform.crop_width / transform.width,
                    300 - 24 * transform.crop_height / transform.height)
        np.testing.assert_allclose(app.fov_crosshair_center(), expected)
        self.assertEqual(app.detection, detection)
        self.assertEqual(app.detection.guide_center, master)
        self.assertIsNone(app.view_center)
        app.zoom_factor = 2
        app.set_view_center(expected)
        self.wait_until(lambda: app.display_transform.crop_width == 400)
        np.testing.assert_allclose(app.fov_crosshair_center(), expected)
        cross = tuple(round(v) for v in app.display_transform.to_display(expected))
        self.assertEqual(ImageTk.getimage(app.video_label.image).getpixel((cross[0], 15))[:3], (255, 0, 0))
        self.assertEqual(app.circle_at(cross)["kind"], "fov")
        # A distant crosshair line is still ordinary pan space, not a huge hit target.
        self.assertIsNone(app.circle_at((cross[0], 5)))
        app.reset_view()
        self.wait_until(lambda: app.display_transform.crop_width == 800)
        np.testing.assert_allclose(app.fov_crosshair_center(), expected)
        app.picking_role = "Secondary edge"
        self.assertIsNone(app.circle_at(app.display_transform.to_display(expected)))
        app.cancel_pick()
        app.fov_center_button.invoke()
        self.assertEqual(app.fov_crosshair_center(), (400, 300))
        self.assertEqual(app.detection, detection)
        self.assertEqual(app.detection.guide_center, master)
        # Circle-rim dragging moves the guide group, not the absolute reference.
        edge = app.detection.candidate(app.selections["Focuser edge"])
        rim = app.display_transform.to_display((master[0] + edge.radius, master[1]))
        start = SimpleNamespace(x=round(ox + rim[0]), y=round(oy + rim[1]), num=1)
        app.begin_pan(start)
        self.assertEqual(app.circle_drag["kind"], "candidate")
        end = SimpleNamespace(x=start.x - 20, y=start.y + 10, num=1)
        app.pan_image(end)
        app.end_pan(end)
        self.assertNotEqual(app.detection.guide_center, master)
        self.assertEqual(app.fov_crosshair_center(), (400, 300))

    def test_fov_position_survives_tracking_detect_exports_and_recenters_on_source_change(self):
        from feature_detection import analyze_frame
        captures = []
        def factory(index):
            cap = FakeCapture(index, opened=index == 0)
            cap.frame = optical_fixture()
            captures.append(cap)
            return cap
        app = self.make_app(factory, live_tracking=True)
        self.wait_until(lambda: app.last_frame is not None)
        app.fov_checkbox.invoke()
        app.set_fov_crosshair_center((320, 225))
        expected = app.fov_crosshair_center()
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        np.testing.assert_allclose(app.fov_crosshair_center(), expected)
        shifted = cv2.warpAffine(optical_fixture(), np.float32([[1, 0, 10], [0, 1, 5]]), (800, 600),
                                 borderValue=(25, 25, 25))
        captures[-1].frame = shifted.copy()
        self.wait_until(lambda: app.detection.guide_center[0] > 408)
        np.testing.assert_allclose(app.fov_crosshair_center(), expected)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        np.testing.assert_allclose(app.fov_crosshair_center(), expected)
        output = app.export_capture(app.options_store.path.with_name("fov.png"))
        metadata = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertTrue(metadata["fov_crosshair"]["visible"])
        np.testing.assert_allclose(metadata["fov_crosshair"]["center_px"], expected)
        np.testing.assert_array_equal(cv2.imdecode(np.frombuffer(output.read_bytes(), np.uint8), 1), shifted)
        app.load_image(output)
        self.assertEqual(app.fov_crosshair_center(), (400, 300))
        self.assertTrue(app.fov_crosshair_visible.get())
        app.set_fov_crosshair_center((200, 100))
        app.resume_live()
        self.wait_until(lambda: app.last_frame is not None and app.camera_on)
        self.assertEqual(app.fov_crosshair_center(), (400, 300))

    def test_no_camera_startup_and_refresh_recovery(self):
        available = set()
        app = self.make_app(lambda index: FakeCapture(index, opened=index in available))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        self.assertFalse(app.camera_on)
        self.assertEqual(str(app.camera_dropdown.cget("state")), "disabled")
        self.assertEqual(app.last_frame, None)
        available.add(2)
        app.refresh_cameras()
        self.wait_until(lambda: app.camera_on and app.last_frame is not None)
        self.assertEqual(app.selected_camera.get(), "Camera 2")
        self.assertAlmostEqual(app.video_width / app.video_height, 160 / 90, delta=0.01)
        self.assertEqual(app.camera_controls[cv2.CAP_PROP_GAIN].value.get(), "500.5")

    def test_main_thread_rendering_and_invalid_values(self):
        captures = []

        def factory(index):
            cap = FakeCapture(index, opened=index == 0)
            captures.append(cap)
            return cap

        app = self.make_app(factory)
        self.wait_until(lambda: app.last_frame is not None)
        self.assertTrue(all(not cap.set_calls for cap in captures))
        control = app.camera_controls[cv2.CAP_PROP_GAIN].value
        for value in ("invalid", "nan", "inf"):
            control.set(value)
            app.apply_camera_value(cv2.CAP_PROP_GAIN)
            self.assertIn("finite numeric", app.loading_label.cget("text"))
        control.set("123.75")
        app.apply_camera_value(cv2.CAP_PROP_GAIN)
        self.wait_until(lambda: control.get() == "123.75" and bool(captures[-1].set_calls))
        self.assertEqual(app.loading_label.cget("text"), "Camera connected.")
        app.show_crosshair = True
        app.move_crosshair(10000, 10000)
        self.assertEqual((app.crosshair_x, app.crosshair_y), (app.video_width - 1, app.video_height - 1))
        app.reset_crosshair()
        self.assertEqual((app.crosshair_x, app.crosshair_y), (app.video_width // 2, app.video_height // 2))
        image = app.video_label.image
        self.wait_until(lambda: app.video_label.image is not image)

    def test_stale_messages_do_not_restore_previous_camera(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.worker.events.put((app.session - 1, "opened", {cv2.CAP_PROP_GAIN: 99}))
        app.worker.frames.put((app.session - 1, np.zeros((90, 160, 3), dtype=np.uint8)))
        self.wait_until(lambda: app.worker.events.empty() and app.worker.frames.empty())
        self.assertFalse(app.camera_on)
        self.assertIsNone(app.last_frame)

    def test_failed_open_keeps_controls_disabled_and_allows_refresh(self):
        visits = {}

        def factory(index):
            visits[index] = visits.get(index, 0) + 1
            return FakeCapture(index, opened=index == 0 and visits[index] == 1)

        app = self.make_app(factory)
        self.wait_until(lambda: "Failed to open" in app.loading_label.cget("text"))
        self.assertFalse(app.camera_on)
        self.assertEqual(str(app.refresh_button.cget("state")), "normal")
        self.assertTrue(all(str(control.entry.cget("state")) == "disabled"
                            for control in app.camera_controls.values()))

    def test_disconnect_clears_video_and_disables_controls(self):
        captures = []

        def factory(index):
            cap = FakeCapture(index, opened=index == 0)
            captures.append(cap)
            return cap

        app = self.make_app(factory)
        self.wait_until(lambda: app.last_frame is not None)
        captures[-1].read_ok = False
        self.wait_until(lambda: "stopped delivering" in app.loading_label.cget("text"))
        self.assertFalse(app.camera_on)
        self.assertIsNone(app.last_frame)
        self.assertIsNone(app.video_label.image)

    def test_driver_ranges_restore_sliders_and_disable_unavailable_controls(self):
        captures = []

        def factory(index):
            cap = FakeCapture(index, opened=index == 0)
            cap.values[cv2.CAP_PROP_GAIN] = 7
            captures.append(cap)
            return cap

        ranges = {"Gain": PropertyInfo("supported", 3, 19, 4, 7, 2),
                  "Zoom": PropertyInfo("unsupported"),
                  "Focus": PropertyInfo("supported", 0, 100, 1, 50, 1)}
        app = self.make_app(factory, ranges)
        self.wait_until(lambda: app.last_frame is not None)
        gain = app.camera_controls[cv2.CAP_PROP_GAIN]
        self.assertEqual((gain.slider.cget("from"), gain.slider.cget("to")), (3.0, 19.0))
        self.assertEqual(gain.slider.get(), 7)
        # Initialization must not set camera controls, even after Tk's idle callbacks.
        self.assertTrue(all(not cap.set_calls for cap in captures))
        self.assertFalse(app.camera_controls[cv2.CAP_PROP_ZOOM].enabled)
        self.assertFalse(app.camera_controls[cv2.CAP_PROP_FOCUS].enabled)
        self.assertEqual(app.camera_controls[cv2.CAP_PROP_ZOOM].note.cget("text"),
                         "Not supported")
        self.assertEqual(app.camera_controls[cv2.CAP_PROP_FOCUS].note.cget("text"), "Automatic only")
        self.assertEqual(app.camera_controls[cv2.CAP_PROP_EXPOSURE].info.status, "unknown")
        gain.slider.event_generate("<MouseWheel>", delta=120)
        self.wait_until(lambda: bool(captures[-1].set_calls))
        self.assertEqual(captures[-1].set_calls, [(cv2.CAP_PROP_GAIN, 11)])
        self.assertEqual(app.zoom_factor, 1.0)

    def test_slider_debounce_is_cancelled_when_camera_changes(self):
        captures = []

        def factory(index):
            cap = FakeCapture(index, opened=index in (0, 1))
            cap.values[cv2.CAP_PROP_GAIN] = 7
            captures.append(cap)
            return cap

        ranges = {"Gain": PropertyInfo("supported", 3, 19, 4, 7, 2)}
        app = self.make_app(factory, ranges)
        self.wait_until(lambda: app.last_frame is not None)
        control = app.camera_controls[cv2.CAP_PROP_GAIN]
        control.slider.set(15)
        self.root.update_idletasks()
        self.assertIsNotNone(control.pending_after)
        app.selected_camera.set("Camera 1")
        app.on_camera_selected(None)
        self.wait_until(lambda: app.last_frame is not None)
        self.assertTrue(all(not cap.set_calls for cap in captures))
        self.assertIsNone(control.pending_after)

    def test_compact_control_group_fits_existing_window_and_hides_value_feedback(self):
        ranges = {name: PropertyInfo("supported", 0, 255, 1, 50, 3)
                  for name in ("Gain", "Exposure", "Zoom", "Focus")}
        app = self.make_app(lambda index: FakeCapture(index, opened=index == 0), ranges)
        self.wait_until(lambda: app.last_frame is not None)
        self.assertLessEqual(sum(control.winfo_height() for control in app.camera_controls.values()), 180)
        self.root.update_idletasks()
        self.assertLessEqual(app.dpad_frame.winfo_y() + app.dpad_frame.winfo_height(), self.root.winfo_height())
        app.handle_camera_event("property", (cv2.CAP_PROP_GAIN, 50, "Gain: camera reports 50."))
        self.assertEqual(app.loading_label.cget("text"), "Camera connected.")

    def test_named_references_render_individually_and_share_a_user_placed_center(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=index == 0))
        self.wait_until(lambda: app.last_frame is not None)
        self.assertEqual([ring.name.get() for ring in app.ring_controls],
                         ["Focuser edge", "Secondary edge", "Primary reflection"])
        app.fov_crosshair_visible.set(True)
        inner = app.ring_controls[2]
        point = (app.crosshair_x + inner.slider.get(), app.crosshair_y)
        self.assertEqual(ImageTk.getimage(app.video_label.image).getpixel(point)[:3], inner.color)
        inner.visible.set(False)
        previous_image = app.video_label.image
        self.wait_until(lambda: app.video_label.image is not previous_image)
        self.assertEqual(ImageTk.getimage(app.video_label.image).getpixel(point)[:3], (255, 0, 0))

        app.toggle_crosshair()
        previous_image = app.video_label.image
        self.wait_until(lambda: app.video_label.image is not previous_image)
        self.assertEqual(ImageTk.getimage(app.video_label.image).getpixel(point)[:3], (255, 0, 0))
        app.fov_checkbox.invoke()
        previous_image = app.video_label.image
        self.wait_until(lambda: app.video_label.image is not previous_image)
        self.assertEqual(ImageTk.getimage(app.video_label.image).getpixel(point)[:3], (0, 0, 0))
        app.toggle_crosshair()
        offset_x = (app.video_label.winfo_width() - app.video_width) // 2
        offset_y = (app.video_label.winfo_height() - app.video_height) // 2
        app.place_guide_center(SimpleNamespace(x=offset_x + 40, y=offset_y + 50))
        self.assertEqual((app.crosshair_x, app.crosshair_y), (40, 50))
        radii = [ring.slider.get() for ring in app.ring_controls]
        inner.scroll(SimpleNamespace(delta=120))
        self.assertEqual([ring.slider.get() for ring in app.ring_controls], [*radii[:2], radii[2] + 1])
        self.assertEqual((app.crosshair_x, app.crosshair_y, app.zoom_factor), (40, 50, 1.0))

        with patch("astro_collimator.messagebox.showinfo") as show_help:
            app.show_guide_help()
        self.assertIn("Newtonian", show_help.call_args.args[0])
        self.assertIn("starting circles are presets", show_help.call_args.args[1])
        self.assertIn("sizes are independent", show_help.call_args.args[1])

    def test_static_detection_draws_guides_without_confirmation(self):
        captures = []

        def factory(index):
            cap = FakeCapture(index, opened=index == 0)
            cap.frame = optical_fixture()
            captures.append(cap)
            return cap

        app = self.make_app(factory)
        self.wait_until(lambda: app.last_frame is not None)
        app.notebook.select(app.review_panel)
        raw = app.last_frame.copy()
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        self.assertFalse(app.view_frozen)
        self.assertFalse(app.show_crosshair)
        self.assertFalse(app.confirmed)
        self.assertEqual(len(app.selections), 4)
        captures[-1].frame[:] = 0
        previous = app.video_label.image
        self.wait_until(lambda: app.video_label.image is not previous)
        self.wait_until(lambda: not app.last_frame.any())
        self.assertFalse(hasattr(app, "confirm_button"))
        self.assertFalse(app.confirmed)
        app.review_role.set("Focuser edge")
        app.review_role_changed()
        app.candidate_choice.set("Unassigned")
        app.choose_candidate()
        self.assertFalse(app.confirmed)
        self.assertNotIn("Focuser edge", app.selections)
        app.resume_live()
        self.wait_until(lambda: app.last_frame is not None and not app.view_frozen)
        self.assertIsNone(app.detection)
        self.assertTrue(app.show_crosshair)

    def test_manual_clicks_use_zoom_transform_and_move_the_shared_center(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=index == 0))
        self.wait_until(lambda: app.last_frame is not None)
        app.notebook.select(app.review_panel)
        app.zoom_factor = 2
        previous = app.video_label.image
        self.wait_until(lambda: app.video_label.image is not previous)
        app.review_role.set("Secondary edge")
        app.begin_manual_pick()
        for point in ((100, 45), (80, 65), (60, 45)):
            x, y = app.display_transform.to_display(point)
            offset_x = (app.video_label.winfo_width() - app.video_width) // 2
            offset_y = (app.video_label.winfo_height() - app.video_height) // 2
            app.place_guide_center(SimpleNamespace(x=x + offset_x, y=y + offset_y))
        edge = app.detection.candidate(app.selections["Secondary edge"])
        np.testing.assert_allclose(edge.center, (80, 45), atol=0.1)
        self.assertAlmostEqual(edge.radius, 20, delta=0.1)
        self.assertFalse(app.confirmed)
        app.review_role.set("Center mark")
        app.review_role_changed()
        app.begin_manual_pick()
        app.pick_review_point((84, 47))
        mark = app.detection.candidate(app.selections["Center mark"])
        self.assertEqual(mark.center, (80, 45))
        self.assertEqual(app.manual_references["Center mark"].center, (84, 47))
        self.assertEqual(mark.provenance, "concentric_guess")
        self.assertFalse(app.confirmed)
        self.assertEqual(app.detection.candidate(app.selections["Secondary edge"]).center, mark.center)
        self.assertEqual(app.detection.guide_center, mark.center)

    def test_import_unicode_image_and_export_raw_pixels_and_metadata(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        path = app.options_store.path.parent / "télescope.png"
        frame = optical_fixture()
        path.write_bytes(cv2.imencode(".png", frame)[1].tobytes())
        app.load_image(path)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        app.profile = TelescopeProfile(name="Saved telescope", aperture_mm=130, focal_length_mm=650)
        output = app.export_capture(path.with_name("capture-é.png"))
        saved = cv2.imdecode(np.frombuffer(output.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        np.testing.assert_array_equal(saved, frame)
        metadata = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["telescope"]["aperture_mm"], 130)
        self.assertNotIn("confirmed", metadata)
        self.assertIn("alignment_advice", metadata)
        self.assertTrue(metadata["detection"]["observations"])
        self.assertEqual(metadata["image_size"], [800, 600])
        self.assertEqual(metadata["detection"]["image_size"], [800, 600])
        self.assertFalse(app.camera_on)

    def test_inflight_results_are_discarded_after_source_changes(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=index == 0))
        self.wait_until(lambda: app.last_frame is not None)
        release = threading.Event()
        entered = threading.Event()
        self.addCleanup(release.set)

        def delayed(frame, shape, **kwargs):
            entered.set()
            release.wait(2)
            from feature_detection import analyze_frame
            return analyze_frame(optical_fixture())

        with patch("collimation_review.analyze_frame", side_effect=delayed):
            app.start_detection()
            self.assertTrue(entered.wait(1))
            app.resume_live()
            release.set()
            self.wait_until(lambda: not app.analysis_busy and app.last_frame is not None)
        self.assertIsNone(app.detection)
        self.assertFalse(app.selections)
        self.assertFalse(app.view_frozen)

    def test_setup_validation_save_and_cancel_preserve_options(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.show_options()
        dialog = app.setup_dialog
        dialog.variables["aperture_mm"].set("nan")
        dialog.save()
        self.assertTrue(dialog.error.get())
        self.assertFalse(app.options_store.path.exists())
        dialog.variables["name"].set("My Newtonian")
        dialog.variables["aperture_mm"].set("130")
        dialog.variables["focal_length_mm"].set("650")
        dialog.mark_shape.set("Triangle")
        self.assertNotIn("max_eccentricity", dialog.variables)
        dialog.save()
        self.assertEqual(app.profile, app.options_store.load())
        self.assertFalse(hasattr(app.profile, "max_eccentricity"))
        self.assertIsNone(app.profile.secondary_minor_axis_mm)
        self.assertIn("f/5", app.profile_label.cget("text"))
        before = app.options_store.path.read_bytes()
        app.show_options()
        app.setup_dialog.variables["name"].set("Canceled")
        app.setup_dialog.destroy()
        self.assertEqual(app.options_store.path.read_bytes(), before)

    def test_review_controls_and_video_fit_regular_screens(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=index == 0))
        self.wait_until(lambda: app.last_frame is not None)
        for size in ("1280x720", "1024x768"):
            app.root.geometry(size)
            for panel in (app.review_panel, app.manual_panel, app.camera_panel):
                app.notebook.select(panel)
                previous = app.video_label.image
                self.wait_until(lambda: app.video_label.image is not previous)
                self.root.update_idletasks()
                for widget in panel.winfo_children():
                    self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                         self.root.winfo_rooty() + self.root.winfo_height())
                self.assertLessEqual(app.video_width + app.sidebar.winfo_width() + 14, self.root.winfo_width())
                self.assertLessEqual(app.video_height + 14, self.root.winfo_height())

    def test_saved_setup_is_loaded_at_startup(self):
        profile = TelescopeProfile(name="My saved scope", aperture_mm=200, focal_length_mm=1000,
                                   center_mark_shape="Ring", mounting_notes="Top mark faces up")
        app = self.make_app(lambda index: FakeCapture(index, opened=False), saved_options=profile)
        self.assertEqual(app.profile, profile)
        self.assertIn("My saved scope", app.profile_label.cget("text"))

    def test_corrupt_options_are_reported_and_preserved_at_startup(self):
        original = b"{broken options"
        app = self.make_app(lambda index: FakeCapture(index, opened=False), saved_options=original)
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        self.assertEqual(app.options_store.path.read_bytes(), original)
        self.assertIn("could not be loaded", app.profile_label.cget("text"))
        self.assertEqual(app.profile, TelescopeProfile())

    def test_analysis_failure_retains_raw_image_for_manual_review(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=index == 0))
        self.wait_until(lambda: app.last_frame is not None)
        raw = app.last_frame.copy()
        with patch("collimation_review.analyze_frame", side_effect=ValueError("Invalid image fixture")):
            app.start_detection()
            self.wait_until(lambda: "Analysis failed" in app.review_status.get())
        self.assertTrue(app.view_frozen)
        np.testing.assert_array_equal(app.last_frame, raw)
        app.review_role.set("Center mark")
        app.begin_manual_pick()
        app.pick_review_point((80, 45))
        self.assertIn("Center mark", app.selections)

    def test_pan_zoom_and_reset_keep_measurements_and_manual_guides_on_image(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        raw = optical_fixture()
        app.last_frame = raw.copy()
        app.view_frozen = True
        app.notebook.select(app.review_panel)
        self.wait_until(lambda: app.video_label.image is not None)
        app.zoom_factor = 2
        self.wait_until(lambda: app.display_transform.crop_width == 400)
        transform = app.display_transform
        guide_point = transform.to_original((app.crosshair_x, app.crosshair_y))
        radius_in_raw = app.ring_controls[0].slider.get() * transform.crop_width / transform.width
        offset_x = (app.video_label.winfo_width() - app.video_width) // 2
        offset_y = (app.video_label.winfo_height() - app.video_height) // 2
        x, y = offset_x + 20, offset_y + 20
        app.video_label.event_generate("<ButtonPress-1>", x=x, y=y)
        app.video_label.event_generate("<B1-Motion>", x=x + 100, y=y + 60)
        app.video_label.event_generate("<ButtonRelease-1>", x=x + 100, y=y + 60)
        self.wait_until(lambda: app.display_transform.crop_x != transform.crop_x)
        panned = app.display_transform
        self.assertAlmostEqual(panned.crop_x, transform.crop_x - 100 * transform.crop_width / transform.width, delta=1)
        self.assertAlmostEqual(panned.crop_y, transform.crop_y - 60 * transform.crop_height / transform.height, delta=1)
        np.testing.assert_allclose(panned.to_original((app.crosshair_x, app.crosshair_y)), guide_point, atol=1)
        self.assertAlmostEqual(app.ring_controls[0].slider.get() * panned.crop_width / panned.width, radius_in_raw, delta=1)
        self.assertIsNone(app.pan_anchor)
        app.review_role.set("Center mark")
        app.begin_manual_pick()
        screen_point = (app.video_width * 0.4, app.video_height * 0.6)
        expected = panned.to_original(screen_point)
        offset_x = (app.video_label.winfo_width() - app.video_width) // 2
        offset_y = (app.video_label.winfo_height() - app.video_height) // 2
        event = SimpleNamespace(x=offset_x + screen_point[0], y=offset_y + screen_point[1], delta=120)
        app.place_guide_center(event)
        edge = app.detection.candidate(app.selections["Center mark"])
        np.testing.assert_allclose(edge.center, expected, atol=1e-8)
        app.zoom_with_scroll(event)
        self.wait_until(lambda: app.display_transform.crop_width < panned.crop_width)
        np.testing.assert_allclose(app.display_transform.to_original(screen_point), expected, atol=1)
        np.testing.assert_array_equal(app.last_frame, raw)
        self.assertEqual(app.detection.candidate(edge.id), edge)
        app.begin_pan(event)
        app.pan_image(SimpleNamespace(x=-10000, y=-10000))
        self.wait_until(lambda: app.display_transform.crop_x + app.display_transform.crop_width == 800)
        app.end_pan()
        app.reset_view()
        self.wait_until(lambda: app.display_transform.crop_width == 800)
        self.assertEqual((app.display_transform.crop_x, app.display_transform.crop_y), (0, 0))
        self.assertIsNone(app.view_center)
        self.assertEqual(app.zoom_factor, 1)
        self.assertEqual(app.detection.candidate(edge.id), edge)

    def test_left_click_places_on_release_but_drag_never_adds_a_pick(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.view_frozen = True
        app.zoom_factor = 2
        app.notebook.select(app.review_panel)
        self.wait_until(lambda: app.video_label.image is not None)
        x = (app.video_label.winfo_width() - app.video_width) // 2 + app.video_width // 3
        y = (app.video_label.winfo_height() - app.video_height) // 2 + app.video_height // 3
        before = (app.crosshair_x, app.crosshair_y)
        app.video_label.event_generate("<ButtonPress-1>", x=x, y=y)
        self.assertEqual((app.crosshair_x, app.crosshair_y), before)
        app.video_label.event_generate("<B1-Motion>", x=x + 2, y=y)
        self.assertIsNone(app.view_center)
        app.video_label.event_generate("<ButtonRelease-1>", x=x + 2, y=y)
        self.assertEqual((app.crosshair_x, app.crosshair_y),
                         app.image_position(SimpleNamespace(x=x + 2, y=y)))
        app.review_role.set("Center mark")
        app.begin_manual_pick()
        previous = app.display_transform
        app.video_label.event_generate("<ButtonPress-1>", x=x, y=y)
        app.video_label.event_generate("<B1-Motion>", x=x + 30, y=y)
        app.video_label.event_generate("<ButtonRelease-1>", x=x + 30, y=y)
        self.assertIsNone(app.detection)
        self.assertEqual(app.pick_points, [])
        self.assertEqual(app.picking_role, "Center mark")
        self.wait_until(lambda: app.display_transform != previous)
        expected = app.display_transform.to_original(app.image_position(SimpleNamespace(x=x, y=y)))
        app.video_label.event_generate("<ButtonPress-1>", x=x, y=y)
        self.assertIsNone(app.detection)
        app.video_label.event_generate("<ButtonRelease-1>", x=x, y=y)
        edge = app.detection.candidate(app.selections["Center mark"])
        np.testing.assert_allclose(edge.center, expected, atol=1e-8)
        self.assertIsNone(app.picking_role)
        self.assertIsNone(app.pan_anchor)

    def test_hold_blink_hides_overlays_and_release_restores_without_changing_references(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.view_frozen = True
        app.notebook.select(app.review_panel)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        app.zoom_factor = 2
        app.set_view_center((350, 240))
        self.wait_until(lambda: app.display_transform.crop_width == 400)
        app.review_role.set("Secondary edge")
        app.begin_manual_pick()
        app.pick_review_point((340, 245))
        detection, selections, confirmed = app.detection, dict(app.selections), set(app.confirmed)
        transform = app.display_transform
        picks = list(app.pick_points)
        previous = app.video_label.image
        self.wait_until(lambda: app.video_label.image is not previous)
        with_overlays = np.array(ImageTk.getimage(app.video_label.image).convert("RGB"))
        previous = app.video_label.image
        app.video_label.event_generate("<ButtonPress-3>", x=50, y=50)
        self.wait_until(lambda: app.video_label.image is not previous)
        self.assertTrue(app.overlays_visible.get())
        self.assertTrue(app.blink_active)
        hidden = np.array(ImageTk.getimage(app.video_label.image).convert("RGB"))
        expected = prepare_frame(app.last_frame, app.zoom_factor, transform.width, transform.height, app.view_center)
        np.testing.assert_array_equal(hidden, expected)
        self.assertTrue(np.any(hidden != with_overlays))
        self.assertEqual(app.display_transform, transform)
        previous = app.video_label.image
        app.video_label.event_generate("<ButtonRelease-3>", x=50, y=50)
        self.wait_until(lambda: app.video_label.image is not previous)
        self.assertTrue(app.overlays_visible.get())
        self.assertFalse(app.blink_active)
        np.testing.assert_array_equal(np.array(ImageTk.getimage(app.video_label.image).convert("RGB")), with_overlays)
        self.assertEqual(app.detection, detection)
        self.assertEqual(app.selections, selections)
        self.assertEqual(app.confirmed, confirmed)
        self.assertEqual(app.pick_points, picks)
        self.assertEqual(app.display_transform, transform)

    def test_dragging_a_circle_moves_the_whole_group_and_detect_resets_it(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        raw = optical_fixture()
        app.last_frame = raw.copy()
        app.view_frozen = True
        app.notebook.select(app.review_panel)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        app.review_role.set("Focuser edge")
        app.review_role_changed()
        originals = {edge.id: edge for edge in app.detection.candidates}
        original = app.detection.candidate(app.selections["Focuser edge"])
        app.zoom_factor = 2
        app.set_view_center((375, 280))
        self.wait_until(lambda: app.display_transform.crop_width == 400)
        transform = app.display_transform
        px, py = transform.to_display(original.center)
        x = round(px) + (app.video_label.winfo_width() - app.video_width) // 2
        y = round(py) + (app.video_label.winfo_height() - app.video_height) // 2
        delta = (45 * transform.crop_width / transform.width, -30 * transform.crop_height / transform.height)
        app.video_label.event_generate("<ButtonPress-1>", x=x, y=y)
        app.video_label.event_generate("<B1-Motion>", x=x + 45, y=y - 30)
        app.video_label.event_generate("<ButtonRelease-1>", x=x + 45, y=y - 30)
        moved = app.detection.candidate(original.id)
        np.testing.assert_allclose(moved.center, np.add(original.center, delta), atol=1e-8)
        self.assertEqual(moved.axes, original.axes)
        self.assertEqual(moved.provenance, "manual_drag")
        self.assertIsNone(moved.fit_quality)
        self.assertFalse(moved.support_bins)
        self.assertNotIn("Focuser edge", app.confirmed)
        self.assertNotIn("Focuser edge", app.detection.suggested)
        for edge in app.detection.candidates:
            np.testing.assert_allclose(edge.center, moved.center, atol=1e-8)
            self.assertEqual(edge.axes, originals[edge.id].axes)
            self.assertEqual(edge.provenance, "manual_drag")
        self.assertFalse(app.confirmed)
        self.assertEqual(app.display_transform, transform)
        np.testing.assert_array_equal(app.last_frame, raw)
        output = app.export_capture(app.options_store.path.with_name("dragged.png"))
        metadata = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        record = metadata["manual_adjustments"][str(moved.id)]
        np.testing.assert_allclose(record["original"]["center"], original.center)
        np.testing.assert_allclose(record["translation"], delta)
        # Move the same reference again; exported translation stays cumulative.
        app.move_review_candidate(moved, (2, 3), ())
        np.testing.assert_allclose(app.manual_adjustments[moved.id]["translation"], np.add(delta, (2, 3)))
        app.overlays_visible.set(False)
        app.start_detection()
        self.assertTrue(app.overlays_visible.get())
        self.assertIsNone(app.circle_drag)
        self.assertEqual(app.manual_adjustments, {})
        self.wait_until(lambda: app.detection is not None)
        new = app.detection.candidate(app.selections["Focuser edge"])
        np.testing.assert_allclose(new.center, original.center, atol=1e-8)
        self.assertEqual(new.provenance, "concentric_guess")
        self.assertIsNone(new.fit_quality)
        self.assertTrue(app.detection.observations)
        self.assertFalse(app.confirmed)

    def test_manual_rim_drag_and_global_reset_preserve_reference_positions(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.view_frozen = True
        self.wait_until(lambda: app.video_label.image is not None)
        app.notebook.select(app.manual_panel)
        radius = app.ring_controls[1].slider.get()
        before = (app.crosshair_x, app.crosshair_y)
        offset_x = (app.video_label.winfo_width() - app.video_width) // 2
        offset_y = (app.video_label.winfo_height() - app.video_height) // 2
        x, y = offset_x + before[0] + radius, offset_y + before[1]
        radii = [ring.slider.get() for ring in app.ring_controls]
        app.video_label.event_generate("<ButtonPress-1>", x=x, y=y)
        app.video_label.event_generate("<B1-Motion>", x=x - 25, y=y + 15)
        app.video_label.event_generate("<ButtonRelease-1>", x=x - 25, y=y + 15)
        self.assertEqual((app.crosshair_x, app.crosshair_y), (before[0] - 25, before[1] + 15))
        self.assertIsNone(app.view_center)
        self.assertEqual([ring.slider.get() for ring in app.ring_controls], radii)
        point = app.display_transform.to_original((app.crosshair_x, app.crosshair_y))
        for panel in (app.manual_panel, app.camera_panel, app.review_panel):
            app.notebook.select(panel)
            app.zoom_factor = 2
            app.set_view_center((350, 240))
            self.wait_until(lambda: app.display_transform.crop_width == 400)
            self.assertTrue(app.view_reset_button.winfo_ismapped())
            app.view_reset_button.invoke()
            self.wait_until(lambda: app.display_transform.crop_width == 800)
            np.testing.assert_allclose(app.display_transform.to_original((app.crosshair_x, app.crosshair_y)), point, atol=2)
            self.assertIsNone(app.view_center)

    def test_outline_replacements_keep_roundness_and_the_master_center(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture(ellipse=True)
        app.notebook.select(app.review_panel)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        center = app.detection.guide_center
        for role in ("Focuser edge", "Secondary edge", "Primary reflection"):
            app.role_buttons[role].invoke()
            app.toggle_alternatives()
            app.cycle_candidate(1)
            guide = app.detection.candidate(app.selections[role])
            self.assertEqual(guide.axes[0], guide.axes[1])
            self.assertEqual(guide.center, center)
            app.close_alternatives()
        self.assertTrue(all(edge.center == center for edge in app.detection.candidates))
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        self.assertFalse(app.confirmed)
        self.assertTrue(all(edge.axes[0] == edge.axes[1] for edge in app.detection.candidates))

    def test_named_outlines_hide_extra_hypotheses_and_guidance_advances(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.notebook.select(app.review_panel)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        previous = app.video_label.image
        self.wait_until(lambda: app.video_label.image is not previous)
        normal = np.array(ImageTk.getimage(app.video_label.image))
        extra = replace(app.detection.candidates[0], id=20, center=(220, 150), axes=(35, 35), support_bins=())
        app.detection = replace(app.detection, candidates=app.detection.candidates + (extra,))
        app.refresh_review_selection()
        previous = app.video_label.image
        self.wait_until(lambda: app.video_label.image is not previous)
        np.testing.assert_array_equal(np.array(ImageTk.getimage(app.video_label.image)), normal)
        self.assertFalse(app.show_candidates.get())
        self.assertFalse(app.alternative_panel.winfo_ismapped())
        self.assertIn("3 / 4 required circles present", app.review_progress.get())
        self.assertTrue(app.next_step.get())
        self.assertFalse(hasattr(app, "confirm_button"))
        app.toggle_alternatives()
        self.root.update()
        self.assertTrue(app.alternative_panel.winfo_ismapped())
        app.candidate_choice.set(next(label for label, value in app.candidate_labels.items() if value == 20))
        app.choose_candidate()
        self.assertEqual(len(app.selections), 4)
        self.assertEqual(app.selections["Focuser edge"], 20)
        self.assertEqual(app.detection.guide_master_id, 20)
        self.assertEqual(app.detection.guide_center, (220, 150))
        self.assertTrue(all(edge.center == (220, 150) for edge in app.detection.candidates))
        app.clear_reference()
        self.assertNotIn("Focuser edge", app.manual_references)
        self.assertNotEqual(app.detection.guide_master_id, 20)
        self.assertFalse(app.show_candidates.get())
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        self.assertFalse(app.alternatives_open)
        self.assertIn("3 / 4 required circles present", app.review_progress.get())
        self.assertNotIn("confirm", app.next_step.get().lower())
        self.assertEqual(app.alignment.stage, "capture")
        self.assertIn("Camera pupil", app.next_step.get())
        self.assertIn("Shared guide center", app.measurement_text.get())
        self.assertNotIn("Image offsets", app.measurement_text.get())
        for size in ("1280x720", "1024x768"):
            self.root.geometry(size)
            self.root.update()
            for widget in app.review_panel.winfo_children():
                if widget.winfo_ismapped():
                    self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                         self.root.winfo_rooty() + self.root.winfo_height())
            for label in (app.next_step_label, app.summary_label, app.measurement_label):
                self.assertEqual(label.winfo_height(), label.winfo_reqheight())
        app.select_review_role("Center mark")
        app.clear_reference()
        self.assertIn("Mark: optional", app.reference_summary.get())
        self.assertNotIn("Missing Center mark", app.next_step.get())

    def test_blink_release_outside_image_and_focus_loss_restore_previous_visibility(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.begin_blink()
        self.assertTrue(app.blink_active)
        app.root.event_generate("<ButtonRelease-3>", x=5, y=5)
        self.root.update()
        self.assertFalse(app.blink_active)
        self.assertTrue(app.overlays_shown())
        app.begin_blink()
        app.root.event_generate("<FocusOut>")
        self.root.update()
        self.assertFalse(app.blink_active)
        app.overlays_visible.set(False)
        app.begin_blink()
        app.end_blink()
        self.assertFalse(app.overlays_shown())
        self.assertFalse(app.overlays_visible.get())

    def test_circle_click_selects_the_role_without_a_dropdown(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.notebook.select(app.review_panel)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        self.assertFalse(hasattr(app, "role_combo"))
        self.assertFalse(hasattr(app, "candidate_combo"))
        self.wait_until(lambda: app.video_label.image is not None)
        for role in ("Primary reflection", "Secondary edge", "Focuser edge", "Center mark"):
            edge = app.detection.candidate(app.selections[role])
            px, py = app.display_transform.to_display((edge.center[0] + edge.radius, edge.center[1]))
            x = round(px) + (app.video_label.winfo_width() - app.video_width) // 2
            y = round(py) + (app.video_label.winfo_height() - app.video_height) // 2
            before = app.detection
            app.video_label.event_generate("<ButtonPress-1>", x=x, y=y)
            app.video_label.event_generate("<ButtonRelease-1>", x=x, y=y)
            self.assertEqual(app.review_role.get(), role)
            self.assertEqual(app.detection, before)

    def test_group_drag_is_absolute_across_motion_events_and_clamps_as_a_group(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        original = app.detection.candidate(app.selections["Secondary edge"])
        observations = app.detection.observations
        app.confirmed = set(app.selections)
        for delta in ((10, 20), (15, 30), (15, 30)):
            app.move_review_candidate(original, delta, ())
        expected = (original.center[0] + 15, original.center[1] + 30)
        self.assertEqual({edge.center for edge in app.detection.candidates}, {expected})
        self.assertFalse(app.confirmed)
        self.assertEqual(app.detection.observations, observations)
        app.move_review_candidate(original, (-9999, 9999), ())
        self.assertEqual({edge.center for edge in app.detection.candidates}, {(0, 599)})
        for edge in app.detection.candidates:
            self.assertEqual(edge.axes[0], edge.axes[1])

    def test_hover_cursor_has_a_forgiving_margin_and_empty_space_drags_the_image(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.notebook.select(app.review_panel)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None and app.display_transform is not None)
        edge = app.detection.candidate(app.selections["Focuser edge"])
        transform = app.display_transform
        px, py = transform.to_display((edge.center[0] + edge.radius, edge.center[1]))
        offset = ((app.video_label.winfo_width() - app.video_width) // 2,
                  (app.video_label.winfo_height() - app.video_height) // 2)
        event = SimpleNamespace(x=round(px + 10) + offset[0], y=round(py) + offset[1])
        app.analysis_busy = True  # A tracking worker must not disable hover/grabbing.
        try:
            app.hover_image(event)
            self.assertEqual(app.video_label.cget("cursor"), "fleur")
            self.assertIsNotNone(app.circle_at(app.image_position(event)))
        finally:
            app.analysis_busy = False
        app.begin_blink()
        app.hover_image(event)
        self.assertEqual(app.video_label.cget("cursor"), "")
        app.end_blink()
        app.zoom_factor = 2
        self.wait_until(lambda: app.display_transform.crop_width == 400)
        transform = app.display_transform
        import math
        secondary = app.detection.candidate(app.selections["Secondary edge"])
        angle = math.radians(139.375)  # Halfway between old sampled rim points.
        radius = secondary.radius + 11 * transform.crop_width / transform.width
        near_rim = transform.to_display((secondary.center[0] + radius * math.cos(angle),
                                         secondary.center[1] + radius * math.sin(angle)))
        self.assertEqual(app.circle_at(near_rim)["edge"].id, secondary.id)
        point = next((x, y) for x in (20, 80, transform.width - 20)
                     for y in (20, 80, transform.height - 20) if app.circle_at((x, y)) is None)
        x = round(point[0]) + (app.video_label.winfo_width() - app.video_width) // 2
        y = round(point[1]) + (app.video_label.winfo_height() - app.video_height) // 2
        app.hover_image(SimpleNamespace(x=x, y=y))
        self.assertEqual(app.video_label.cget("cursor"), "")
        center = app.detection.guide_center
        start = SimpleNamespace(x=x, y=y, num=1)
        app.begin_pan(start)
        self.assertIsNone(app.circle_drag)
        app.pan_image(SimpleNamespace(x=x + 35, y=y + 20))
        app.end_pan(SimpleNamespace(x=x + 35, y=y + 20))
        self.assertIsNotNone(app.view_center)
        self.assertEqual(app.detection.guide_center, center)

    def test_clicked_circle_size_controls_and_control_wheel_preserve_group_and_reset(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.notebook.select(app.review_panel)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None and app.display_transform is not None)
        app.select_review_role("Secondary edge")
        before = app.detection
        secondary = before.candidate(app.selections["Secondary edge"])
        app.shrink_button.invoke()
        resized = app.detection.candidate(secondary.id)
        self.assertAlmostEqual(resized.radius, round(secondary.radius) - 1)
        self.assertEqual(resized.axes[0], resized.axes[1])
        self.assertEqual(app.detection.guide_center, before.guide_center)
        for edge in app.detection.candidates:
            if edge.id != secondary.id:
                self.assertEqual(edge.axes, before.candidate(edge.id).axes)
        self.assertEqual(app.manual_references["Secondary edge"].provenance, "manual_resize")
        original = next(edge for edge in before.observations if edge.id == secondary.id)
        self.assertEqual(app.manual_references["Secondary edge"].center, original.center)
        app.grow_button.invoke()
        resized = app.detection.candidate(secondary.id)
        self.assertGreater(resized.radius, round(secondary.radius) - 1)
        px, py = app.display_transform.to_display((resized.center[0] + resized.radius, resized.center[1]))
        x = round(px) + (app.video_label.winfo_width() - app.video_width) // 2
        y = round(py) + (app.video_label.winfo_height() - app.video_height) // 2
        app.zoom_with_scroll(SimpleNamespace(x=x, y=y, state=4, delta=-120))
        self.assertAlmostEqual(app.detection.candidate(secondary.id).radius, resized.radius - 1)
        app.zoom_with_scroll(SimpleNamespace(x=x, y=y, state=4, delta=-120))
        self.assertAlmostEqual(app.detection.candidate(secondary.id).radius, resized.radius - 2)
        self.assertEqual(app.zoom_factor, 1)
        app.zoom_with_scroll(SimpleNamespace(x=x, y=y, state=0, delta=120))
        self.assertGreater(app.zoom_factor, 1)
        with tempfile.TemporaryDirectory() as folder:
            image_path = app.export_capture(Path(folder) / "resized.png")
            metadata = image_path.with_suffix(".json")
            export = json.loads(metadata.read_text(encoding="utf-8"))
            self.assertEqual(export["manual_references"]["Secondary edge"]["provenance"], "manual_resize")
        app.set_review_radius(340)
        self.assertTrue(app.manual_references["Secondary edge"].clipped)
        app.set_review_radius(120)
        self.assertFalse(app.manual_references["Secondary edge"].clipped)
        from edge_tracking import merge_tracking
        fresh = replace(before, candidates=tuple(edge for edge in before.candidates if edge.id != secondary.id),
                        observations=tuple(edge for edge in before.observations if edge.id != secondary.id),
                        suggested={role: value for role, value in before.suggested.items() if role != "Secondary edge"})
        update = merge_tracking(app.detection, fresh, app.manual_references)
        self.assertIn("Secondary edge", update.held)
        self.assertEqual(update.result.candidate(update.selections["Secondary edge"]).radius,
                         app.detection.candidate(secondary.id).radius)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        self.assertFalse(app.manual_references)
        self.assertAlmostEqual(app.detection.candidate(app.selections["Secondary edge"]).radius, secondary.radius, delta=1)
        app.clear_reference()
        self.assertEqual(str(app.shrink_button.cget("state")), "disabled")

    def test_role_controls_match_circle_colors_and_keep_compact_layout(self):
        from feature_detection import FEATURE_NAMES, FEATURE_COLORS
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.notebook.select(app.review_panel)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        for role, color in zip(FEATURE_NAMES, FEATURE_COLORS):
            app.role_buttons[role].invoke()
            self.assertEqual(app.role_swatches[role].cget("background"), "#{:02x}{:02x}{:02x}".format(*color))
            self.assertEqual(app.role_buttons[role].cget("style"), app.role_styles[role])
            self.assertEqual(app.shrink_button.cget("style"), app.role_styles[role])
        for size in ("1280x720", "1024x768"):
            self.root.geometry(size)
            self.root.update()
            for widget in app.review_panel.winfo_children():
                if widget.winfo_ismapped():
                    self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                         self.root.winfo_rooty() + self.root.winfo_height())

    def test_radius_entry_accepts_exact_pixels_and_rejects_invalid_values_without_changes(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.notebook.select(app.review_panel)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        app.select_review_role("Secondary edge")
        center = app.detection.guide_center
        app.begin_radius_edit()
        app.radius_text.set("137")
        app.commit_review_radius()
        self.assertEqual(app.detection.candidate(app.selections["Secondary edge"]).axes, (137, 137))
        self.assertEqual(app.detection.guide_center, center)
        for invalid in ("", "NaN", "137.5", "-1", "0", "99999"):
            before = app.detection
            app.begin_radius_edit()
            app.radius_text.set(invalid)
            app.commit_review_radius()
            self.assertEqual(app.detection, before)
            self.assertTrue(app.radius_editing)
            self.assertIn("Radius", app.review_status.get())
            app.finish_radius_edit(restore=True)
            self.assertEqual(app.radius_text.get(), "137")
        app.resize_review_circle(-1)
        self.assertEqual(app.radius_text.get(), "136")
        app.resize_review_circle(1)
        self.assertEqual(app.radius_text.get(), "137")

    def test_radius_typing_pauses_tracking_until_commit_and_keeps_manual_radius(self):
        def factory(index):
            cap = FakeCapture(index, opened=index == 0)
            cap.frame = optical_fixture()
            return cap
        app = self.make_app(factory, live_tracking=True)
        self.wait_until(lambda: app.camera_on and app.last_frame is not None)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        app.select_review_role("Secondary edge")
        app.begin_radius_edit()
        app.radius_text.set("123")
        snapshot = app.last_frame.copy()
        generation = app.analysis_generation
        deadline = time.monotonic() + .6
        while time.monotonic() < deadline:
            self.root.update()
            time.sleep(.005)
        self.assertEqual(app.radius_text.get(), "123")
        self.assertEqual(app.analysis_generation, generation)
        np.testing.assert_array_equal(app.last_frame, snapshot)
        app.commit_review_radius()
        self.assertFalse(app.radius_editing)
        self.wait_until(lambda: app.analysis_generation > generation + 1)
        self.assertEqual(app.manual_references["Secondary edge"].radius, 123)
        app.begin_radius_edit()
        app.radius_text.set("99")
        app.end_pan()
        self.assertTrue(app.view_frozen)
        app.cancel_radius_edit()
        self.assertEqual(app.radius_text.get(), "123")
        self.assertFalse(app.view_frozen)
        app.begin_radius_edit()
        app.track_live.set(False)
        app.tracking_changed()
        app.cancel_radius_edit()
        self.assertFalse(app.view_frozen)
        self.assertFalse(app.radius_editing)

    def test_optional_mark_setup_and_manual_camera_pupil_keep_master_and_export(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False), saved_options=TelescopeProfile(center_mark_shape="None"))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.last_frame = optical_fixture()
        app.notebook.select(app.review_panel)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        self.assertNotIn("Center mark", app.selections)
        center = app.detection.guide_center
        app.role_buttons["Camera pupil"].invoke()
        app.begin_manual_pick()
        for point in ((390, 290), (410, 290), (400, 300)):
            app.pick_review_point(point)
        pupil_id = app.selections["Camera pupil"]
        self.assertEqual(app.detection.guide_center, center)
        self.assertEqual(app.manual_references["Camera pupil"].kind, "pupil_manual")
        self.assertIn("4 / 4 required circles present", app.review_progress.get())
        self.assertIn("Mark: absent", app.reference_summary.get())
        with tempfile.TemporaryDirectory() as folder:
            path = app.export_capture(Path(folder) / "pupil.png")
            metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["selections"]["Camera pupil"], pupil_id)
            self.assertEqual(metadata["telescope"]["center_mark_shape"], "None")
            self.assertTrue(metadata["alignment_advice"]["metrics"]["camera_pupil_present"])
        app.show_options()
        dialog = app.setup_dialog
        dialog.mark_shape.set("Unknown")
        dialog.save()
        self.assertEqual(app.options_store.load().center_mark_shape, "Unknown")

    def test_live_tracking_redraws_from_matching_analyzed_frames_and_can_pause(self):
        captures = []
        def factory(index):
            cap = FakeCapture(index, opened=index == 0)
            cap.frame = optical_fixture()
            captures.append(cap)
            return cap
        app = self.make_app(factory, live_tracking=True)
        self.wait_until(lambda: app.last_frame is not None)
        app.start_detection()
        self.wait_until(lambda: len(app.selections) == 4)
        self.assertTrue(app.tracking_active)
        self.assertFalse(app.view_frozen)
        shifted = cv2.warpAffine(optical_fixture(), np.float32([[1, 0, 12], [0, 1, 6]]), (800, 600),
                                 borderValue=(25, 25, 25))
        captures[-1].frame = shifted.copy()
        self.wait_until(lambda: app.detection.guide_center[0] > 410)
        np.testing.assert_array_equal(app.last_frame, shifted)
        self.assertEqual({edge.center for edge in app.detection.candidates}, {app.detection.guide_center})
        output = app.export_capture(app.options_store.path.with_name("tracked.png"))
        np.testing.assert_array_equal(cv2.imdecode(np.frombuffer(output.read_bytes(), np.uint8), 1), shifted)
        metadata = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertTrue(metadata["tracking"]["active"])
        self.assertNotIn("confirmed", metadata)
        app.track_live.set(False)
        app.tracking_changed()
        held = app.detection
        generation = app.analysis_generation
        session = app.session
        captures[-1].frame[:] = 0
        self.wait_until(lambda: not app.last_frame.any())
        deadline = time.monotonic() + .6
        self.wait_until(lambda: time.monotonic() >= deadline)
        self.assertEqual(app.analysis_generation, generation)
        self.assertEqual(app.detection, held)
        self.assertFalse(app.view_frozen)
        self.assertTrue(app.camera_on)
        self.assertIn("live image continues", app.next_step.get())
        output = app.export_capture(app.options_store.path.with_name("paused.png"))
        self.assertFalse(cv2.imdecode(np.frombuffer(output.read_bytes(), np.uint8), 1).any())
        paused = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertFalse(paused["observations_match_image"])
        self.assertIsNone(paused["alignment_advice"])
        captures[-1].frame = shifted.copy()
        app.track_live.set(True)
        app.tracking_changed()
        self.wait_until(lambda: app.analysis_generation > generation + 1 and app.observations_current and app.last_frame.any())
        self.assertEqual(app.session, session)
        self.assertEqual(app.selected_camera.get(), "Camera 0")
        self.assertTrue(app.observations_current)
        self.assertEqual(set(app.selections), set(held.suggested))

    def test_live_manual_circle_survives_loss_moves_with_master_and_reacquires(self):
        captures = []
        def factory(index):
            cap = FakeCapture(index, opened=index == 0)
            cap.frame = optical_fixture()
            captures.append(cap)
            return cap
        app = self.make_app(factory, live_tracking=True)
        self.wait_until(lambda: app.last_frame is not None)
        app.start_detection()
        self.wait_until(lambda: len(app.selections) == 4)
        master = app.detection.guide_center
        app.select_review_role("Secondary edge")
        app.begin_manual_pick()
        self.assertTrue(app.view_frozen)
        for point in ((612, 296), (412, 496), (212, 296)):
            app.pick_review_point(point)
        self.assertEqual(app.detection.guide_center, master)
        self.assertFalse(app.view_frozen)
        missing = np.full((600, 800, 3), 25, np.uint8)
        cv2.circle(missing, (410, 300), 250, (120,) * 3, -1, cv2.LINE_AA)
        cv2.circle(missing, (428, 300), 160, (190,) * 3, -1, cv2.LINE_AA)
        cv2.circle(missing, (431, 302), 10, (20,) * 3, -1, cv2.LINE_AA)
        captures[-1].frame = missing
        self.wait_until(lambda: "Secondary edge" in app.tracking_held and app.detection.guide_center[0] > 408)
        self.assertAlmostEqual(app.detection.candidate(app.selections["Secondary edge"]).radius, 200, delta=2)
        self.assertEqual({edge.center for edge in app.detection.candidates}, {app.detection.guide_center})
        self.assertEqual(app.alignment.stage, "capture")
        restored = cv2.warpAffine(optical_fixture(), np.float32([[1, 0, 10], [0, 1, 0]]), (800, 600),
                                  borderValue=(25, 25, 25))
        captures[-1].frame = restored
        self.wait_until(lambda: "Secondary edge" not in app.tracking_held)
        self.assertIsNotNone(app.manual_references["Secondary edge"].fit_quality)
        np.testing.assert_array_equal(app.last_frame, restored)

    def test_tracking_has_one_worker_and_discards_inflight_result_during_pick(self):
        from feature_detection import analyze_frame as real_analysis
        app = self.make_app(lambda index: FakeCapture(index, opened=index == 0), live_tracking=True)
        self.wait_until(lambda: app.last_frame is not None)
        app.last_frame = optical_fixture()
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        app.track_live.set(False)
        app.tracking_changed()
        self.wait_until(lambda: not app.analysis_busy)
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        active = [0, 0]
        lock = threading.Lock()
        def delayed(frame, shape):
            with lock:
                active[0] += 1
                active[1] = max(active[1], active[0])
            entered.set()
            release.wait(2)
            result = real_analysis(frame, shape)
            with lock:
                active[0] -= 1
            return result
        with patch("collimation_review.analyze_frame", side_effect=delayed):
            app.track_live.set(True)
            app.tracking_changed()
            self.wait_until(entered.is_set)
            before = app.detection
            app.select_review_role("Center mark")
            app.begin_manual_pick()
            for _ in range(4):
                app.tracking_pending_frame = optical_fixture()
                app.maybe_track()
            release.set()
            self.wait_until(lambda: not app.analysis_busy)
            self.assertEqual(app.detection, before)
            self.assertTrue(app.view_frozen)
            self.assertEqual(active[1], 1)
            app.cancel_pick()
            app.track_live.set(False)
            app.tracking_changed()

    def test_capture_advice_remains_readable_and_reports_candidates(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.notebook.select(app.review_panel)
        app.last_frame = cv2.GaussianBlur(optical_fixture(), (0, 0), 10)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None)
        self.assertIn("Improve camera focus", app.review_status.get())
        self.assertLess(len(app.review_status.get()), 200)
        for size in ("1280x720", "1024x768"):
            self.root.geometry(size)
            self.root.update()
            self.assertEqual(app.advice_label.winfo_height(), app.advice_label.winfo_reqheight())
            for widget in app.review_panel.winfo_children():
                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                     self.root.winfo_rooty() + self.root.winfo_height())
        self.assertIn("circles present", app.review_progress.get())
        self.assertFalse(app.confirmed)
        for role in ("Focuser edge", "Secondary edge", "Primary reflection", "Center mark"):
            app.review_role.set(role)
            app.review_role_changed()
            self.assertTrue(app.selection_status.get())


if __name__ == "__main__":
    unittest.main()
