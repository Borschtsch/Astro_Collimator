from dataclasses import replace
import unittest
from pathlib import Path

import cv2
import numpy as np

from source.feature_detection import (DisplayTransform, EdgeCandidate, DetectionResult, FEATURE_NAMES, _analyze_observations as analyze_frame,
                               as_focuser_circle, circle_from_points, draw_detection)


from tests.fixtures.images import TEST_IMAGES, optical_fixture, pupil_fixture


class DetectionTests(unittest.TestCase):
    def test_pupil_is_distinct_from_mark_and_secondary_shadow_at_raw_scales(self):
        for scale in (1, 3):
            result = analyze_frame(pupil_fixture((800 * scale, 600 * scale)), "Ring")
            pupil = result.candidate(result.suggested["Camera pupil"])
            mark = result.candidate(result.suggested["Center mark"])
            self.assertNotEqual(pupil.id, mark.id)
            self.assertEqual(pupil.kind, "pupil_round")
            np.testing.assert_allclose(pupil.center, np.array((405, 285)) * scale, atol=3 * scale)
            self.assertAlmostEqual(pupil.radius, 12 * scale, delta=3 * scale)
            np.testing.assert_allclose(mark.center, np.array((447, 330)) * scale, atol=3 * scale)
            self.assertLess(pupil.radius, 20 * scale)  # The shadow radius is 36.

    def test_unmarked_primary_still_detects_pupil_and_three_edges(self):
        result = analyze_frame(pupil_fixture(mark=False), "None")
        self.assertEqual(set(result.suggested), set(FEATURE_NAMES) - {"Center mark"})
        self.assertEqual(result.candidate(result.suggested["Camera pupil"]).kind, "pupil_round")
        # Shape restriction applies to the mirror mark, not a round lens pupil.
        triangle = analyze_frame(pupil_fixture(mark=False), "Triangle")
        self.assertIn("Camera pupil", triangle.suggested)

    def test_solid_secondary_shadow_or_lone_dot_is_not_invented_as_a_pupil(self):
        for frame in (pupil_fixture(mark=False, opening=False), optical_fixture()):
            self.assertNotIn("Camera pupil", analyze_frame(frame, "None").suggested)

    def test_tight_round_outer_rim_is_assigned_but_thin_primary_sides_are_not(self):
        for radius in (170, 154):
            frame = np.full((400, 400, 3), 20, np.uint8)
            cv2.circle(frame, (200, 200), radius, (90,) * 3, -1, cv2.LINE_AA)
            cv2.circle(frame, (200, 200), 150, (210,) * 3, -1, cv2.LINE_AA)
            cv2.circle(frame, (200, 200), 20, (20,) * 3, -1, cv2.LINE_AA)
            result = analyze_frame(frame, "Ring")
            self.assertIn("Primary reflection", result.suggested)
            self.assertNotIn("Secondary edge", result.suggested)
            if radius == 170:
                focuser = result.candidate(result.suggested["Focuser edge"])
                self.assertAlmostEqual(focuser.radius, radius, delta=2)
                self.assertEqual(focuser.axes[0], focuser.axes[1])
            else:
                self.assertNotIn("Focuser edge", result.suggested)

    def test_independent_centers_duplicate_rims_and_raw_resolution(self):
        for size in ((800, 600), (2400, 1800)):
            with self.subTest(size=size):
                result = analyze_frame(optical_fixture(size))
                self.assertEqual(result.image_size, size)
                self.assertEqual(len(result.candidates), 4)
                self.assertEqual(set(result.suggested), set(FEATURE_NAMES[:4]))
                ratio = size[0] / 800
                for role, center, radius in zip(FEATURE_NAMES, ((400, 300), (412, 296), (418, 300), (421, 302)),
                                                (250, 200, 160, 10)):
                    edge = result.candidate(result.suggested[role])
                    np.testing.assert_allclose(edge.center, np.array(center) * ratio, atol=2 * ratio)
                    self.assertAlmostEqual(edge.radius, radius * ratio, delta=2 * ratio)
                    self.assertGreater(edge.coverage, 0.8)

    def test_elliptical_edges_and_triangle_mark(self):
        result = analyze_frame(optical_fixture(ellipse=True, triangle=True, circular_focuser=True), "Triangle")
        self.assertEqual(set(result.suggested), set(FEATURE_NAMES[:4]))
        secondary = result.candidate(result.suggested["Secondary edge"])
        self.assertAlmostEqual(secondary.axes[1] / secondary.axes[0], 0.85, delta=0.02)
        self.assertAlmostEqual(secondary.angle_deg, 18, delta=2)
        self.assertEqual(result.candidate(result.suggested["Center mark"]).kind, "mark_triangle")

    def test_unusable_missing_and_clipped_edges_keep_uncertainty(self):
        blank = analyze_frame(np.full((300, 400, 3), 90, dtype=np.uint8))
        self.assertFalse(blank.candidates)
        self.assertIn("Low contrast", blank.messages[0])
        frame = np.full((400, 400, 3), 20, np.uint8)
        cv2.circle(frame, (200, 200), 140, (180,) * 3, -1)
        only_one = analyze_frame(frame)
        self.assertFalse(only_one.suggested)
        self.assertEqual(len(only_one.candidates), 1)
        clipped = np.full((400, 400, 3), 20, np.uint8)
        cv2.circle(clipped, (30, 200), 140, (180,) * 3, -1)
        result = analyze_frame(clipped)
        self.assertEqual(len(result.candidates), 1)
        rim = result.candidates[0]
        self.assertTrue(rim.clipped)
        self.assertLess(rim.coverage, 0.85)
        self.assertGreater(rim.coverage, 0.48)
        np.testing.assert_allclose(rim.center, (30, 200), atol=3)
        self.assertAlmostEqual(rim.radius, 140, delta=3)
        self.assertTrue(rim.support_bins)
        self.assertFalse(result.suggested)
        self.assertIn("Zoom", " ".join(result.messages).replace("zoom", "Zoom"))
        noise = np.random.default_rng(54).integers(0, 256, (300, 400, 3), dtype=np.uint8)
        self.assertFalse(analyze_frame(noise).suggested)

    def test_moderate_noise_and_blur_preserve_usable_edges(self):
        frame = optical_fixture().astype(np.float32)
        frame += np.random.default_rng(5).normal(0, 4, frame.shape)
        frame = cv2.GaussianBlur(np.clip(frame, 0, 255).astype(np.uint8), (5, 5), 1)
        result = analyze_frame(frame)
        self.assertEqual(set(result.suggested), set(FEATURE_NAMES[:4]))

    def test_missing_secondary_keeps_the_primary_and_focuser_visible(self):
        frame = np.full((600, 800, 3), 25, np.uint8)
        cv2.circle(frame, (400, 300), 250, (120,) * 3, -1, cv2.LINE_AA)
        cv2.circle(frame, (418, 300), 160, (190,) * 3, -1, cv2.LINE_AA)
        cv2.circle(frame, (421, 302), 10, (20,) * 3, -1, cv2.LINE_AA)
        result = analyze_frame(frame)
        self.assertIn("Primary reflection", result.suggested)
        self.assertIn("Focuser edge", result.suggested)
        self.assertNotIn("Secondary edge", result.suggested)
        self.assertEqual(len(set(result.suggested.values())), len(result.suggested))

    def test_dim_capture_uses_relative_face_brightness(self):
        frame = (optical_fixture().astype(float) * .25).astype(np.uint8)
        result = analyze_frame(frame)
        self.assertTrue(set(FEATURE_NAMES[:3]) <= set(result.suggested))

    def test_a_primary_and_its_dark_pupil_do_not_form_three_optical_layers(self):
        frame = np.full((400, 400, 3), 20, np.uint8)
        cv2.circle(frame, (200, 200), 140, (190,) * 3, -1, cv2.LINE_AA)
        cv2.circle(frame, (200, 200), 35, (20,) * 3, -1, cv2.LINE_AA)
        result = analyze_frame(frame)
        self.assertEqual(set(result.suggested), {"Primary reflection"})
        self.assertAlmostEqual(result.candidate(result.suggested["Primary reflection"]).radius, 140, delta=3)

    def test_eccentricity_limit_rejects_stretched_rims_and_accepts_raster_circles(self):
        frame = np.full((500, 500, 3), 20, np.uint8)
        cv2.ellipse(frame, (250, 250), (160, 100), 25, 0, 360, (180,) * 3, -1, cv2.LINE_AA)
        self.assertFalse(analyze_frame(frame).candidates)
        loose = analyze_frame(frame, max_eccentricity=0.85)
        self.assertEqual(len(loose.candidates), 1)
        np.testing.assert_allclose(loose.candidates[0].center, (250, 250), atol=2)
        self.assertAlmostEqual(loose.candidates[0].eccentricity, 0.78, delta=0.03)
        strict = analyze_frame(optical_fixture(ellipse=True), max_eccentricity=0.25)
        self.assertFalse(strict.suggested)
        self.assertFalse(any(edge.kind == "boundary" for edge in strict.candidates))
        self.assertTrue(set(FEATURE_NAMES[:3]) <= set(analyze_frame(optical_fixture(), max_eccentricity=0).suggested))
        for invalid in (-0.1, 0.9, float("nan"), None, True):
            with self.assertRaises(ValueError):
                analyze_frame(frame, max_eccentricity=invalid)

    def test_an_interior_short_arc_cannot_invent_a_complete_rim(self):
        frame = np.full((500, 500, 3), 20, np.uint8)
        cv2.ellipse(frame, (250, 250), (160, 160), 0, 0, 160, (180,) * 3, 4, cv2.LINE_AA)
        self.assertFalse(analyze_frame(frame).candidates)

    def test_missing_support_stays_empty_even_after_confirmation(self):
        edge = EdgeCandidate(1, (200, 200), (100, 100), 0, coverage=0.25,
                             support_bins=tuple(range(18, 36)))
        result = DetectionResult((400, 400), (edge,), {}, (), 0)
        mapping = DisplayTransform.for_image((400, 400), 1, 400, 400)
        for confirmed in (set(), {"Secondary edge"}):
            canvas = np.zeros((400, 400, 3), np.uint8)
            draw_detection(canvas, result, {"Secondary edge": 1}, confirmed, mapping)
            self.assertFalse(canvas[197:204, 297:304].any())
            self.assertTrue(canvas[297:304, 197:204].any())

    def test_circular_focuser_is_extrapolated_while_other_missing_arcs_stay_empty(self):
        for frame in (optical_fixture(ellipse=True, circular_focuser=True), optical_fixture()[:, 200:]):
            result = analyze_frame(frame)
            edge = result.candidate(result.suggested["Focuser edge"])
            self.assertEqual(edge.axes[0], edge.axes[1])
            if frame.shape[1] == 600:
                self.assertTrue(edge.clipped)
                np.testing.assert_allclose(edge.center, (200, 300), atol=3)
                self.assertAlmostEqual(edge.radius, 250, delta=3)
        edge = EdgeCandidate(1, (200, 200), (100, 100), 0, coverage=0.25,
                             support_bins=tuple(range(18, 36)))
        result = DetectionResult((400, 400), (edge,), {}, (), 0)
        mapping = DisplayTransform.for_image((400, 400), 1, 400, 400)
        for confirmed in (set(), {"Focuser edge"}):
            canvas = np.zeros((400, 400, 3), np.uint8)
            draw_detection(canvas, result, {"Focuser edge": 1}, confirmed, mapping)
            self.assertTrue(canvas[197:204, 297:304].any())
            # Fine predicted dashes still have actual gaps after confirmation.
            self.assertFalse(canvas[207:211, 297:301].any())

    def test_manual_focuser_constraint_fits_a_circle_and_drops_ellipse_fit_score(self):
        edge = EdgeCandidate(3, (220, 190), (100, 90), 20, fit_quality=0.9,
                             coverage=0.75, support_bins=tuple(range(54)))
        constrained = as_focuser_circle(edge, (500, 400))
        self.assertEqual(constrained.axes[0], constrained.axes[1])
        self.assertEqual(constrained.id, edge.id)
        self.assertEqual(constrained.provenance, "focuser_circle_estimate")
        self.assertIsNone(constrained.fit_quality)
        self.assertIsNone(constrained.residual)
        self.assertTrue(constrained.support_bins)
        self.assertTrue(np.isfinite(constrained.center).all())

    def test_panned_transform_clamps_to_image_and_keeps_raw_coordinates(self):
        for center in ((-1000, -1000), (10000, 10000), (140, 230)):
            mapping = DisplayTransform.for_image((641, 481), 2, 700, 500, center)
            self.assertGreaterEqual(mapping.crop_x, 0)
            self.assertGreaterEqual(mapping.crop_y, 0)
            self.assertLessEqual(mapping.crop_x + mapping.crop_width, 641)
            self.assertLessEqual(mapping.crop_y + mapping.crop_height, 481)
            point = (mapping.crop_x + 42, mapping.crop_y + 65)
            np.testing.assert_allclose(mapping.to_original(mapping.to_display(point)), point, atol=1e-8)
        full = DisplayTransform.for_image((641, 481), 1, center=(0, 0))
        self.assertEqual((full.crop_x, full.crop_y), (0, 0))

    def test_bad_input_is_rejected_and_manual_circle_checks_geometry(self):
        for frame in (None, np.zeros((20, 20, 3), np.uint8), np.zeros((100, 100), np.uint8),
                      np.zeros((100, 100, 3), float)):
            with self.assertRaises(ValueError):
                analyze_frame(frame)
        edge = circle_from_points(((200, 100), (100, 200), (0, 100)), 8, (400, 300))
        np.testing.assert_allclose(edge.center, (100, 100), atol=1e-6)
        self.assertEqual(edge.radius, 100)
        self.assertEqual(edge.provenance, "manual_circle")
        self.assertIsNone(edge.fit_quality)
        for points in (((10, 10), (20, 20), (30, 30)), ((-1, 10), (20, 20), (30, 30)),
                       ((10, 10), (10, 10), (10, 10))):
            with self.assertRaises(ValueError):
                circle_from_points(points, 8, (400, 300))

    def test_crop_zoom_round_trip_and_independent_overlay_centers(self):
        for size in ((1921, 1081), (641, 481), (600, 900)):
            for zoom in (1, 1.3, 3):
                mapping = DisplayTransform.for_image(size, zoom, 700, 500)
                point = (size[0] * 0.55, size[1] * 0.48)
                np.testing.assert_allclose(mapping.to_original(mapping.to_display(point)), point, atol=1e-8)
        result = analyze_frame(optical_fixture())
        canvas = np.zeros((600, 800, 3), np.uint8)
        draw_detection(canvas, result, result.suggested, {"Secondary edge"},
                       DisplayTransform.for_image((800, 600), 1, 800, 600), False)
        self.assertTrue(canvas[296, 412].any())
        self.assertTrue(canvas[300, 400].any())

    def test_disconnected_rims_survive_spider_lines_and_obstructions(self):
        frame = optical_fixture()
        frame[70:260, 395:410] = 25
        frame[350:500, 450:510] = 25
        result = analyze_frame(frame)
        for role, center, radius in zip(FEATURE_NAMES, ((400, 300), (412, 296), (418, 300)), (250, 200, 160)):
            edge = result.candidate(result.suggested[role])
            np.testing.assert_allclose(edge.center, center, atol=4)
            self.assertAlmostEqual(edge.radius, radius, delta=4)

    def test_moderate_blur_is_tolerated_and_excessive_blur_requests_focus(self):
        moderate = analyze_frame(cv2.GaussianBlur(optical_fixture(), (0, 0), 3))
        self.assertTrue(set(FEATURE_NAMES[:3]) <= set(moderate.suggested))
        self.assertNotIn("too blurry", " ".join(moderate.messages))
        severe = analyze_frame(cv2.GaussianBlur(optical_fixture(), (0, 0), 10))
        self.assertFalse(severe.suggested)
        self.assertIn("Improve camera focus", " ".join(severe.messages))
        self.assertTrue(any((edge.edge_width or 0) >= 14 for edge in severe.candidates))

    def test_faint_rims_and_straight_lines_do_not_share_a_result(self):
        faint = np.clip(optical_fixture().astype(float) * 0.2 + 70, 0, 255).astype(np.uint8)
        result = analyze_frame(faint)
        self.assertTrue(set(FEATURE_NAMES[:3]) <= set(result.suggested))
        lines = np.full((400, 400, 3), 20, np.uint8)
        for x in (40, 100, 170, 250, 320):
            cv2.line(lines, (x, 0), (x, 399), (200,) * 3, 7)
        negative = analyze_frame(lines)
        self.assertFalse(negative.candidates)
        self.assertFalse(negative.suggested)

    def test_unassigned_overlays_are_bright_and_selection_is_emphasized(self):
        result = analyze_frame(optical_fixture())
        mapping = DisplayTransform.for_image((800, 600), 1, 800, 600)
        standard = np.zeros((600, 800, 3), np.uint8)
        selected = standard.copy()
        draw_detection(standard, result, {}, set(), mapping)
        draw_detection(selected, result, {}, set(), mapping, selected_id=1)
        vivid = (standard.max(axis=2) > 200) & (np.ptp(standard.astype(int), axis=2) > 60)
        self.assertGreater(np.count_nonzero(vivid), 1200)
        self.assertGreater(np.count_nonzero(selected), np.count_nonzero(standard))


class LocalImageTests(unittest.TestCase):
    """Optional user-supplied photos; no downloads or image modifications."""
    folder = TEST_IMAGES

    @unittest.skipUnless((folder / "images.jpg").exists(), "Local telescope example is absent")
    def test_spider_divided_primary_seeds_the_actual_rims_instead_of_ghosts(self):
        frame = cv2.imdecode(np.frombuffer((self.folder / "images.jpg").read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        result = analyze_frame(frame)
        self.assertTrue(set(FEATURE_NAMES[:3]) <= set(result.suggested))
        for role, bounds in zip(FEATURE_NAMES, ((200, 230), (115, 140), (85, 105))):
            edge = result.candidate(result.suggested[role])
            self.assertGreater(edge.radius, bounds[0])
            self.assertLess(edge.radius, bounds[1])
            np.testing.assert_allclose(edge.center, (212, 224), atol=12)
            self.assertLessEqual(edge.eccentricity, 0.55)
        self.assertFalse(any(edge.radius < 60 and edge.center[1] > 260 for edge in result.candidates))

    @unittest.skipUnless((folder / "image (1).jpg").exists(), "Local telescope example is absent")
    def test_extra_off_center_ellipse_is_rejected_in_small_dark_tube_view(self):
        frame = cv2.imdecode(np.frombuffer((self.folder / "image (1).jpg").read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        result = analyze_frame(frame)
        self.assertTrue(set(FEATURE_NAMES[:3]) <= set(result.suggested))
        self.assertFalse(any(edge.kind == "boundary" and edge.center[1] > 235 for edge in result.candidates))

    @unittest.skipUnless((folder / "image.jpg").exists(), "Local telescope example is absent")
    def test_real_view_has_outer_secondary_and_primary_candidates(self):
        frame = cv2.imdecode(np.frombuffer((self.folder / "image.jpg").read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        result = analyze_frame(frame)
        self.assertTrue(set(FEATURE_NAMES[:3]) <= set(result.suggested))
        # Loose visual bounds identify different rims, not a calibrated accuracy claim.
        for role, bounds in zip(FEATURE_NAMES, ((470, 560), (270, 320), (190, 230))):
            radius = result.candidate(result.suggested[role]).radius
            self.assertGreater(radius, bounds[0])
            self.assertLess(radius, bounds[1])

    @unittest.skipUnless((folder / "post-330586-0-86207400-1592443472.jpg").exists(), "Local telescope example is absent")
    def test_real_soft_outer_rim_requests_focus_and_a_wider_view(self):
        frame = cv2.imdecode(np.frombuffer((self.folder / "post-330586-0-86207400-1592443472.jpg").read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        result = analyze_frame(frame)
        self.assertTrue(any(edge.clipped and edge.radius > 300 for edge in result.candidates))
        self.assertIn("Improve camera focus", " ".join(result.messages))
        self.assertIn("wider-view camera", " ".join(result.messages))

    def load_example(self, name):
        path = self.folder / name
        if not path.exists():
            self.skipTest("Local telescope example is absent")
        return cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), cv2.IMREAD_COLOR)

    def test_annotated_secondary_uses_its_displaced_outer_edge_not_the_primary_rim_side(self):
        result = analyze_frame(self.load_example("collimating-newtonian-secondary.jpg"), "Ring")
        self.assertTrue(set(FEATURE_NAMES[:3]) <= set(result.suggested))
        for role, center, radius in zip(FEATURE_NAMES, ((238, 259), (200, 255), (238, 255)), (210, 164, 139)):
            edge = result.candidate(result.suggested[role])
            np.testing.assert_allclose(edge.center, center, atol=8)
            self.assertAlmostEqual(edge.radius, radius, delta=8)
        self.assertGreater(result.candidate(result.suggested["Secondary edge"]).coverage, .7)

    def test_soft_outer_photo_keeps_all_three_rim_assignments(self):
        result = analyze_frame(self.load_example("post-330586-0-86207400-1592443472.jpg"), "Ring")
        self.assertTrue(set(FEATURE_NAMES[:3]) <= set(result.suggested))
        for role, center, radius in zip(FEATURE_NAMES, ((347, 675), (340, 682), (341, 679)), (351, 232, 206)):
            edge = result.candidate(result.suggested[role])
            np.testing.assert_allclose(edge.center, center, atol=8)
            self.assertAlmostEqual(edge.radius, radius, delta=8)
        focuser = result.candidate(result.suggested["Focuser edge"])
        self.assertEqual(focuser.axes[0], focuser.axes[1])
        self.assertTrue(focuser.clipped)
        self.assertGreaterEqual(focuser.edge_width, 14)
        self.assertIn("Improve camera focus", " ".join(result.messages))

    def test_soft_secondary_photo_keeps_primary_and_round_focuser_without_inventing_secondary(self):
        result = analyze_frame(self.load_example("post-474648-0-99865000-1758374870.jpg"), "Ring")
        for role, center, radius in (("Focuser edge", (432, 664), 401), ("Primary reflection", (445, 656), 171)):
            edge = result.candidate(result.suggested[role])
            np.testing.assert_allclose(edge.center, center, atol=8)
            self.assertAlmostEqual(edge.radius, radius, delta=8)
        self.assertNotIn("Secondary edge", result.suggested)

    def test_small_low_contrast_view_recovers_a_partial_circular_focuser(self):
        result = analyze_frame(self.load_example("images (1).jpg"), "Ring")
        focuser = result.candidate(result.suggested["Focuser edge"])
        self.assertEqual(focuser.axes[0], focuser.axes[1])
        np.testing.assert_allclose(focuser.center, (86, 130), atol=4)
        self.assertAlmostEqual(focuser.radius, 74, delta=4)
        self.assertLess(focuser.coverage, .7)
        self.assertAlmostEqual(result.candidate(result.suggested["Primary reflection"]).radius, 55, delta=3)
        self.assertNotIn("Secondary edge", result.suggested)

    def test_cropped_primary_view_does_not_label_a_reflected_pupil_as_secondary(self):
        result = analyze_frame(self.load_example("2.png"), "Ring")
        primary = result.candidate(result.suggested["Primary reflection"])
        np.testing.assert_allclose(primary.center, (548, 523), atol=8)
        self.assertAlmostEqual(primary.radius, 396, delta=8)
        self.assertNotIn("Secondary edge", result.suggested)
        self.assertNotIn("Focuser edge", result.suggested)

    def test_reported_native_inner_opening_is_a_pupil_not_a_primary_mark(self):
        result = analyze_frame(self.load_example("post-333184-0-47945200-1591447543.jpeg"), "None")
        pupil = result.candidate(result.suggested["Camera pupil"])
        self.assertEqual(pupil.kind, "pupil_round")
        self.assertAlmostEqual(pupil.radius, 16.5, delta=2)
        self.assertNotIn("Center mark", result.suggested)

    def test_reported_tight_native_view_assigns_the_clean_outer_focuser_automatically(self):
        result = analyze_frame(self.load_example("post-333184-0-47945200-1591447543.jpeg"), "Ring")
        focuser = result.candidate(result.suggested["Focuser edge"])
        primary = result.candidate(result.suggested["Primary reflection"])
        self.assertEqual(focuser.axes[0], focuser.axes[1])
        self.assertAlmostEqual(focuser.radius, 145, delta=3)
        np.testing.assert_allclose(focuser.center, (186, 267), atol=3)
        self.assertGreater(focuser.coverage, .95)
        self.assertLess(focuser.radius / primary.radius, 1.3)
        self.assertNotIn("Secondary edge", result.suggested)

    def test_scaled_partial_view_preserves_raw_references_without_forcing_a_secondary(self):
        frame = self.load_example("collimating-newtonian-secondary.jpg")
        large = cv2.resize(frame, None, fx=3, fy=3)
        result = analyze_frame(large, "Ring")
        for role, center, radius in (("Focuser edge", (714, 777), 630),
                                    ("Primary reflection", (715, 764), 416)):
            edge = result.candidate(result.suggested[role])
            np.testing.assert_allclose(edge.center, center, atol=24)
            self.assertAlmostEqual(edge.radius, radius, delta=24)
        # Resampling this partly merged rim leaves insufficient independent
        # evidence. It must remain missing instead of acquiring a nearby rim side.
        self.assertNotIn("Secondary edge", result.suggested)
        self.assertEqual(len({item.id for item in result.candidates}), len(result.candidates))


class SharedCircleGuideTests(unittest.TestCase):
    def test_round_shared_guides_retain_original_independent_observations(self):
        from source.feature_detection import analyze_frame as analyze_guides
        result = analyze_guides(optical_fixture(ellipse=True, circular_focuser=True))
        focuser = result.candidate(result.suggested["Focuser edge"])
        self.assertEqual(result.guide_master_id, focuser.id)
        self.assertEqual(result.guide_center, focuser.center)
        for edge in result.candidates:
            self.assertEqual(edge.center, focuser.center)
            self.assertEqual(edge.axes[0], edge.axes[1])
            self.assertEqual(edge.eccentricity, 0)
            self.assertFalse(edge.support_bins)
            self.assertIsNone(edge.fit_quality)
        self.assertGreater(len({edge.center for edge in result.observations}), 1)
        self.assertTrue(any(edge.axes[0] != edge.axes[1] for edge in result.observations))

    def test_master_is_focuser_else_largest_boundary(self):
        from source.feature_detection import concentric_guides
        small = EdgeCandidate(1, (180, 200), (50, 40), 30)
        large = EdgeCandidate(2, (220, 210), (100, 95), 20)
        result = DetectionResult((400, 400), (small, large), {"Primary reflection": 1}, (), 0)
        guesses = concentric_guides(result)
        self.assertEqual(guesses.guide_master_id, large.id)
        self.assertEqual({edge.center for edge in guesses.candidates}, {large.center})
        focuser = concentric_guides(replace(result, suggested={"Focuser edge": 1}))
        self.assertEqual(focuser.guide_master_id, small.id)
        self.assertEqual({edge.center for edge in focuser.candidates}, {small.center})

    def test_recenter_preserves_radii_and_originals_and_rejects_invalid_centers(self):
        from source.feature_detection import analyze_frame as analyze_guides, concentric_guides
        result = analyze_guides(optical_fixture())
        moved = concentric_guides(result, (-1000, 2000))
        self.assertEqual(moved.guide_center, (0, 599))
        self.assertEqual(moved.observations, result.observations)
        self.assertEqual([edge.radius for edge in moved.candidates], [edge.radius for edge in result.candidates])
        for point in ((float("nan"), 0), (0,), (0, float("inf"))):
            with self.assertRaises(ValueError):
                concentric_guides(result, point)

    def test_every_local_photo_produces_only_concentric_circular_guides(self):
        from source.feature_detection import analyze_frame as analyze_guides
        folder = TEST_IMAGES
        photos = list(folder.iterdir()) if folder.exists() else []
        if not photos:
            self.skipTest("Local photos are absent")
        for path in photos:
            frame = cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                continue
            with self.subTest(image=path.name):
                result = analyze_guides(frame, "Ring")
                self.assertTrue(result.candidates)
                self.assertEqual({edge.center for edge in result.candidates}, {result.guide_center})
                self.assertTrue(all(edge.axes[0] == edge.axes[1] and edge.eccentricity == 0 for edge in result.candidates))

    def test_empty_image_does_not_invent_guides_or_a_master(self):
        from source.feature_detection import analyze_frame as analyze_guides
        result = analyze_guides(np.full((400, 400, 3), 25, np.uint8))
        self.assertFalse(result.candidates)
        self.assertIsNone(result.guide_center)
        self.assertIsNone(result.guide_master_id)


if __name__ == "__main__":
    unittest.main()
