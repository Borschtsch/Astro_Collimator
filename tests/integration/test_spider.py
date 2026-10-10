"""Spider evidence through production loading, analysis, controls and rendering."""
import tempfile
from pathlib import Path
import cv2
import numpy as np
from PIL import ImageTk
from tests.integration.test_app import GuiTests
from tests.fixtures.camera import FakeCapture
from tests.fixtures.images import optical_fixture, spider_fixture, red_pixels


class SpiderTests(GuiTests):
    def load_fixture(self, app, frame):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spider.png"
            self.assertTrue(cv2.imwrite(str(path), frame))
            app.load_image(path)

    def test_auto_alignment_and_shared_controls(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        self.assertEqual(app.crosshair_blades.get(), 4)
        for count, angle in ((3, 19), (4, 33), (2, 47), (3, 110)):
            with self.subTest(count=count, angle=angle):
                self.load_fixture(app, spider_fixture(count, angle))
                app.start_detection()
                self.wait_until(lambda: not app.analysis_busy and app.detection is not None)
                self.assertEqual(app.vane_detection.count, count)
                self.assertEqual(app.crosshair_blades.get(), 3 if count == 3 else 4)
                selection = dict(app.selections)
                capture_advice = app.review_status.get()
                app.align_crosshairs()
                self.assertEqual(app.vane_status.get(), "Aligning…")
                self.wait_until(lambda: not app.vane_busy)
                self.assertEqual(app.vane_status.get(), "")
                self.assertEqual(app.review_status.get(), capture_advice)
                step = 120 if count == 3 else 90
                error = (app.crosshair_angles["optical"] + angle + step / 2) % step - step / 2
                self.assertLess(abs(error), 3)
                self.assertEqual(app.crosshair_angles["fov"], 0)  # Image turns; crosshair angle stays fixed.
                self.assertEqual(app.selections, selection)
                np.testing.assert_array_equal(app.last_frame, spider_fixture(count, angle))
        app.notebook.select(app.manual_panel)
        self.root.update()
        if not app.fov_crosshair_visible.get():
            app.fov_checkbox.invoke()
        app.crosshair_controls[1]["switch"].invoke()
        self.assertEqual(app.crosshair_blades.get(), 4)
        app.angle_text["optical"].set("-15")
        app.set_crosshair_angle("optical")
        self.assertEqual(app.crosshair_angles["optical"], 345)
        fov_angle = app.crosshair_angles["fov"]
        app.angle_text["fov"].set("nan")
        app.set_crosshair_angle("fov")
        self.assertEqual(app.crosshair_angles["fov"], fov_angle)
        for size in ("1280x720", "1024x768"):
            self.root.geometry(size)
            for tab, controls in zip((app.review_panel, app.manual_panel), app.crosshair_controls):
                app.notebook.select(tab)
                self.root.update()
                for widget in (controls["panel"], controls["switch"], controls["align"], *controls["entries"].values()):
                    self.assertTrue(widget.winfo_ismapped())
                    self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), self.root.winfo_rooty() + self.root.winfo_height())
                    self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), app.sidebar.winfo_rootx() + app.sidebar.winfo_width())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.png"
            app.export_capture(path)
            import json
            metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["image_rotation_deg"], 345)
            self.assertNotIn("optical_crosshair", metadata)
            self.assertEqual(metadata["crosshair"], metadata["fov_crosshair"])
            self.assertEqual(metadata["fov_crosshair"]["angle_deg"], fov_angle)
            self.assertEqual(metadata["spider_vanes"]["count"], 3)
            np.testing.assert_array_equal(cv2.imread(str(path)), app.last_frame)

    def test_uncertain_spiders_and_stale_alignment(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        for frame in (optical_fixture(), spider_fixture(3, design="curved"),
                      spider_fixture(3, design="offset"), spider_fixture(3, blur=12),
                      np.zeros((600, 800, 3), np.uint8)):
            self.load_fixture(app, frame)
            for name, angle in (("optical", "27"), ("fov", "52")):
                app.angle_text[name].set(angle)
                app.set_crosshair_angle(name)
            app.align_crosshairs()
            self.wait_until(lambda: not app.vane_busy)
            self.assertEqual(app.crosshair_blades.get(), 4)
            self.assertIsNone(app.vane_detection.angle_deg)
            self.assertEqual(app.crosshair_angles, {"optical": 27, "fov": 52})
        self.load_fixture(app, spider_fixture(3, 19))
        app.align_crosshairs()
        app.angle_text["optical"].set("73")
        app.set_crosshair_angle("optical")
        self.wait_until(lambda: not app.vane_busy)
        self.assertEqual(app.crosshair_angles["optical"], 73)
        app.align_crosshairs()
        self.load_fixture(app, optical_fixture())
        self.wait_until(lambda: not app.vane_busy)
        self.assertEqual(app.crosshair_blades.get(), 4)
        self.assertIsNone(app.vane_detection.count)

    def test_crosshair_visibility_rotation_blink_and_live_capture(self):
        captures = []
        def factory(index):
            capture = FakeCapture(index, opened=index == 0)
            capture.frame = spider_fixture(3, 19)
            captures.append(capture)
            return capture
        app = self.make_app(factory, live_tracking=True)
        self.wait_until(lambda: app.camera_on and app.last_frame is not None)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None and app.vane_detection.count == 3)
        self.assertFalse(app.view_frozen)
        app.notebook.select(app.manual_panel)
        self.root.update()
        if not app.fov_crosshair_visible.get():
            app.fov_checkbox.invoke()
        app.crosshair_controls[1]["switch"].invoke()
        self.assertEqual(app.crosshair_blades.get(), 4)
        app.align_crosshairs()
        self.wait_until(lambda: not app.vane_busy)
        self.assertEqual(app.crosshair_blades.get(), 3)
        app.track_live.set(False)
        app.tracking_changed()
        self.assertTrue(app.camera_on)
        self.assertFalse(app.view_frozen)
        app.set_fov_crosshair_center(app.detection.guide_center)
        self.assertTrue(app.fov_crosshair_visible.get())
        app.angle_text["fov"].set("0")
        app.set_crosshair_angle("fov")
        self.wait_until(lambda: app.display_transform is not None)
        def pixels():
            return np.array(ImageTk.getimage(app.video_label.image))[:, :, :3]
        def center():
            return tuple(round(v) for v in app.display_transform.to_display(app.fov_crosshair_center()))
        x, y = center()
        self.wait_until(lambda: red_pixels(pixels()[y, x + 25]))
        # Three rays differ visibly from the four-blade fallback.
        self.assertFalse(red_pixels(tuple(pixels()[y - 25, x])))
        self.assertTrue(np.any(red_pixels(pixels()[y + 24:y + 29, x - 17:x - 12])))
        app.crosshair_controls[1]["switch"].invoke()
        self.wait_until(lambda: red_pixels(pixels()[y - 25, x]))
        self.assertEqual(set(app.crosshair_controls[0]["checkboxes"]), {"fov"})
        self.assertFalse(hasattr(app, "optical_crosshair_visible"))
        app.crosshair_controls[1]["checkboxes"]["fov"].invoke()
        self.assertFalse(app.fov_crosshair_visible.get())
        self.wait_until(lambda: np.all(pixels()[y, x] >= 240)
                        and not red_pixels(pixels()[y, x + 25]))
        app.notebook.select(app.review_panel)
        self.root.update()
        self.assertFalse(app.fov_crosshair_visible.get())
        app.crosshair_controls[0]["checkboxes"]["fov"].invoke()
        self.wait_until(lambda: tuple(pixels()[y, x]) == (255, 255, 255)
                        and red_pixels(pixels()[y, x + 25]))
        app.begin_blink()
        self.wait_until(lambda: tuple(pixels()[y, x]) != (255, 255, 255))
        app.end_blink()
        self.wait_until(lambda: tuple(pixels()[y, x]) == (255, 255, 255))
        self.assertTrue(app.camera_on)
        self.assertFalse(app.analysis_busy)

    def test_real_photographs_recognize_clear_vanes_and_rotate_display_only(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        photos = Path(__file__).resolve().parents[1] / "images"
        for name, expected in (("2.png", 40.25), ("qbvhjd7cwo7a1.jpg", 0),
                               ("post-333184-0-47945200-1591447543.jpeg", 11.63)):
            with self.subTest(photo=name):
                app.load_image(photos / name)
                raw = app.last_frame.copy()
                app.start_detection()
                deadline = __import__("time").monotonic() + 8
                while app.analysis_busy and __import__("time").monotonic() < deadline:
                    self.root.update()
                    __import__("time").sleep(.01)
                self.assertFalse(app.analysis_busy)
                self.assertIsNotNone(app.detection)
                self.assertEqual(app.vane_detection.count, 4)
                self.assertEqual(app.crosshair_blades.get(), 4)
                selections = dict(app.selections)
                app.align_crosshairs()
                self.wait_until(lambda: not app.vane_busy)
                self.assertEqual(app.vane_detection.count, 4)
                error = (app.crosshair_angles["optical"] + expected + 45) % 90 - 45
                self.assertLess(abs(error), 3)
                self.assertEqual(app.crosshair_angles["fov"], 0)
                self.assertEqual(app.selections, selections)
                np.testing.assert_array_equal(app.last_frame, raw)

    def test_drag_angles_rotate_image_and_preserve_rotated_mouse_workflows(self):
        from types import SimpleNamespace
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        raw = spider_fixture(4)
        cv2.circle(raw, (490, 220), 12, (0, 0, 255), -1)
        self.load_fixture(app, raw)
        app.start_detection()
        self.wait_until(lambda: app.detection is not None and not app.analysis_busy)
        original_detection = app.detection
        app.overlays_visible.set(False)
        app.angle_text["optical"].set("90.00")
        app.set_crosshair_angle("optical")
        def pixels():
            return np.array(ImageTk.getimage(app.video_label.image))[:, :, :3]
        self.wait_until(lambda: app.display_transform.rotation_deg == 90)
        transform = app.display_transform
        x, y = (round(v) for v in transform.to_display((490, 220)))
        self.assertTrue(red_pixels(tuple(pixels()[y, x])))
        # Rotation keeps the source scale; corners may fall outside the viewport.
        self.assertAlmostEqual(transform.display_scale, transform.width / 800)
        self.assertAlmostEqual(__import__("math").dist(transform.to_display((490, 220)),
            transform.to_display((500, 220))), 10 * transform.display_scale)
        self.assertEqual(transform.pivot, app.fov_crosshair_center())
        controls = app.crosshair_controls[0]
        entry = controls["entries"]["optical"]
        self.assertEqual(entry.winfo_class(), "TEntry")
        entry.event_generate("<ButtonPress-1>", x=5, y=5, rootx=100, rooty=100)
        entry.event_generate("<B1-Motion>", x=15, y=5, rootx=110, rooty=100, state=0x100)
        self.root.update()
        self.assertEqual(app.crosshair_angles["optical"], 91)
        # Entering fine mode mid-drag continues smoothly from the current angle.
        entry.event_generate("<B1-Motion>", x=16, y=5, rootx=111, rooty=100, state=0x101)
        entry.event_generate("<ButtonRelease-1>", x=16, y=5, rootx=111, rooty=100)
        self.root.update()
        self.assertEqual(app.crosshair_angles["optical"], 91.01)
        entry.event_generate("<ButtonPress-1>", x=5, y=5, rootx=100, rooty=100)
        entry.event_generate("<B1-Motion>", x=8, y=5, rootx=103, rooty=100, state=0x101)
        entry.event_generate("<ButtonRelease-1>", x=8, y=5, rootx=103, rooty=100)
        self.root.update()
        self.assertEqual(app.crosshair_angles["optical"], 91.04)
        self.assertEqual(app.angle_text["optical"].get(), "91.04")
        app.angle_text["optical"].set("90")
        app.set_crosshair_angle("optical")
        app.overlays_visible.set(True)
        app.fov_crosshair_visible.set(True)
        app.set_fov_crosshair_center((500, 250))
        self.wait_until(lambda: app.display_transform.rotation_deg == 90 and app.fov_crosshair_center() == (500, 250))
        transform = app.display_transform
        cx, cy = (round(v) for v in transform.to_display((500, 250)))
        self.wait_until(lambda: red_pixels(pixels()[cy + 25, cx]))
        x, y = (round(v) for v in transform.to_display((490, 220)))
        landmark = tuple(pixels()[y, x])
        app.angle_text["fov"].set("30.01")
        app.set_crosshair_angle("fov")
        self.wait_until(lambda: not red_pixels(pixels()[cy + 25, cx]))
        self.assertEqual(tuple(pixels()[y, x]), landmark)
        self.assertEqual(app.detection.observations, original_detection.observations)
        # Overlay dragging uses the inverse rotation without moving image pixels.
        def event(point, **extra):
            extra.setdefault("num", 1)
            return SimpleNamespace(widget=app.video_label,
                x=round(point[0] + (app.video_label.winfo_width() - app.video_width) // 2),
                y=round(point[1] + (app.video_label.winfo_height() - app.video_height) // 2), **extra)
        hit = transform.to_display((500, 250))
        self.assertEqual(app.circle_at(hit)["kind"], "fov")
        app.begin_pan(event(hit))
        app.pan_image(event((hit[0], hit[1] + 30)))
        app.end_pan()
        expected_delta = transform.to_original_vector((0, 30))
        self.assertLess(abs(app.fov_crosshair_center()[0] - 500 - expected_delta[0]), 1)
        self.assertLess(abs(app.fov_crosshair_center()[1] - 250 - expected_delta[1]), 1)
        self.root.update()
        transform = app.display_transform
        edge = app.detection.candidate(app.selections["Primary reflection"])
        rim = transform.to_display((edge.center[0] + edge.radius, edge.center[1]))
        self.assertEqual(app.circle_at(rim, include_fov=False)["kind"], "candidate")
        # Zoom preserves the cursor's raw image anchor under rotation.
        anchor = transform.to_display((430, 320))
        before = transform.to_original(anchor)
        app.zoom_with_scroll(event(anchor, delta=120, state=0, num=None))
        self.wait_until(lambda: app.display_transform.crop_width < transform.crop_width)
        self.assertLess(__import__("math").dist(before, app.display_transform.to_original(anchor)), 2)
        app.zoom_factor = 2
        app.set_view_center((400, 300))
        self.wait_until(lambda: app.display_transform.crop_width == 400)
        transform = app.display_transform
        start = (15, 15)
        app.begin_pan(event(start))
        app.pan_image(event((35, 25)))
        app.end_pan()
        expected_delta = transform.viewport_delta((20, 10))
        self.assertLess(abs(app.view_center[0] - (400 - expected_delta[0])), 1)
        self.assertLess(abs(app.view_center[1] - (300 - expected_delta[1])), 1)
        with tempfile.TemporaryDirectory() as directory:
            rotated_path = Path(directory) / "before-reset.png"
            app.export_capture(rotated_path)
            import json
            saved = json.loads(rotated_path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(saved["image_rotation_deg"], 90)
            self.assertEqual(saved["crosshair"]["angle_deg"], 30.01)
            np.testing.assert_array_equal(cv2.imread(str(rotated_path)), raw)
        app.view_reset_button.invoke()
        self.wait_until(lambda: app.display_transform.crop_width == 800 and app.display_transform.rotation_deg == 0)
        self.assertEqual(app.crosshair_angles, {"optical": 0, "fov": 0})
        self.assertEqual([value.get() for value in app.angle_text.values()], ["0.00", "0.00"])
        np.testing.assert_array_equal(app.last_frame, raw)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rotated.png"
            app.export_capture(path)
            import json
            metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["image_rotation_deg"], 0)
            self.assertEqual(metadata["fov_crosshair"]["angle_deg"], 0)
            np.testing.assert_array_equal(cv2.imread(str(path)), raw)

    def test_repeated_image_rotation_preserves_manual_circle_size(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        self.load_fixture(app, np.zeros((600, 800, 3), np.uint8))
        app.notebook.select(app.manual_panel)
        self.wait_until(lambda: app.display_transform is not None and app.show_crosshair)
        ring = app.ring_controls[1]
        ring.slider.set(137)
        self.root.update()
        self.assertEqual(ring.slider.get(), 137)
        for angle in (*range(2, 91, 2), *range(88, -1, -2)):
            app.angle_text["optical"].set(str(angle))
            app.set_crosshair_angle("optical")
            self.wait_until(lambda: app.display_transform.rotation_deg == angle)
        self.assertEqual(ring.slider.get(), 137)
        self.assertIn("Secondary edge", app.manual_guide_edits)
        self.assertIsNone(app.detection)
        np.testing.assert_array_equal(app.last_frame, np.zeros((600, 800, 3), np.uint8))

    def test_rotation_uses_crosshair_pivot_at_fixed_scale_and_source_load_resets_view(self):
        import math
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        raw = spider_fixture(4, 19)
        cv2.circle(raw, (400, 300), 8, (0, 0, 255), -1)
        cv2.circle(raw, (350, 100), 8, (0, 255, 0), -1)
        self.load_fixture(app, raw)
        app.overlays_visible.set(False)
        app.set_fov_crosshair_center((350, 275))
        for zoom in (1, 2):
            app.zoom_factor = zoom
            app.set_view_center((400, 300))
            app.angle_text["optical"].set("0")
            app.set_crosshair_angle("optical")
            self.wait_until(lambda: app.display_transform.crop_width == int(800 / zoom)
                            and app.display_transform.rotation_deg == 0)
            base = app.display_transform
            pivot = base.to_display((350, 275))
            radius = math.dist(base.to_display((400, 300)), pivot)
            for angle in (23.57, 45, 90, 180):
                app.angle_text["optical"].set(str(angle))
                app.set_crosshair_angle("optical")
                self.wait_until(lambda: app.display_transform.rotation_deg == angle)
                transform = app.display_transform
                self.assertEqual(transform.pivot, (350, 275))
                self.assertEqual(transform.display_scale, base.display_scale)
                np.testing.assert_allclose(transform.to_display((350, 275)), pivot, atol=1e-8)
                self.assertAlmostEqual(math.dist(transform.to_display((400, 300)), pivot), radius)
                np.testing.assert_allclose(transform.to_original(transform.to_display((400, 300))),
                                           (400, 300), atol=1e-8)
                point = tuple(round(v) for v in transform.to_display((400, 300)))
                pixels = np.array(ImageTk.getimage(app.video_label.image))[:, :, :3]
                self.assertTrue(red_pixels(tuple(pixels[point[1], point[0]])))
                if zoom == 2 and angle == 90:
                    # Rotation reads full source pixels beyond the original zoom crop.
                    self.assertLess(100, transform.crop_y)
                    x, y = (round(v) for v in transform.to_display((350, 100)))
                    self.assertEqual(tuple(pixels[y, x]), (0, 255, 0))
        app.angle_text["fov"].set("42.35")
        app.set_crosshair_angle("fov")
        app.align_crosshairs()
        app.view_reset_button.invoke()
        self.wait_until(lambda: not app.vane_busy and app.display_transform.rotation_deg == 0
                        and app.display_transform.crop_width == 800)
        self.assertEqual(app.crosshair_angles, {"optical": 0, "fov": 0})
        self.assertEqual(app.zoom_factor, 1)
        self.assertIsNone(app.view_center)
        self.assertEqual(app.fov_crosshair_center(), (400, 300))
        app.zoom_factor = 2
        app.set_view_center((450, 325))
        for name, angle in (("optical", "67.89"), ("fov", "12.34")):
            app.angle_text[name].set(angle)
            app.set_crosshair_angle(name)
        replacement = optical_fixture()
        self.load_fixture(app, replacement)
        self.wait_until(lambda: app.display_transform is not None and app.display_transform.rotation_deg == 0
                        and app.display_transform.crop_width == 800)
        self.assertEqual(app.crosshair_angles, {"optical": 0, "fov": 0})
        self.assertEqual([value.get() for value in app.angle_text.values()], ["0.00", "0.00"])
        self.assertEqual(app.zoom_factor, 1)
        self.assertIsNone(app.view_center)
        self.assertEqual(app.fov_crosshair_center(), (400, 300))
        self.assertIsNone(app.detection)
        np.testing.assert_array_equal(app.last_frame, replacement)

    def test_overlay_edits_keep_rotated_pixels_fixed_and_angle_edits_use_current_center(self):
        import math
        from types import SimpleNamespace
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        raw = optical_fixture()
        cv2.circle(raw, (420, 320), 7, (0, 0, 255), -1)
        def repaint():
            previous = app.video_label.image
            self.wait_until(lambda: app.video_label.image is not previous)
        def clean_pixels():
            app.overlays_visible.set(False)
            repaint()
            result = np.array(ImageTk.getimage(app.video_label.image))[:, :, :3]
            app.overlays_visible.set(True)
            repaint()
            return result
        def event(point, **extra):
            extra.setdefault("num", 1)
            return SimpleNamespace(widget=app.video_label,
                x=round(point[0] + (app.video_label.winfo_width() - app.video_width) // 2),
                y=round(point[1] + (app.video_label.winfo_height() - app.video_height) // 2), **extra)
        for mode, zoom in ((m, z) for m in ("fov", "manual", "detected") for z in (1, 2)):
            for angle in (0, 37.25, 90):
                with self.subTest(mode=mode, zoom=zoom, angle=angle):
                    self.load_fixture(app, raw)
                    self.assertEqual(app.image_rotation_shift, (0.0, 0.0))
                    self.assertIsNone(app.image_rotation_center)
                    app.notebook.select(app.manual_panel if mode == "manual" else app.review_panel)
                    self.root.update()
                    if mode == "detected":
                        app.start_detection()
                        self.wait_until(lambda: app.detection is not None and not app.analysis_busy)
                    elif mode == "manual":
                        app.ring_controls[0].slider.set(65)
                        self.root.update()
                    app.fov_crosshair_visible.set(True)
                    app.set_fov_crosshair_center((390, 285))
                    app.zoom_factor = zoom
                    app.set_view_center((400, 300))
                    app.angle_text["optical"].set(str(angle))
                    app.set_crosshair_angle("optical")
                    self.wait_until(lambda: app.display_transform is not None
                                    and app.display_transform.crop_width == int(800 / zoom)
                                    and app.display_transform.rotation_deg == angle)
                    baseline = clean_pixels()
                    transform = app.display_transform
                    view = app.view_center
                    observations = app.detection.observations if app.detection else None
                    original = app.fov_crosshair_center()
                    guide_center = app.detection.guide_center if app.detection else None
                    manual_center = (app.crosshair_x, app.crosshair_y)
                    point = transform.to_display(original)
                    app.begin_pan(event(point))
                    self.assertIsNotNone(app.circle_drag, {"point": point, "fov": app.fov_crosshair_center(), "transform": app.display_transform, "shown": app.overlays_shown(), "picking": app.picking_role, "image_position": app.image_position(event(point)), "dimensions": (app.video_width, app.video_height), "hit": app.circle_at(point)})
                    self.assertEqual(app.circle_drag["kind"], "fov")
                    app.pan_image(event((point[0] + 24, point[1] - 18)))
                    app.end_pan()
                    repaint()
                    delta = transform.to_original_vector((24, -18))
                    np.testing.assert_allclose(app.fov_crosshair_center(), np.add(original, delta), atol=1)
                    np.testing.assert_array_equal(clean_pixels(), baseline)
                    np.testing.assert_allclose(app.display_transform.image_matrix(), transform.image_matrix(), atol=1e-8)
                    self.assertEqual(app.view_center, view)
                    if app.detection:
                        self.assertEqual(app.detection.guide_center, guide_center)
                    self.assertEqual((app.crosshair_x, app.crosshair_y), manual_center)
                    if mode != "fov":
                        fixed_fov = app.fov_crosshair_center()
                        if mode == "manual":
                            point = (app.crosshair_x + app.ring_controls[0].slider.get(), app.crosshair_y)
                        else:
                            edge = app.detection.candidate(app.selections["Primary reflection"])
                            points = [transform.to_display((edge.center[0] + edge.radius * math.cos(a),
                                                            edge.center[1] + edge.radius * math.sin(a)))
                                      for a in np.linspace(0, 2 * math.pi, 72)]
                            point = next(p for p in points if 15 < p[0] < transform.width - 15
                                         and 15 < p[1] < transform.height - 15
                                         and (app.circle_at(p) or {}).get("kind") == "candidate")
                        app.begin_pan(event(point))
                        self.assertEqual(app.circle_drag["kind"], "guide" if mode == "manual" else "candidate")
                        app.pan_image(event((point[0] - 20, point[1] + 12)))
                        app.end_pan()
                        np.testing.assert_array_equal(clean_pixels(), baseline)
                        self.assertEqual(app.fov_crosshair_center(), fixed_fov)
                        if mode == "manual":
                            app.move_crosshair(7, -5)
                            np.testing.assert_array_equal(clean_pixels(), baseline)
                        else:
                            self.assertEqual(app.detection.observations, observations)
                            # A new automatic master must not rebase the image.
                            app.start_detection()
                            self.wait_until(lambda: app.detection is not None and not app.analysis_busy)
                            np.testing.assert_array_equal(clean_pixels(), baseline)
                    guide_before_recenter = app.detection
                    manual_before_recenter = (app.crosshair_x, app.crosshair_y)
                    app.fov_center_button.invoke()
                    self.assertEqual(app.detection, guide_before_recenter)
                    self.assertEqual((app.crosshair_x, app.crosshair_y), manual_before_recenter)
                    np.testing.assert_array_equal(clean_pixels(), baseline)
                    # A subsequent angle change rotates around the moved intersection,
                    # keeping that intersection in exactly the same screen position.
                    pivot = app.fov_crosshair_center()
                    old = app.display_transform
                    before = old.to_display(pivot)
                    landmark = old.to_display((420, 320))
                    app.angle_text["optical"].set(str(angle + 11.5))
                    app.set_crosshair_angle("optical")
                    self.wait_until(lambda: app.display_transform.rotation_deg == angle + 11.5)
                    rotated = app.display_transform
                    np.testing.assert_allclose(rotated.to_display(pivot), before, atol=1e-8)
                    self.assertEqual(rotated.pivot, pivot)
                    self.assertEqual(rotated.display_scale, old.display_scale)
                    self.assertAlmostEqual(math.dist(rotated.to_display((420, 320)), before),
                                           math.dist(landmark, before))
                    # Cursor zoom retains its source anchor even after pivot composition.
                    target = rotated.to_display((420, 320))
                    anchor = rotated.to_original(target)
                    app.zoom_with_scroll(event(target, delta=120, state=0, num=None))
                    self.wait_until(lambda: app.display_transform.crop_width < rotated.crop_width)
                    self.assertLess(math.dist(app.display_transform.to_original(target), anchor), 2)
                    # Empty-space/middle drag deliberately moves pixels in screen axes.
                    panned_from = app.display_transform
                    before_point = panned_from.to_display((420, 320))
                    app.begin_pan(event((10, 10), num=2))
                    app.pan_image(event((30, 20), num=2))
                    app.end_pan()
                    self.wait_until(lambda: app.display_transform.crop_x != panned_from.crop_x
                                    or app.display_transform.crop_y != panned_from.crop_y)
                    np.testing.assert_allclose(app.display_transform.to_display((420, 320)),
                                               np.add(before_point, (20, 10)), atol=2)
                    clean = clean_pixels()
                    x, y = (round(v) for v in app.display_transform.to_display((420, 320)))
                    self.assertTrue(red_pixels(tuple(clean[y, x])))
                    np.testing.assert_array_equal(app.last_frame, raw)

    def test_manual_tab_on_rotated_zoomed_file_has_no_frame_jitter(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        raw = optical_fixture()
        self.load_fixture(app, raw)
        app.notebook.select(app.review_panel)
        self.root.update()
        app.fov_crosshair_visible.set(True)
        app.set_fov_crosshair_center((370, 280))
        app.zoom_factor = 2
        app.set_view_center((400, 300))
        app.angle_text["optical"].set("37.25")
        app.set_crosshair_angle("optical")
        self.wait_until(lambda: app.display_transform is not None and app.display_transform.rotation_deg == 37.25)
        app.notebook.select(app.manual_panel)
        self.root.update()
        previous = app.video_label.image
        self.wait_until(lambda: app.video_label.image is not previous)
        matrix = app.display_transform.image_matrix()
        guide_center = app.display_transform.to_original((app.crosshair_x, app.crosshair_y))
        radii = [ring.slider.get() for ring in app.ring_controls]
        reference = np.array(ImageTk.getimage(app.video_label.image))
        for index in range(24):
            if index % 4 == 0:
                app.notebook.select(app.review_panel)
                self.root.update()
                app.notebook.select(app.manual_panel)
                self.root.update()
            previous = app.video_label.image
            self.wait_until(lambda: app.video_label.image is not previous)
            np.testing.assert_allclose(app.display_transform.image_matrix(), matrix, atol=1e-8)
            np.testing.assert_allclose(app.display_transform.to_original((app.crosshair_x, app.crosshair_y)),
                                       guide_center, atol=1e-8)
            self.assertEqual([ring.slider.get() for ring in app.ring_controls], radii)
            self.assertEqual(app.fov_crosshair_center(), (370, 280))
            np.testing.assert_array_equal(np.array(ImageTk.getimage(app.video_label.image)), reference)
        self.assertIsNone(app.detection)
        self.assertEqual(app.source_mode, "image")
        np.testing.assert_array_equal(app.last_frame, raw)

    def test_fov_group_order_enablement_and_pending_alignment(self):
        from types import SimpleNamespace
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        self.load_fixture(app, spider_fixture(3, 19))
        controls = app.crosshair_controls[0]
        self.assertEqual(app.fov_checkbox.cget("text"), "FOV Crosshair")
        self.assertEqual(controls["center"].cget("text"), "Center")
        self.assertFalse(hasattr(app, "fullscreen_button"))
        self.assertTrue(controls["entries"]["fov"].instate(["disabled"]))
        app.fov_checkbox.invoke()
        for size in ("1280x720", "1024x768"):
            self.root.geometry(size)
            for tab in (app.review_panel, app.manual_panel):
                app.notebook.select(tab)
                self.root.update()
                center, align = (controls[n] for n in ("center", "align"))
                angle = controls["entries"]["fov"]
                self.assertLess(center.winfo_rootx(), align.winfo_rootx())
                self.assertLess(align.winfo_rootx(), angle.winfo_rootx())
                self.assertAlmostEqual(align.winfo_rooty(), angle.winfo_rooty(), delta=3)
                self.assertGreater(angle.winfo_rooty(), app.fov_checkbox.winfo_rooty() + app.fov_checkbox.winfo_height() - 3)
                self.assertNotIn("status", controls)
                self.assertGreater(align.winfo_rooty(), app.view_reset_button.winfo_rooty())
                self.assertAlmostEqual(app.fov_checkbox.winfo_rooty(), controls["switch"].winfo_rooty(), delta=3)
                self.assertTrue(controls["panel"].winfo_ismapped())
        old_angle = app.crosshair_angles["fov"]
        controls["align"].invoke()
        self.assertTrue(app.vane_busy)
        app.fov_checkbox.invoke()
        for name in ("center", "align", "switch"):
            self.assertTrue(controls[name].instate(["disabled"]))
        entry = controls["entries"]["fov"]
        self.assertTrue(entry.instate(["disabled"]))
        entry.begin_drag(SimpleNamespace(x_root=10, state=0))
        entry.drag(SimpleNamespace(x_root=110, state=0))
        self.assertIsNone(entry.anchor)
        app.angle_text["fov"].set("77.77")
        entry.event_generate("<FocusOut>")
        entry.event_generate("<Return>")
        self.root.update()
        self.assertEqual(app.crosshair_angles["fov"], old_angle)
        app.angle_text["fov"].set(f"{old_angle:.2f}")
        self.wait_until(lambda: not app.vane_busy)
        self.assertEqual(app.crosshair_angles["fov"], old_angle)
        self.assertFalse(controls["entries"]["optical"].instate(["disabled"]))
        self.assertFalse(app.view_reset_button.instate(["disabled"]))
        blades = app.crosshair_blades.get()
        controls["switch"].invoke()
        self.assertEqual(app.crosshair_blades.get(), blades)
        app.fov_checkbox.invoke()
        self.assertFalse(entry.instate(["disabled"]))
        controls["align"].invoke()
        self.wait_until(lambda: not app.vane_busy)
        self.assertEqual(app.vane_status.get(), "")

    def test_fractional_image_pivot_and_white_circle_center_independence(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        pivot = (370.37, 270.41)
        yy, xx = np.indices((600, 800))
        raw = np.zeros((600, 800, 3), np.uint8)
        raw[:, :, 1] = np.rint(200 * np.exp(-((xx - pivot[0]) ** 2 + (yy - pivot[1]) ** 2) / 32)).astype(np.uint8)
        self.load_fixture(app, raw)
        app.set_fov_crosshair_center(pivot)
        def repaint():
            previous = app.video_label.image
            self.wait_until(lambda: app.video_label.image is not previous)
            return np.array(ImageTk.getimage(app.video_label.image))[:, :, :3]
        def centroid(weights):
            y, x = np.indices(weights.shape)
            return (float((x * weights).sum() / weights.sum()), float((y * weights).sum() / weights.sum()))
        for zoom in (1, 2):
            app.zoom_factor = zoom
            app.set_view_center((400, 300))
            app.overlays_visible.set(False)
            for angle in (0, .01, 37.25, 90, 180):
                app.angle_text["optical"].set(str(angle))
                app.set_crosshair_angle("optical")
                pixels = repaint()
                expected = app.display_transform.to_display(pivot)
                np.testing.assert_allclose(centroid(pixels[:, :, 1].astype(float)), expected, atol=.12)
        app.fov_crosshair_visible.set(True)
        app.overlays_visible.set(True)
        app.notebook.select(app.manual_panel)
        repaint()
        # The white marker follows the guide group; the red FOV stays independent.
        for guide_center in ((430, 320), (455, 350)):
            app.set_review_center(guide_center)
            pixels = repaint()
            white = pixels.min(axis=2).astype(float)
            x, y = app.crosshair_x, app.crosshair_y
            yy, xx = np.indices(white.shape)
            white[(abs(xx - x) > 12) | (abs(yy - y) > 12)] = 0
            np.testing.assert_allclose(centroid(white), (x, y), atol=.2)
        fixed_guides = (app.crosshair_x, app.crosshair_y)
        moved = (pivot[0] + 15.15, pivot[1] - 12.12)
        app.set_fov_crosshair_center(moved)
        pixels = repaint()
        white = pixels.min(axis=2).astype(float)
        x, y = app.crosshair_x, app.crosshair_y
        yy, xx = np.indices(white.shape)
        white[(abs(xx - x) > 12) | (abs(yy - y) > 12)] = 0
        np.testing.assert_allclose(centroid(white), (x, y), atol=.2)
        self.assertEqual((app.crosshair_x, app.crosshair_y), fixed_guides)
        app.fov_checkbox.invoke()
        pixels = repaint()
        x, y = app.crosshair_x, app.crosshair_y
        self.assertTrue(np.all(pixels[y, x] >= 240))
        app.guides_visible.set(False)
        app.on_guide_visibility_changed()
        pixels = repaint()
        self.assertFalse(pixels.min(axis=2).any())
        np.testing.assert_array_equal(app.last_frame, raw)

    def test_white_guide_marker_matches_fov_shape_and_angle(self):
        import math
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        raw = np.zeros((600, 800, 3), np.uint8)
        self.load_fixture(app, raw)
        app.notebook.select(app.manual_panel)
        app.fov_checkbox.invoke()
        app.set_fov_crosshair_center((280, 180))
        def repaint():
            previous = app.video_label.image
            self.wait_until(lambda: app.video_label.image is not previous)
            return np.array(ImageTk.getimage(app.video_label.image))[:, :, :3]
        def point(center, angle, distance):
            vector = app.display_transform.to_display_vector((math.cos(math.radians(angle)), math.sin(math.radians(angle))))
            vector = np.array(vector) / np.linalg.norm(vector)
            return tuple(round(v) for v in np.add(center, distance * vector))
        def check_rays(pixels, blades, angle):
            guide = (app.crosshair_x, app.crosshair_y)
            fov = app.display_transform.to_display(app.fov_crosshair_center())
            for index in range(blades):
                direction = angle + index * 360 / blades
                x, y = point(guide, direction, 4)
                self.assertGreaterEqual(int(pixels[y, x].min()), 180)
                x, y = point(fov, direction, 30)
                self.assertTrue(red_pixels(pixels[y - 1:y + 2, x - 1:x + 2]).any())
            # Three rays lack the opposing first ray; four omit the diagonal.
            gap = angle + (180 if blades == 3 else 45)
            x, y = point(guide, gap, 4)
            self.assertLess(int(pixels[y, x].min()), 150)
        fixed_fov = app.fov_crosshair_center()
        for blades, angle, image_angle in ((4, 0, 0), (4, 45, 0), (3, 0, 0),
                                          (3, 90, 0), (3, 13.37, 37.25), (4, 0, 90)):
            with self.subTest(blades=blades, angle=angle, image_angle=image_angle):
                if app.crosshair_blades.get() != blades:
                    app.crosshair_controls[0]["switch"].invoke()
                app.angle_text["fov"].set(str(angle))
                app.set_crosshair_angle("fov")
                app.angle_text["optical"].set(str(image_angle))
                app.set_crosshair_angle("optical")
                pixels = repaint()
                check_rays(pixels, blades, angle)
                self.assertEqual(app.fov_crosshair_center(), fixed_fov)
        # Hiding FOV keeps the marker and its current shared shape/angle.
        x, y = app.crosshair_x, app.crosshair_y
        marker = pixels[y - 8:y + 9, x - 8:x + 9].copy()
        app.fov_checkbox.invoke()
        pixels = repaint()
        np.testing.assert_array_equal(pixels[y - 8:y + 9, x - 8:x + 9], marker)
        np.testing.assert_array_equal(app.last_frame, raw)
        # Real edge detection and alignment drive both references automatically.
        for blades, angle in ((3, 19), (4, 33)):
            self.load_fixture(app, spider_fixture(blades, angle))
            app.start_detection()
            self.wait_until(lambda: app.detection is not None and not app.analysis_busy)
            app.set_fov_crosshair_center((280, 180))
            app.fov_crosshair_visible.set(True)
            app.align_crosshairs()
            self.wait_until(lambda: not app.vane_busy)
            self.assertEqual(app.crosshair_blades.get(), blades)
            pixels = repaint()
            guide = app.display_transform.to_display(app.detection.guide_center)
            for index in range(blades):
                x, y = point(guide, app.crosshair_render_angle() + index * 360 / blades, 4)
                self.assertGreaterEqual(int(pixels[y, x].min()), 180)

    def test_detect_rotates_image_once_and_keeps_crosshair_fixed(self):
        import json
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        raw = spider_fixture(3, 19)
        cv2.circle(raw, (490, 220), 8, (0, 0, 255), -1)
        self.load_fixture(app, raw)
        app.set_fov_crosshair_center((350, 250))
        app.zoom_factor = 2
        app.set_view_center((400, 300))
        for name, value in (("optical", "27.65"), ("fov", "12.34")):
            app.angle_text[name].set(value)
            app.set_crosshair_angle(name)
        app.overlays_visible.set(False)
        def repaint():
            previous = app.video_label.image
            self.wait_until(lambda: app.video_label.image is not previous)
            return np.array(ImageTk.getimage(app.video_label.image))[:, :, :3]
        def direction():
            angle = np.deg2rad(app.crosshair_render_angle())
            vector = np.array(app.display_transform.to_display_vector((np.cos(angle), np.sin(angle))))
            return vector / np.linalg.norm(vector)
        repaint()
        center = app.fov_crosshair_center()
        before = app.display_transform
        pivot = before.to_display(center)
        ray = direction()
        landmark = before.to_display((490, 220))
        app.start_detection()
        self.wait_until(lambda: app.detection is not None and not app.analysis_busy)
        pixels = repaint()
        self.assertEqual(app.crosshair_blades.get(), 3)
        self.assertEqual(app.crosshair_angles["fov"], 12.34)
        self.assertEqual(app.angle_text["fov"].get(), "12.34")
        self.assertNotEqual(app.crosshair_angles["optical"], 27.65)
        self.assertEqual(app.fov_crosshair_center(), center)
        self.assertEqual(app.zoom_factor, 2)
        np.testing.assert_allclose(app.display_transform.to_display(center), pivot, atol=1e-8)
        np.testing.assert_allclose(direction(), ray, atol=1e-8)
        # Vanes and fixed crosshair now have matching displayed directions.
        angle = np.deg2rad(app.vane_detection.angle_deg)
        vector = np.array(app.display_transform.to_display_vector((np.cos(angle), np.sin(angle))))
        np.testing.assert_allclose(vector / np.linalg.norm(vector), ray, atol=.001)
        point = app.display_transform.to_display((490, 220))
        self.assertGreater(np.linalg.norm(np.subtract(point, landmark)), 2)
        x, y = (round(v) for v in point)
        self.assertTrue(red_pixels(pixels[y, x]))
        matrix = app.display_transform.image_matrix().copy()
        measured = app.detection.observations
        app.align_crosshairs()
        self.wait_until(lambda: not app.vane_busy)
        after = repaint()
        np.testing.assert_array_equal(after, pixels)
        np.testing.assert_allclose(app.display_transform.image_matrix(), matrix, atol=1e-8)
        self.assertEqual(app.detection.observations, measured)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "aligned.png"
            app.export_capture(path)
            metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["crosshair"]["angle_deg"], 12.34)
            self.assertEqual(metadata["crosshair"]["rotation_compensation_deg"], app.crosshair_rotation_offset)
            self.assertEqual(metadata["crosshair"]["render_angle_deg"], app.crosshair_render_angle())
            np.testing.assert_array_equal(cv2.imread(str(path)), raw)
        guides = app.detection.guide_center
        app.reset_view()
        repaint()
        self.assertEqual(app.crosshair_rotation_offset, 0)
        self.assertEqual(app.crosshair_angles, {"optical": 0, "fov": 0})
        self.assertEqual(app.detection.guide_center, guides)
        # A reset or angle edit during detection supersedes its automatic rotation.
        app.start_detection()
        app.reset_view()
        self.wait_until(lambda: not app.analysis_busy)
        self.assertEqual(app.crosshair_angles["optical"], 0)
        self.assertEqual(app.crosshair_rotation_offset, 0)
        app.start_detection()
        app.angle_text["fov"].set("43.21")
        app.set_crosshair_angle("fov")
        self.wait_until(lambda: not app.analysis_busy)
        self.assertEqual(app.crosshair_angles, {"optical": 0, "fov": 43.21})
        self.assertEqual(app.crosshair_rotation_offset, 0)
        np.testing.assert_array_equal(app.last_frame, raw)

    def test_rotation_step_buttons_branding_and_view_order(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        self.assertEqual(self.root.title(), "Advanced Astro Collimator")
        self.load_fixture(app, np.zeros((600, 800, 3), np.uint8))
        app.notebook.select(app.manual_panel)
        self.root.update()
        controls = app.crosshair_controls[0]
        app.fov_checkbox.invoke()
        center = app.fov_crosshair_center()
        guides = (app.crosshair_x, app.crosshair_y)
        for name in ("optical", "fov"):
            minus, plus = controls["buttons"][name]
            app.angle_text[name].set("0.00")
            app.set_crosshair_angle(name)
            minus.invoke()
            self.assertEqual(app.crosshair_angles[name], 359.99)
            plus.invoke()
            self.assertEqual(app.crosshair_angles[name], 0)
            app.angle_text[name].set("12.34")
            plus.invoke()
            self.assertEqual(app.crosshair_angles[name], 12.35)
            minus.invoke()
            self.assertEqual(app.crosshair_angles[name], 12.34)
            app.angle_text[name].set("nan")
            plus.invoke()
            self.assertEqual(app.crosshair_angles[name], 12.35)
        self.assertEqual(app.fov_crosshair_center(), center)
        # View changes preserve the raw guide center, even as its display moves.
        np.testing.assert_allclose(app.current_view_transform().to_original((app.crosshair_x, app.crosshair_y)),
                                   (400, 300), atol=1)
        app.fov_checkbox.invoke()
        for button in controls["buttons"]["fov"]:
            self.assertTrue(button.instate(["disabled"]))
            button.invoke()
        self.assertEqual(app.crosshair_angles["fov"], 12.35)
        self.assertFalse(controls["buttons"]["optical"][1].instate(["disabled"]))
        for size in ("1280x720", "1024x768"):
            self.root.geometry(size)
            for tab in (app.review_panel, app.manual_panel):
                app.notebook.select(tab)
                self.root.update()
                self.assertLess(app.view_reset_button.winfo_rooty(), controls["panel"].winfo_rooty())
                self.assertLess(controls["panel"].winfo_rooty() + controls["panel"].winfo_height(), app.notebook.winfo_rooty())
                labels = [widget.cget("text") for widget in controls["entries"]["fov"].master.winfo_children()
                          if widget.winfo_class() == "TLabel"]
                self.assertIn("Rotation", labels)
                for name, label in (("fov", "Rotation"), ("optical", "Image rotation")):
                    entry = controls["entries"][name]
                    minus, plus = controls["buttons"][name]
                    text_widgets = {widget.cget("text"): widget for widget in entry.master.winfo_children()
                                    if widget.winfo_class() == "TLabel"}
                    ordered = (minus, text_widgets[label], entry, text_widgets["°"], plus)
                    for left, right in zip(ordered, ordered[1:]):
                        self.assertLessEqual(left.winfo_rootx() + left.winfo_width(), right.winfo_rootx())
                        self.assertLess(abs((left.winfo_rooty() + left.winfo_height() / 2)
                                            - (right.winfo_rooty() + right.winfo_height() / 2)), 2)
                for button in (*controls["buttons"]["fov"], *controls["buttons"]["optical"]):
                    self.assertTrue(button.winfo_ismapped())
                    self.assertLessEqual(button.winfo_rootx() + button.winfo_width(), app.sidebar.winfo_rootx() + app.sidebar.winfo_width())
        import subprocess
        import sys
        result = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve().parents[2] / "start.py"), "--version"],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("Advanced Astro Collimator "))
