import threading
import time
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np
from PIL import ImageTk

from astro_collimator import CameraWorker, WebcamApp, prepare_frame
from camera_properties import PropertyInfo


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
    def make_app(self, factory, capabilities=None):
        root = tk.Tk()
        # Map widgets invisibly so Tk exercises real Scale idle callbacks.
        root.attributes("-alpha", 0.0)
        self.root = root
        self.callback_errors = []
        root.report_callback_exception = lambda *error: self.callback_errors.append(error)
        with patch("astro_collimator.open_camera", side_effect=factory), \
                patch("astro_collimator.query_camera_properties", return_value=capabilities or {}):
            self.app = WebcamApp(root)
        self.addCleanup(self.close_app)
        return self.app

    def close_app(self):
        if not self.app.closing:
            self.app.on_closing()
        self.app.worker.join(2)
        self.assertFalse(self.app.worker.is_alive())
        self.assertEqual(self.callback_errors, [])

    def wait_until(self, predicate):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            self.root.update()
            if predicate():
                return
            time.sleep(0.005)
        self.fail("Timed out waiting for UI state")

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
        self.assertEqual((app.video_width, app.video_height), (960, 540))
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
        self.assertEqual((app.crosshair_x, app.crosshair_y), (959, 539))
        app.reset_crosshair()
        self.assertEqual((app.crosshair_x, app.crosshair_y), (480, 270))
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


if __name__ == "__main__":
    unittest.main()
