"""Application workflows using real Tk, analysis, tracking and file exports.

Capture substitutes represent the hardware boundary. No detector, averaging,
tracking or guidance implementation is mocked by these workflows.
"""

import json
from pathlib import Path
import time
from unittest.mock import patch

import cv2
import numpy as np

from source.app_options import TelescopeProfile
from tests.fixtures.camera import FakeCapture
from tests.integration.test_app import GuiTests
from tests.fixtures.images import TEST_IMAGES, optical_fixture, pupil_fixture


class WorkflowTests(GuiTests):
    def wait_until(self, predicate):
        # Complete native-photo and noisy camera workflows may include a full
        # recognition fallback. Allow that work without weakening assertions.
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            self.root.update()
            if predicate():
                return
            time.sleep(.005)
        self.fail("Timed out waiting for complete application workflow")

    def open_detect_export(self, frame):
        path = self.app.options_store.path.with_name("workflow-é.png")
        ok, encoded = cv2.imencode(".png", frame)
        self.assertTrue(ok)
        path.write_bytes(encoded.tobytes())
        self.app.load_image(path)
        self.wait_until(lambda: str(self.app.detect_button.cget("state")) == "normal")
        self.app.detect_button.invoke()
        self.wait_until(lambda: self.app.detection is not None and not self.app.analysis_busy)
        output = self.app.export_capture(path.with_name("export.png"))
        np.testing.assert_array_equal(cv2.imdecode(np.frombuffer(output.read_bytes(), np.uint8), 1), frame)
        metadata = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertTrue(metadata["observations_match_image"])
        self.assertIsNotNone(self.app.video_label.image)
        self.assertEqual(len(set(self.app.selections.values())), len(self.app.selections))
        if self.app.detection.candidates:
            self.assertEqual({edge.center for edge in self.app.detection.candidates}, {self.app.detection.guide_center})
            self.assertTrue(all(edge.axes[0] == edge.axes[1] for edge in self.app.detection.candidates))
        return self.app.detection, metadata

    def test_detection_import_review_export_quality_and_identity(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False),
                            saved_options=TelescopeProfile(center_mark_shape="Ring"))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.notebook.select(app.review_panel)
        for size in ((800, 600), (2400, 1800)):
            with self.subTest(size=size):
                result, metadata = self.open_detect_export(pupil_fixture(size))
                self.assertEqual(len(app.selections), 5)
                raw = {edge.id: edge for edge in result.observations}
                pupil, mark = (raw[app.selections[role]] for role in ("Camera pupil", "Center mark"))
                scale = size[0] / 800
                np.testing.assert_allclose(pupil.center, np.array((405, 285)) * scale, atol=3 * scale)
                np.testing.assert_allclose(mark.center, np.array((447, 330)) * scale, atol=3 * scale)
                self.assertLess(pupil.radius, 20 * scale)
                self.assertNotEqual(mark.id, pupil.id)
                self.assertGreater(len({edge.center for edge in result.observations}), 1)
                self.assertEqual(metadata["image_size"], list(size))
        scenes = {
            "blank": np.full((300, 400, 3), 90, np.uint8),
            "noise": np.random.default_rng(54).integers(0, 256, (300, 400, 3), dtype=np.uint8),
            "soft": cv2.GaussianBlur(optical_fixture(), (0, 0), 10),
            "dim": (optical_fixture().astype(float) * .25).astype(np.uint8),
            "clipped": optical_fixture()[:, 200:],
            "shadow only": pupil_fixture(mark=False, opening=False),
        }
        for name, frame in scenes.items():
            with self.subTest(scene=name):
                result, metadata = self.open_detect_export(frame)
                self.assertEqual(app.alignment.stage, "capture")
                if name in ("blank", "noise"):
                    self.assertFalse(app.selections)
                if name == "clipped":
                    raw = next(edge for edge in result.observations if edge.id == app.selections["Focuser edge"])
                    self.assertTrue(raw.clipped)
                    self.assertEqual(raw.axes[0], raw.axes[1])
                if name == "shadow only":
                    self.assertNotIn("Camera pupil", app.selections)
                if name == "dim":
                    self.assertTrue({"Focuser edge", "Secondary edge", "Primary reflection"} <= set(app.selections))
                self.assertTrue(metadata["alignment_advice"]["instruction"])

    def test_setup_atomic_failure_and_invalid_edits_preserve_saved_file(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False),
                            saved_options=TelescopeProfile(name="Original", aperture_mm=130))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        before = app.options_store.path.read_bytes()
        app.show_options()
        dialog = app.setup_dialog
        for field, value in (("aperture_mm", "0"), ("aperture_mm", "True"),
                             ("focal_length_mm", "nan"), ("focal_length_mm", "inf"),
                             ("secondary_minor_axis_mm", "140"), ("secondary_offset_mm", "-1")):
            with self.subTest(field=field, value=value):
                old = dialog.variables[field].get()
                dialog.variables[field].set(value)
                dialog.save()
                self.assertTrue(dialog.error.get())
                self.assertTrue(dialog.winfo_exists())
                self.assertEqual(app.options_store.path.read_bytes(), before)
                dialog.variables[field].set(old)
        dialog.variables["name"].set("New é")
        with patch("source.app_options.os.replace", side_effect=PermissionError("Locked file")):
            dialog.save()
        self.assertIn("Locked", dialog.error.get())
        self.assertEqual(app.options_store.path.read_bytes(), before)
        self.assertEqual(list(app.options_store.path.parent.glob(".options-*.tmp")), [])
        dialog.save()
        self.assertEqual(app.profile.name, "New é")
        self.assertFalse(app.options_store.path.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertIsNone(app.profile.secondary_offset_mm)

    def test_legacy_options_are_loaded_and_resaved_by_setup_without_eccentricity(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False), saved_options=
                            b'{"schema_version":1,"telescope":{"name":"Older scope","max_eccentricity":0.85}}')
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        self.assertEqual(app.profile.name, "Older scope")
        app.show_options()
        app.setup_dialog.save()
        self.assertNotIn(b"max_eccentricity", app.options_store.path.read_bytes())

    def test_future_options_are_reported_without_overwrite(self):
        original = b'{"schema_version":2,"telescope":{}}'
        app = self.make_app(lambda index: FakeCapture(index, opened=False), saved_options=original)
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        self.assertTrue(app.options_error)
        self.assertEqual(app.options_store.path.read_bytes(), original)

    def test_native_photos_import_detect_render_and_export_observed_rims(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False),
                            saved_options=TelescopeProfile(center_mark_shape="Ring"))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        app.notebook.select(app.review_panel)
        expected = {
            "images.jpg": {"Focuser edge": (215, 15), "Secondary edge": (127, 13), "Primary reflection": (95, 10)},
            "image.jpg": {"Focuser edge": (515, 45), "Secondary edge": (295, 25), "Primary reflection": (210, 20)},
            "collimating-newtonian-secondary.jpg": {"Focuser edge": (210, 8), "Secondary edge": (164, 8), "Primary reflection": (139, 8)},
            "post-330586-0-86207400-1592443472.jpg": {"Focuser edge": (351, 8), "Secondary edge": (232, 8), "Primary reflection": (206, 8)},
            "post-474648-0-99865000-1758374870.jpg": {"Focuser edge": (401, 8), "Primary reflection": (171, 8)},
            "images (1).jpg": {"Focuser edge": (74, 4), "Primary reflection": (55, 3)},
            "2.png": {"Primary reflection": (396, 8)},
            "post-333184-0-47945200-1591447543.jpeg": {"Focuser edge": (145, 3)},
        }
        checked = 0
        for path in sorted(TEST_IMAGES.iterdir()):
            if path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                continue
            with self.subTest(photo=path.name):
                frame = cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), 1)
                result, metadata = self.open_detect_export(frame)
                self.assertTrue(result.candidates)
                raw = {edge.id: edge for edge in result.observations}
                for role, (radius, tolerance) in expected.get(path.name, {}).items():
                    self.assertAlmostEqual(raw[app.selections[role]].radius, radius, delta=tolerance)
                if path.name in ("post-474648-0-99865000-1758374870.jpg", "images (1).jpg", "2.png",
                                  "post-333184-0-47945200-1591447543.jpeg"):
                    self.assertNotIn("Secondary edge", app.selections)
                if path.name == "2.png":
                    self.assertNotIn("Focuser edge", app.selections)
                if path.name == "post-330586-0-86207400-1592443472.jpg":
                    self.assertGreaterEqual(raw[app.selections["Focuser edge"]].edge_width, 14)
                if path.name == "images.jpg":
                    self.assertFalse(any(edge.radius < 60 and edge.center[1] > 260 for edge in result.observations))
                self.assertEqual(metadata["analysis"], {"mode": "full", "averaged_frames": 1})
                checked += 1
        self.assertEqual(checked, 14)

    def test_live_local_tracking_averages_steady_frames_and_exports_matching_pixels(self):
        captures = []
        rng = np.random.default_rng(9)
        original = pupil_fixture()

        class NoisyCapture(FakeCapture):
            def read(self):
                ok, frame = super().read()
                if ok:
                    frame = np.clip(frame.astype(np.int16) + rng.integers(-4, 5, frame.shape), 0, 255).astype(np.uint8)
                return ok, frame

        def factory(index):
            cap = NoisyCapture(index, opened=index == 0)
            cap.frame = original.copy()
            captures.append(cap)
            return cap

        app = self.make_app(factory, live_tracking=True, saved_options=TelescopeProfile(center_mark_shape="Ring"))
        # Keep rendering inexpensive enough for three UI-delivered captures to
        # fit inside the production 120 ms age bound on this test machine.
        self.root.geometry("900x700")
        self.wait_until(lambda: app.last_frame is not None)
        app.detect_button.invoke()
        try:
            self.wait_until(lambda: len(app.selections) == 5 and app.analysis_mode == "local" and app.averaged_frames == 3)
        except AssertionError:
            self.fail(f"Live workflow: roles={app.selections}, mode={app.analysis_mode}, "
                      f"samples={app.averaged_frames}, buffer={len(app.live_average.frames)}, "
                      f"status={app.review_status.get()}")
        app.track_live.set(False)
        app.tracking_changed()
        # Export immediately on the owning Tk thread, before raw preview advances.
        snapshot = app.last_frame.copy()
        output = app.export_capture(app.options_store.path.with_name("averaged.png"))
        np.testing.assert_array_equal(cv2.imdecode(np.frombuffer(output.read_bytes(), np.uint8), 1), snapshot)
        metadata = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["analysis"], {"mode": "local", "averaged_frames": 3})
        self.assertTrue(metadata["observations_match_image"])
        self.assertLess(float(np.mean((snapshot.astype(float) - original) ** 2)), 7)
        app.track_live.set(True)
        app.tracking_changed()
        self.wait_until(lambda: app.analysis_mode == "local" and app.observations_current)
        app.begin_radius_edit()
        self.assertFalse(app.live_average.frames)
        app.finish_radius_edit(restore=True)
        app.track_live.set(False)
        app.tracking_changed()
        self.assertFalse(app.live_average.frames)

    def test_live_lost_edges_force_full_search_and_recover_from_latest_frame(self):
        captures = []
        def factory(index):
            cap = FakeCapture(index, opened=index == 0)
            cap.frame = pupil_fixture()
            captures.append(cap)
            return cap
        app = self.make_app(factory, live_tracking=True, saved_options=TelescopeProfile(center_mark_shape="Ring"))
        self.wait_until(lambda: app.last_frame is not None)
        app.detect_button.invoke()
        self.wait_until(lambda: app.analysis_mode == "local")
        captures[-1].frame = np.full((600, 800, 3), 25, np.uint8)
        self.wait_until(lambda: app.analysis_mode == "full" and not app.selections)
        self.assertEqual(app.alignment.stage, "capture")
        self.assertLessEqual(app.worker.frames.qsize(), 1)
        captures[-1].frame = cv2.warpAffine(pupil_fixture(), np.float32([[1, 0, 8], [0, 1, 4]]),
                                            (800, 600), borderValue=(25, 25, 25))
        self.wait_until(lambda: len(app.selections) == 5 and app.detection.guide_center[0] > 406)
        self.wait_until(lambda: app.analysis_mode == "local")
        self.assertEqual(len(set(app.selections.values())), 5)
        np.testing.assert_array_equal(app.last_frame, captures[-1].frame)

    def test_scaled_camera_references_track_after_small_mirror_motion(self):
        captures = []
        original = pupil_fixture((1600, 1200))
        def factory(index):
            cap = FakeCapture(index, opened=index == 0)
            cap.frame = original.copy()
            captures.append(cap)
            return cap
        app = self.make_app(factory, live_tracking=True, saved_options=TelescopeProfile(center_mark_shape="Ring"))
        self.wait_until(lambda: app.last_frame is not None)
        app.start_detection()
        self.wait_until(lambda: app.analysis_mode == "local" and len(app.selections) == 5)
        self.assertEqual(app.detection.image_size, (1600, 1200))
        captures[-1].frame = cv2.warpAffine(original, np.float32([[1, 0, 4], [0, 1, 2]]),
                                            (1600, 1200), borderValue=(25, 25, 25))
        self.wait_until(lambda: app.detection.guide_center[0] > 802 and app.analysis_mode == "local")
        raw = {edge.id: edge for edge in app.detection.observations}
        np.testing.assert_allclose(raw[app.selections["Camera pupil"]].center, (814, 572), atol=5)
        np.testing.assert_allclose(raw[app.selections["Center mark"]].center, (898, 662), atol=5)
        self.assertEqual(len(set(app.selections.values())), 5)
