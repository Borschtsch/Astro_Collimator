"""Application workflows using real Tk, analysis, tracking and file exports.

Capture substitutes represent the hardware boundary. No detector, averaging,
tracking or guidance implementation is mocked by these workflows.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
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

    def test_linux_wheel_events_adjust_controls_zoom_and_circle_radius(self):
        from source.camera_properties import PropertyInfo
        captures = []

        def factory(index):
            cap = FakeCapture(index, opened=index == 0)
            cap.values[cv2.CAP_PROP_GAIN] = 7
            captures.append(cap)
            return cap

        app = self.make_app(factory, {"Gain": PropertyInfo("supported", 3, 19, 4, 7, 2)})
        self.wait_until(lambda: app.last_frame is not None)
        gain = app.camera_controls[cv2.CAP_PROP_GAIN]
        gain.slider.event_generate("<Button-4>")
        self.wait_until(lambda: captures[-1].set_calls == [(cv2.CAP_PROP_GAIN, 11)])
        gain.slider.event_generate("<Button-5>")
        self.wait_until(lambda: len(captures[-1].set_calls) == 2)
        self.assertEqual(captures[-1].set_calls[-1], (cv2.CAP_PROP_GAIN, 7))
        self.assertEqual(app.zoom_factor, 1)
        self.wait_until(lambda: app.display_transform is not None)
        app.video_label.event_generate("<Button-4>", x=400, y=300)
        self.assertAlmostEqual(app.zoom_factor, 1.1)
        app.video_label.event_generate("<Button-5>", x=400, y=300)
        self.assertAlmostEqual(app.zoom_factor, 1)
        self.open_detect_export(pupil_fixture())
        app.notebook.select(app.review_panel)
        app.role_buttons["Primary reflection"].invoke()
        self.root.update()
        radius = app.detection.candidate(app.selections["Primary reflection"]).radius
        app.grow_button.event_generate("<Button-4>")
        self.assertEqual(app.detection.candidate(app.selections["Primary reflection"]).radius, round(radius) + 1)
        app.shrink_button.event_generate("<Button-5>")
        self.assertEqual(app.detection.candidate(app.selections["Primary reflection"]).radius, round(radius))
        app.notebook.select(app.manual_panel)
        self.root.update()
        ring = app.ring_controls[0]
        radius = ring.slider.get()
        ring.slider.event_generate("<Button-5>")
        self.assertEqual(ring.slider.get(), radius - 1)
        ring.slider.event_generate("<Button-4>")
        self.assertEqual(ring.slider.get(), radius)

    def test_linux_native_query_scan_stream_control_switch_and_export(self):
        import threading
        from tests.fixtures.linux_camera import LinuxCameraHardware
        with LinuxCameraHardware() as hardware:
            app = self.make_app(None, native_camera=True)
            try:
                self.wait_until(lambda: app.last_frame is not None)
                self.assertEqual(app.camera_list, ["Astro Camera (Camera 2)", "Astro Camera (Camera 14)"])
                gain = app.camera_controls[cv2.CAP_PROP_GAIN]
                self.assertEqual((gain.slider.cget("from"), gain.slider.cget("to")), (3, 19))
                self.assertEqual(gain.slider.get(), 7)
                self.assertFalse(app.camera_controls[cv2.CAP_PROP_EXPOSURE].enabled)
                self.assertEqual(app.camera_controls[cv2.CAP_PROP_EXPOSURE].info.status, "unsupported")
                self.assertEqual(app.camera_controls[cv2.CAP_PROP_ZOOM].info.status, "unknown")
                self.assertFalse(app.camera_controls[cv2.CAP_PROP_FOCUS].enabled)
                self.assertEqual(app.camera_controls[cv2.CAP_PROP_FOCUS].note.cget("text"), "Automatic only")
                self.assertTrue(all(cap.set_calls == [(cv2.CAP_PROP_MODE, 0)] for cap in hardware.captures))
                gain.slider.event_generate("<Button-4>")
                self.wait_until(lambda: len(hardware.captures[-1].set_calls) == 2)
                self.assertEqual(hardware.captures[-1].set_calls[-1], (cv2.CAP_PROP_GAIN, 11))
                app.selected_camera.set("Astro Camera (Camera 14)")
                app.camera_dropdown.event_generate("<<ComboboxSelected>>")
                self.wait_until(lambda: app.camera_controls[cv2.CAP_PROP_GAIN].info.status == "unknown" and app.last_frame is not None)
                self.assertTrue(gain.enabled)  # malformed driver range keeps numeric fallback
                self.assertTrue(hardware.queries)
                self.assertTrue(all(owner != threading.get_ident() for _, _, owner in hardware.queries))
                self.assertEqual(hardware.closed, [100002, 100014])
                self.open_detect_export(pupil_fixture())
                self.assertIn("Camera pupil", app.selections)
            finally:
                app.on_closing()
                app.worker.join(3)
            self.assertTrue(all(cap.released for cap in hardware.captures))

    def test_linux_query_permission_failure_keeps_stream_and_numeric_controls(self):
        from tests.fixtures.linux_camera import LinuxCameraHardware
        with LinuxCameraHardware(permission_denied=True) as hardware:
            app = self.make_app(None, native_camera=True)
            try:
                self.wait_until(lambda: app.last_frame is not None)
                for control in app.camera_controls.values():
                    self.assertEqual(control.info.status, "unknown")
                    self.assertTrue(control.enabled)
                self.assertFalse(hardware.queries)
                self.open_detect_export(pupil_fixture())
                self.assertIn("Camera pupil", app.selections)
            finally:
                app.on_closing()
                app.worker.join(3)
            self.assertTrue(all(cap.released for cap in hardware.captures))

    def test_source_launcher_preserves_explicit_interpreter_from_another_directory(self):
        from tests.fixtures.source_checkout import source_checkout, launch_directory
        with launch_directory() as folder:
            checkout, interpreter = source_checkout(folder)
            report = Path(folder) / "source.json"
            subprocess.run([str(interpreter), str(checkout / "start.py"), "--smoke-test", "--report", str(report)],
                           cwd=folder, check=True, timeout=45)
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "passed")
            self.assertTrue(result["virtual_environment"])
            self.assertEqual(Path(result["python_executable"]), interpreter)
            self.assertEqual(Path(result["settings_path"]), checkout / "options.json")
            self.assertIn("matched raw PNG and JSON export", result["checks"])
            self.assertFalse((checkout / "options.json").exists())

    def test_source_launcher_reports_missing_dependencies_without_silent_exit(self):
        from tests.fixtures.source_checkout import source_checkout, launch_directory
        with launch_directory() as folder:
            checkout, interpreter = source_checkout(folder, dependencies=False)
            completed = subprocess.run([str(interpreter), str(checkout / "start.py"), "--smoke-test"],
                                       cwd=folder, capture_output=True, text=True, encoding="utf-8",
                                       env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=30)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("could not start", completed.stderr)
            self.assertIn("Install the application dependencies", completed.stderr)
            for dependency in ("numpy", "opencv-python", "Pillow", "qrcode", "cryptography", "pillow-heif"):
                self.assertIn(dependency, completed.stderr)
            self.assertIn("Required runtime checks failed", completed.stderr)
            log = checkout / "build" / "startup-error.log"
            self.assertTrue(log.is_file())
            self.assertIn("ModuleNotFoundError", log.read_text(encoding="utf-8"))
            self.assertIn("Interpreter: " + str(interpreter), log.read_text(encoding="utf-8"))
            self.assertIn("Interpreter: " + str(interpreter), completed.stderr)
            self.assertFalse((checkout / "options.json").exists())

    def test_source_launcher_rejects_missing_phone_packages_and_broken_native_codec_then_recovers(self):
        from tests.fixtures.source_checkout import source_checkout, launch_directory, copy_runtime_packages
        with launch_directory() as folder:
            checkout, interpreter = source_checkout(folder, dependencies=False)
            copy_runtime_packages(interpreter, ("numpy", "cv2", "PIL"))
            report = Path(folder) / "dependencies.json"
            command = [str(interpreter), "-B", str(checkout / "start.py"),
                       "--smoke-test", "--report", str(report)]
            environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
            missing = subprocess.run(command, cwd=folder, capture_output=True, text=True,
                                     encoding="utf-8", env=environment, timeout=30)
            self.assertEqual(missing.returncode, 1, missing.stderr)
            for dependency in ("qrcode", "cryptography / HTTPS", "pillow-heif"):
                self.assertIn(dependency + ": ModuleNotFoundError", missing.stderr)
            self.assertNotIn("opencv-python:", missing.stderr)
            self.assertFalse(report.exists())
            self.assertFalse((checkout / "options.json").exists())
            packages = copy_runtime_packages(interpreter,
                ("qrcode", "cryptography", "pillow_heif", "_pillow_heif", "_cffi_backend", "cffi", "pycparser"))
            # Remove only this isolated installation's actual binary extension.
            binaries = list(packages.glob("_pillow_heif*.pyd")) + list(packages.glob("_pillow_heif*.so"))
            self.assertTrue(binaries)
            binary = binaries[0]
            disabled = binary.with_name(binary.name + ".disabled")
            binary.rename(disabled)
            broken = subprocess.run(command, cwd=folder, capture_output=True, text=True,
                                    encoding="utf-8", env=environment, timeout=30)
            self.assertEqual(broken.returncode, 1, broken.stderr)
            self.assertIn("pillow-heif:", broken.stderr)
            self.assertNotIn("qrcode:", broken.stderr)
            self.assertNotIn("cryptography / HTTPS:", broken.stderr)
            self.assertIn("Interpreter: " + str(interpreter), broken.stderr)
            self.assertFalse(report.exists())
            self.assertFalse((checkout / "phone-link").exists())
            disabled.rename(binary)
            repaired = subprocess.run(command, cwd=folder, capture_output=True, text=True,
                                      encoding="utf-8", env=environment, timeout=45)
            self.assertEqual(repaired.returncode, 0, repaired.stderr)
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "passed")
            self.assertIn("matched raw PNG and JSON export", result["checks"])
            self.assertFalse((checkout / "options.json").exists())

    @unittest.skipUnless(sys.platform == "win32", "Windows process paths")
    def test_source_startup_repairs_windows_paths_without_literal_cache_folders(self):
        from tests.fixtures.source_checkout import source_checkout, launch_directory
        names = ("SystemDrive", "SystemRoot", "WINDIR", "ProgramData", "ALLUSERSPROFILE")
        project = Path(__file__).resolve().parents[2]
        with launch_directory() as folder:
            checkout, interpreter = source_checkout(folder)
            environment = dict(os.environ)
            for key in list(environment):
                if key.lower() in {name.lower() for name in names}:
                    environment.pop(key)
            environment["ProgramData"] = "%SystemDrive%/ProgramData"
            environment["WINDIR"] = "%SystemDrive%/Windows"
            driver = (
                "import json,os,sys; from pathlib import Path; "
                "sys.path.insert(0,sys.argv[1]); from source.bootstrap import launch; "
                "result=launch(['--smoke-test','--report',sys.argv[2]]); "
                "Path(sys.argv[3]).write_text(json.dumps({k:os.environ.get(k) for k in "
                "('SystemDrive','SystemRoot','WINDIR','ProgramData','ALLUSERSPROFILE')}),encoding='utf-8'); "
                "sys.exit(result)"
            )
            for case in ("incomplete", "preserved"):
                with self.subTest(case=case):
                    report = Path(folder) / (case + ".json")
                    paths = Path(folder) / (case + "-paths.json")
                    if case == "preserved":
                        shared = Path(folder) / "Caller data"
                        shared.mkdir()
                        environment.update(resolved)
                        environment["ProgramData"] = str(shared)
                        environment["ALLUSERSPROFILE"] = str(shared)
                    child = subprocess.run(
                        [str(interpreter), "-B", "-c", driver, str(checkout), str(report), str(paths)],
                        cwd=folder, env=environment, capture_output=True, text=True, timeout=60)
                    self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
                    result = json.loads(report.read_text(encoding="utf-8"))
                    self.assertEqual(result["status"], "passed")
                    self.assertIn("Tk rendering", result["checks"])
                    self.assertIn("matched raw PNG and JSON export", result["checks"])
                    resolved = json.loads(paths.read_text(encoding="utf-8"))
                    self.assertEqual(len(resolved["SystemDrive"]), 2)
                    self.assertTrue(resolved["SystemDrive"].endswith(":"))
                    for name in names[1:]:
                        self.assertTrue(Path(resolved[name]).is_absolute(), resolved)
                        self.assertNotIn("%", resolved[name])
                    if case == "preserved":
                        self.assertEqual(resolved["ProgramData"], str(shared))
                        self.assertEqual(resolved["ALLUSERSPROFILE"], str(shared))
                    self.assertFalse(list(Path(folder).rglob("%SystemDrive%")))
                    self.assertFalse((project / "%SystemDrive%").exists())

    @unittest.skipUnless(sys.platform == "win32", "Windows Explorer file association")
    def test_explorer_uses_associated_python_without_switching_to_local_venv(self):
        from tests.fixtures.source_checkout import source_checkout, launch_directory
        with launch_directory() as folder:
            checkout, interpreter = source_checkout(folder, dependencies=False)
            for entry in ("start.py",):
                with self.subTest(entry=entry):
                    report = Path(folder) / (entry + ".json")
                    arguments = '--smoke-test --report "' + str(report) + '"'
                    os.startfile(str(checkout / entry), "open", arguments, folder)
                    deadline = time.monotonic() + 45
                    while not report.exists() and time.monotonic() < deadline:
                        time.sleep(.05)
                    self.assertTrue(report.exists(), "Explorer launch did not produce the app report")
                    result = json.loads(report.read_text(encoding="utf-8"))
                    # The report is written after app shutdown, just before the
                    # interpreter exits. Wait for this owned child before venv cleanup.
                    import ctypes as ct
                    kernel = ct.WinDLL("kernel32", use_last_error=True)
                    kernel.OpenProcess.argtypes = (ct.c_uint32, ct.c_int, ct.c_uint32)
                    kernel.OpenProcess.restype = ct.c_void_p
                    kernel.WaitForSingleObject.argtypes = (ct.c_void_p, ct.c_uint32)
                    kernel.WaitForSingleObject.restype = ct.c_uint32
                    kernel.CloseHandle.argtypes = (ct.c_void_p,)
                    handle = kernel.OpenProcess(0x00100000, False, result["process_id"])
                    if handle:
                        try:
                            self.assertEqual(kernel.WaitForSingleObject(handle, 10000), 0)
                        finally:
                            kernel.CloseHandle(handle)
                    self.assertEqual(result["status"], "passed")
                    self.assertNotEqual(Path(result["python_executable"]), interpreter)
                    self.assertEqual(Path(result["python_executable"]).name.lower(), "python.exe")
                    self.assertTrue(result["console_attached"])
                    self.assertFalse(result["console_window_visible"])
                    self.assertIn("Tk rendering", result["checks"])
                    self.assertIn("matched raw PNG and JSON export", result["checks"])
                    self.assertFalse((checkout / "options.json").exists())

    @unittest.skipUnless(sys.platform == "win32", "Windows shared console")
    def test_source_launcher_preserves_console_shared_with_another_process(self):
        from tests.fixtures.source_checkout import source_checkout, launch_directory
        with launch_directory() as folder:
            checkout, interpreter = source_checkout(folder)
            report = checkout / "shared-console.json"
            helper = checkout / "terminal_parent.py"
            helper.write_text(
                "import subprocess, sys\n"
                "raise SystemExit(subprocess.call([sys.executable, 'start.py', "
                "'--smoke-test', '--report', 'shared-console.json']))\n",
                encoding="utf-8")
            # An actual parent and app share a new native console. Do not mock
            # console ownership or visibility; run the complete app workflow.
            subprocess.run([str(interpreter), str(helper)], cwd=checkout,
                           creationflags=subprocess.CREATE_NEW_CONSOLE, check=True, timeout=45)
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "passed")
            self.assertEqual(Path(result["python_executable"]), interpreter)
            self.assertTrue(result["console_window_visible"])
            self.assertIn("Tk rendering", result["checks"])
            self.assertIn("matched raw PNG and JSON export", result["checks"])
            self.assertFalse((checkout / "options.json").exists())

    def test_opened_image_wheel_zoom_and_margin_pan_preserve_optical_geometry(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        self.open_detect_export(optical_fixture())
        app.notebook.select(app.review_panel)
        self.wait_until(lambda: app.display_transform is not None)
        detection = app.detection
        raw = app.last_frame.copy()
        for sequence, direction in (("<MouseWheel>", 1), ("<Button-4>", 1), ("<Button-5>", -1)):
            with self.subTest(sequence=sequence):
                before = app.zoom_factor
                transform = app.display_transform
                x = (app.video_label.winfo_width() - app.video_width) // 2 + transform.width // 2
                y = (app.video_label.winfo_height() - app.video_height) // 2 + transform.height // 2
                app.video_label.event_generate(sequence, x=x, y=y, state=0,
                                               **({"delta": 120} if sequence == "<MouseWheel>" else {}))
                self.assertAlmostEqual(app.zoom_factor, before + .1 * direction)
                expected_width = int(raw.shape[1] / app.zoom_factor)
                self.wait_until(lambda: app.display_transform.crop_width == expected_width)
        # Zoom further entirely through widget events, then start a drag in
        # the letterbox margin rather than touching a guide or source pixel.
        for _ in range(9):
            app.video_label.event_generate("<MouseWheel>", x=x, y=y, delta=120, state=0)
            self.root.update()
        self.wait_until(lambda: app.display_transform.crop_width < 420)
        transform = app.display_transform
        ox = (app.video_label.winfo_width() - app.video_width) // 2
        oy = (app.video_label.winfo_height() - app.video_height) // 2
        self.assertGreater(max(ox, oy), 10)
        x, y = (2, app.video_label.winfo_height() // 2) if ox > 10 else (app.video_label.winfo_width() // 2, 2)
        app.video_label.event_generate("<ButtonPress-1>", x=x, y=y, state=0)
        self.assertIsNotNone(app.pan_anchor)
        self.assertIsNone(app.circle_drag)
        app.video_label.event_generate("<B1-Motion>", x=x + 40, y=y + 25, state=0x100)
        app.video_label.event_generate("<ButtonRelease-1>", x=x + 40, y=y + 25, state=0)
        self.wait_until(lambda: app.display_transform.crop_x != transform.crop_x)
        self.assertAlmostEqual(app.display_transform.crop_x,
                               transform.crop_x - 40 * transform.crop_width / transform.width, delta=1)
        self.assertIsNone(app.pan_anchor)
        self.assertEqual(app.detection, detection)
        np.testing.assert_array_equal(app.last_frame, raw)
        app.view_reset_button.invoke()
        self.wait_until(lambda: app.display_transform.crop_width == raw.shape[1])
        self.assertEqual((app.display_transform.crop_x, app.display_transform.crop_y), (0, 0))
        self.assertIsNone(app.view_center)
        self.assertEqual(app.detection, detection)

    def test_opened_image_precise_scroll_decodes_both_axes_and_preserves_editing(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        if not self.root.tk.call("info", "commands", "::tk::PreciseScrollDeltas"):
            self.skipTest("Tk does not provide high-resolution scroll events")
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        self.open_detect_export(optical_fixture())
        app.notebook.select(app.review_panel)
        self.wait_until(lambda: app.display_transform is not None)
        detection = app.detection
        original = app.last_frame.copy()
        ox = (app.video_label.winfo_width() - app.video_width) // 2
        oy = (app.video_label.winfo_height() - app.video_height) // 2
        x, y = ox + app.video_width // 2, oy + app.video_height // 2
        fine_step = .025 if self.root.tk.call("tk", "windowingsystem") == "win32" else .1
        for horizontal, vertical in ((0, 30), (5, -30), (-5, 0)):
            before = app.zoom_factor
            packed = (horizontal << 16) | (vertical & 0xffff)
            app.video_label.event_generate("<TouchpadScroll>", x=x, y=y, delta=packed, state=0)
            expected = before + fine_step * ((vertical > 0) - (vertical < 0))
            self.assertAlmostEqual(app.zoom_factor, expected)
            self.root.update()
        self.assertEqual(app.detection, detection)
        np.testing.assert_array_equal(app.last_frame, original)
        edge = app.detection.candidate(app.selections["Primary reflection"])
        point = app.display_transform.to_display((edge.center[0] + edge.radius, edge.center[1]))
        ox = (app.video_label.winfo_width() - app.video_width) // 2
        oy = (app.video_label.winfo_height() - app.video_height) // 2
        before_zoom = app.zoom_factor
        app.video_label.event_generate("<TouchpadScroll>", x=round(ox + point[0]), y=round(oy + point[1]),
                                       delta=(-30 & 0xffff), state=0x0004)
        self.assertEqual(app.detection.candidate(edge.id).radius, round(edge.radius) - 1)
        self.assertEqual(app.zoom_factor, before_zoom)
        self.assertEqual(app.detection.guide_center, detection.guide_center)
        output = app.export_capture(app.options_store.path.with_name("precise-scroll.png"))
        np.testing.assert_array_equal(cv2.imdecode(np.frombuffer(output.read_bytes(), np.uint8), 1), original)

    @unittest.skipUnless(sys.platform == "win32", "Native Windows wheel delivery")
    def test_native_windows_fine_wheel_reaches_image_with_sidebar_focus(self):
        import ctypes as ct
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        if not self.root.tk.call("info", "commands", "::tk::PreciseScrollDeltas"):
            self.skipTest("Tk does not provide high-resolution scroll events")
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        self.open_detect_export(optical_fixture())
        app.notebook.select(app.review_panel)
        self.wait_until(lambda: app.display_transform is not None)
        detection = app.detection
        original = app.last_frame.copy()
        # Native Tk routes Windows wheel messages by hit-testing the visible
        # window. Unlike event_generate, this needs an opaque mapped window.
        self.root.attributes("-alpha", 1)
        self.root.lift()
        self.root.update()
        user = ct.WinDLL("user32")
        user.SendMessageW.argtypes = (ct.c_void_p, ct.c_uint32, ct.c_size_t, ct.c_ssize_t)
        user.SendMessageW.restype = ct.c_ssize_t
        x = app.video_label.winfo_rootx() + app.video_label.winfo_width() // 2
        y = app.video_label.winfo_rooty() + app.video_label.winfo_height() // 2
        position = (x & 0xffff) | ((y & 0xffff) << 16)
        for focused in (app.video_label, app.view_reset_button):
            focused.focus_force()
            self.root.update()
            for delta in (30, -30, 120, -120):
                with self.subTest(focus=str(focused), delta=delta):
                    before = app.zoom_factor
                    # Send only to this owned app's HWND. Production Windows
                    # message translation, Tk routing and zoom handlers run.
                    user.SendMessageW(focused.winfo_id(), 0x020A, (delta & 0xffff) << 16, position)
                    expected = before + .1 * delta / 120
                    self.wait_until(lambda: abs(app.zoom_factor - expected) < 1e-8)
                    self.wait_until(lambda: app.display_transform.crop_width == int(original.shape[1] / expected))
        before = app.zoom_factor
        user.SendMessageW(app.video_label.winfo_id(), 0x020E, 30 << 16, position)
        self.root.update()
        self.assertAlmostEqual(app.zoom_factor, before)  # Horizontal input does not zoom.
        self.assertEqual(app.detection, detection)
        np.testing.assert_array_equal(app.last_frame, original)

    def test_opened_image_scroll_enlarges_rendered_pixels_and_records_input_path(self):
        from PIL import ImageTk
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
                "ASTRO_COLLIMATOR_INPUT_LOG": str(Path(directory) / "input.json")}):
            app = self.make_app(lambda index: FakeCapture(index, opened=False))
            self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
            frame = optical_fixture()
            frame[310:330, 460:490] = (250, 210, 10)
            self.open_detect_export(frame)
            app.notebook.select(app.review_panel)
            app.overlays_visible.set(False)
            self.wait_until(lambda: app.display_transform is not None)
            # Inspect the actual Tk image pixels, not only zoom/crop metadata.
            def colored_area():
                pixels = np.asarray(ImageTk.getimage(app.video_label.image))
                return int(np.count_nonzero((pixels[:, :, 0] < 30) &
                                            (pixels[:, :, 1] > 180) & (pixels[:, :, 2] > 200)))
            self.wait_until(lambda: colored_area() > 200)
            before = colored_area()
            detection = app.detection
            for _ in range(10):
                x = app.video_label.winfo_width() // 2
                y = app.video_label.winfo_height() // 2
                app.video_label.event_generate("<MouseWheel>", x=x, y=y, delta=120, state=0)
                expected_width = int(frame.shape[1] / app.zoom_factor)
                self.wait_until(lambda: app.display_transform.crop_width == expected_width)
            self.wait_until(lambda: colored_area() > before * 3.5)
            self.assertLess(colored_area(), before * 4.5)
            self.assertEqual(app.detection, detection)
            np.testing.assert_array_equal(app.last_frame, frame)
            path = Path(directory) / "input.json"
            self.wait_until(lambda: len(json.loads(path.read_text(encoding="utf-8"))["events"]) >= 10)
            report = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(Path(report["runtime"]["interpreter"]), Path(sys.executable))
            self.assertEqual(Path(report["runtime"]["source"]).parent.name, "source")
            events = report["events"]
            self.assertLessEqual(len(events), 40)
            self.assertEqual(events[-1]["callback"], "WebcamApp.zoom_with_scroll")
            self.assertEqual(events[-1]["state"], 0)
            self.assertEqual(events[-1]["raw_delta"], 120)
            self.assertGreater(events[-1]["after"]["zoom"], events[-1]["before"]["zoom"])
            self.assertEqual(events[-1]["after"]["radii"], events[-1]["before"]["radii"])
            output = app.export_capture(Path(directory) / "zoomed.png")
            np.testing.assert_array_equal(cv2.imdecode(np.frombuffer(output.read_bytes(), np.uint8), 1), frame)

    def test_named_camera_selection_refresh_fallback_and_detection_label(self):
        import threading
        from tests.fixtures.linux_camera import LinuxCameraHardware
        with LinuxCameraHardware() as hardware:
            app = self.make_app(None, native_camera=True)
            self.wait_until(lambda: app.camera_on and app.last_frame is not None)
            self.assertEqual(app.detect_button.cget("text"), "Detect edges and align image")
            self.assertEqual(app.camera_devices, {"Astro Camera (Camera 2)": 2, "Astro Camera (Camera 14)": 14})
            app.selected_camera.set("Astro Camera (Camera 14)")
            app.camera_dropdown.event_generate("<<ComboboxSelected>>")
            self.wait_until(lambda: app.camera_on and app.last_frame is not None and hardware.captures[-1].index == 14)
            self.assertEqual(app.source_description, "Astro Camera (Camera 14)")
            hardware.names[14] = "  ZWO ASI 174 MM  "
            session = app.session
            app.refresh_button.invoke()
            self.wait_until(lambda: app.session > session + 1 and app.camera_on and app.last_frame is not None)
            self.assertEqual(app.selected_camera.get(), "ZWO ASI 174 MM (Camera 14)")
            self.assertEqual(hardware.captures[-1].index, 14)
            hardware.names.clear()
            session = app.session
            app.refresh_button.invoke()
            self.wait_until(lambda: app.session > session + 1 and app.camera_on and app.last_frame is not None)
            self.assertEqual(app.camera_list, ["Camera 2", "Camera 14"])
            self.assertEqual(app.selected_camera.get(), "Camera 14")
            self.assertTrue(all(owner != threading.get_ident() for _, owner in hardware.name_reads))
            for size in ("1280x720", "1024x768"):
                self.root.geometry(size)
                app.notebook.select(app.review_panel)
                self.root.update()
                self.assertLessEqual(app.detect_button.winfo_rootx() + app.detect_button.winfo_reqwidth(),
                                     app.review_panel.winfo_rootx() + app.review_panel.winfo_width())
            self.open_detect_export(pupil_fixture())
            app.resume_live()
            self.wait_until(lambda: app.camera_on and app.last_frame is not None)
            self.assertEqual(app.selected_camera.get(), "Camera 14")
            self.assertEqual(hardware.captures[-1].index, 14)

    @unittest.skipUnless(sys.platform == "win32", "Native DirectShow name API requires Windows")
    def test_windows_native_camera_names_scan_stream_and_refresh(self):
        from source.camera_properties import query_camera_names
        captures = []
        expected = query_camera_names(list(range(10)))

        def factory(index):
            cap = FakeCapture(index, opened=index in (0, 1))
            captures.append(cap)
            return cap

        app = self.make_app(factory, native_names=True)
        self.wait_until(lambda: app.camera_on and app.last_frame is not None)
        for label, index in app.camera_devices.items():
            name = " ".join(expected.get(index, "").split())
            self.assertEqual(label, f"{name} (Camera {index})" if name else f"Camera {index}")
        self.assertEqual(app.camera_devices[app.selected_camera.get()], 0)
        app.camera_dropdown.current(1)
        app.camera_dropdown.event_generate("<<ComboboxSelected>>")
        self.wait_until(lambda: app.camera_on and app.last_frame is not None and captures[-1].index == 1)
        session = app.session
        app.refresh_button.invoke()
        self.wait_until(lambda: app.session > session + 1 and app.camera_on and app.last_frame is not None)
        self.assertEqual(app.camera_devices[app.selected_camera.get()], 1)
        self.assertEqual(captures[-1].index, 1)
