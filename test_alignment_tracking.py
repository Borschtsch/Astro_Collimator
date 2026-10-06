from dataclasses import replace
import unittest

from app_options import TelescopeProfile
from collimation_guidance import alignment_advice
from edge_tracking import merge_tracking
from feature_detection import DetectionResult, EdgeCandidate, FEATURE_NAMES, concentric_guides


def measured_view(shift=(0, 0)):
    edges = tuple(EdgeCandidate(index + 1, (200 + shift[0], 200 + shift[1]), (radius, radius), 0,
                                kind="mark_round" if index == 3 else "pupil_round" if index == 4 else "boundary",
                                fit_quality=.95, coverage=1, residual=.005, edge_width=4)
                  for index, radius in enumerate((150, 100, 70, 5, 8)))
    return concentric_guides(DetectionResult((500, 500), edges,
                            dict(zip(FEATURE_NAMES, (1, 2, 3, 4, 5))), (), 10))


def modify_observation(result, role, **values):
    candidate_id = result.suggested[role]
    observations = tuple(replace(edge, **values) if edge.id == candidate_id else edge for edge in result.observations)
    return concentric_guides(replace(result, candidates=observations, observations=observations, guide_center=None))


class AlignmentTests(unittest.TestCase):
    def pupil_view(self, mark=True, pupil_shift=(0, 0)):
        result = measured_view()
        observations = tuple(edge for edge in result.observations if edge.id != 5 and (mark or edge.id != 4))
        pupil = EdgeCandidate(5, (200 + pupil_shift[0], 200 + pupil_shift[1]), (8, 8), 0,
                              kind="pupil_round", fit_quality=.95, coverage=1, edge_width=3)
        observations += (pupil,)
        selections = dict(result.suggested)
        if not mark:
            selections.pop("Center mark")
        selections["Camera pupil"] = pupil.id
        return concentric_guides(replace(result, candidates=observations, observations=observations,
                                          suggested=selections, guide_center=None))

    def test_absent_or_unknown_mark_does_not_block_pupil_analysis(self):
        result = self.pupil_view(mark=False)
        for shape in ("None", "Unknown"):
            advice = alignment_advice(result, result.suggested, TelescopeProfile(center_mark_shape=shape))
            self.assertEqual(advice.stage, "verification")
            self.assertFalse(advice.metrics["center_mark_present"])
            self.assertTrue(advice.metrics["camera_pupil_present"])
            self.assertIn("rough", advice.instruction)
            self.assertIn("star test", advice.instruction)
        known = alignment_advice(result, result.suggested, TelescopeProfile(center_mark_shape="Ring"))
        self.assertEqual(known.stage, "capture")
        self.assertIn("Center mark", known.metrics["missing"])

    def test_primary_pupil_error_uses_actual_pupil_position_not_shared_guides(self):
        result = self.pupil_view(pupil_shift=(12, -10))
        self.assertEqual({edge.center for edge in result.candidates}, {(200, 200)})
        advice = self.advice(result)
        self.assertEqual(advice.stage, "primary_tilt")
        self.assertIn("left and down", advice.instruction)
        self.assertIn("center mark", advice.instruction)
        self.assertEqual(advice.metrics["pupil_from_primary_reference_px"], (12, -10))
        self.assertEqual(self.advice(concentric_guides(result, (212, 190))), advice)

    def test_unmarked_primary_uses_approximate_rim_reference_for_tilt(self):
        result = self.pupil_view(mark=False, pupil_shift=(12, -10))
        advice = alignment_advice(result, result.suggested, TelescopeProfile(center_mark_shape="None"))
        self.assertEqual(advice.stage, "primary_tilt")
        self.assertIn("approximate", advice.instruction)
        self.assertIn("estimated primary rim center", advice.instruction)
        self.assertEqual(advice.metrics["primary_reference"], "Primary rim center (approximate)")
        result = modify_observation(result, "Primary reflection", center=(213, 187))
        advice = alignment_advice(result, result.suggested, TelescopeProfile(center_mark_shape="None"))
        self.assertEqual(advice.stage, "secondary_tilt")
        self.assertIn("No center mark", advice.instruction)

    def test_missing_or_soft_pupil_requests_capture_improvement_without_fake_success(self):
        result = measured_view()
        result = replace(result, candidates=result.candidates[:-1], observations=result.observations[:-1],
                         suggested={role: value for role, value in result.suggested.items() if role != "Camera pupil"})
        advice = self.advice(result)
        self.assertEqual(advice.stage, "capture")
        self.assertIn("lens opening", advice.instruction)
        soft = modify_observation(self.pupil_view(), "Camera pupil", edge_width=18)
        self.assertEqual(self.advice(soft).stage, "capture")

    def advice(self, result, selections=None):
        return alignment_advice(result, selections if selections is not None else result.suggested, TelescopeProfile())

    def test_missing_roles_request_capture_improvement_and_manual_addition(self):
        result = measured_view()
        advice = self.advice(result, {"Primary reflection": 3})
        self.assertEqual(advice.stage, "capture")
        for word in ("illumination", "focus", "manually", "Widen"):
            self.assertIn(word, advice.instruction)
        self.assertNotIn("tilt", advice.instruction)

    def test_secondary_shape_is_measured_before_projecting_round_guides(self):
        result = modify_observation(measured_view(), "Secondary edge", axes=(100, 88))
        self.assertEqual({edge.eccentricity for edge in result.candidates}, {0})
        advice = self.advice(result)
        self.assertEqual(advice.stage, "secondary_shape")
        self.assertIn("rotation", advice.instruction)

    def test_similar_mirror_ovals_request_camera_seating_before_mirror_changes(self):
        result = modify_observation(measured_view(), "Secondary edge", axes=(100, 85), angle_deg=20)
        result = modify_observation(result, "Primary reflection", axes=(70, 59.5), angle_deg=25)
        advice = self.advice(result)
        self.assertEqual(advice.stage, "camera")
        self.assertIn("camera", advice.instruction)

    def test_secondary_placement_moves_the_apparent_face_toward_the_focuser(self):
        result = modify_observation(measured_view(), "Secondary edge", center=(216, 190))
        advice = self.advice(result)
        self.assertEqual(advice.stage, "secondary_placement")
        self.assertIn("left and down", advice.instruction)
        self.assertIn("not center the dark reflected shadow", advice.instruction)

    def test_primary_center_mark_error_requests_secondary_tilt(self):
        result = modify_observation(measured_view(), "Center mark", center=(190, 212))
        advice = self.advice(result)
        self.assertEqual(advice.stage, "secondary_tilt")
        self.assertIn("right and up", advice.instruction)
        self.assertNotIn("primary tilt", advice.instruction)

    def test_concentric_references_do_not_certify_primary_alignment(self):
        advice = self.advice(measured_view())
        self.assertEqual(advice.stage, "verification")
        self.assertIn("star test", advice.instruction)
        self.assertNotIn("aligned", advice.instruction)

    def test_dragging_the_guides_cannot_manufacture_measured_alignment(self):
        result = modify_observation(measured_view(), "Center mark", center=(190, 212))
        before = self.advice(result)
        result = concentric_guides(result, (190, 212))
        self.assertEqual(self.advice(result), before)

    def test_soft_partial_clipped_or_held_evidence_defers_mirror_adjustment(self):
        for role, values in (("Primary reflection", {"edge_width": 18}),
                             ("Secondary edge", {"coverage": .75}),
                             ("Focuser edge", {"clipped": True}),
                             ("Secondary edge", {"provenance": "manual_hold"})):
            with self.subTest(role=role, values=values):
                result = modify_observation(measured_view(), role, **values)
                self.assertEqual(self.advice(result).stage, "capture")

    def test_present_guide_without_a_measurement_requests_reacquisition(self):
        result = measured_view()
        result = replace(result, observations=result.observations[:-1])
        self.assertEqual(self.advice(result).stage, "capture")


class TrackingTests(unittest.TestCase):
    def test_manual_camera_pupil_holds_and_reacquires_without_stealing_the_mark(self):
        old = AlignmentTests().pupil_view()
        manual = replace(old.observations[-1], kind="pupil_manual", provenance="manual_circle")
        fresh = replace(old, candidates=old.candidates[:-1], observations=old.observations[:-1],
                        suggested={role: value for role, value in old.suggested.items() if role != "Camera pupil"})
        held = merge_tracking(old, fresh, {"Camera pupil": manual})
        self.assertEqual(held.held, ("Camera pupil",))
        self.assertEqual(held.selections["Center mark"], 4)
        self.assertNotEqual(held.selections["Center mark"], held.selections["Camera pupil"])
        recovered = merge_tracking(held.result, old, held.manual_references)
        self.assertEqual(recovered.recovered, ("Camera pupil",))
        self.assertEqual(recovered.selections["Camera pupil"], 5)

    def test_unmatched_manual_circle_keeps_radius_and_moves_with_the_master(self):
        old = measured_view()
        manual = replace(old.observations[1], axes=(120, 120), provenance="manual_circle")
        fresh = measured_view((10, -5))
        # Existing secondary is too small to be a good replacement.
        fresh = modify_observation(fresh, "Secondary edge", axes=(75, 75))
        update = merge_tracking(old, fresh, {"Secondary edge": manual})
        self.assertEqual(update.held, ("Secondary edge",))
        guide = update.result.candidate(update.selections["Secondary edge"])
        self.assertEqual(guide.radius, 120)
        self.assertEqual(guide.center, (210, 195))
        self.assertEqual({edge.center for edge in update.result.candidates}, {(210, 195)})
        self.assertEqual(update.manual_references["Secondary edge"].provenance, "manual_hold")

    def test_a_good_candidate_replaces_manual_geometry_and_can_be_held_again(self):
        old = measured_view()
        manual = replace(old.observations[1], provenance="manual_circle")
        update = merge_tracking(old, measured_view((10, 0)), {"Secondary edge": manual})
        self.assertEqual(update.recovered, ("Secondary edge",))
        self.assertFalse(update.held)
        self.assertIsNotNone(update.manual_references["Secondary edge"].fit_quality)
        fresh = measured_view((20, 0))
        fresh = replace(fresh, observations=tuple(edge for edge in fresh.observations if edge.id != 2),
                        candidates=tuple(edge for edge in fresh.candidates if edge.id != 2),
                        suggested={name: value for name, value in fresh.suggested.items() if name != "Secondary edge"})
        again = merge_tracking(update.result, fresh, update.manual_references)
        self.assertEqual(again.held, ("Secondary edge",))
        self.assertEqual(again.result.candidate(again.selections["Secondary edge"]).center, (220, 200))

    def test_soft_or_distant_candidates_do_not_replace_manual_circle(self):
        old = measured_view()
        manual = old.observations[1]
        for values in ({"edge_width": 18}, {"center": (270, 260)}, {"coverage": .3}, {"fit_quality": .2}):
            fresh = modify_observation(measured_view(), "Secondary edge", **values)
            self.assertEqual(merge_tracking(old, fresh, {"Secondary edge": manual}).held, ("Secondary edge",))

    def test_manual_point_reacquires_mark_without_requiring_a_fictitious_radius(self):
        old = measured_view()
        manual = replace(old.observations[3], axes=(1, 1), kind="mark_point", provenance="manual_point")
        update = merge_tracking(old, measured_view(), {"Center mark": manual})
        self.assertEqual(update.recovered, ("Center mark",))

    def test_manual_circle_does_not_steal_another_assigned_element(self):
        old = measured_view()
        manual = replace(old.observations[1], axes=(70, 70))
        update = merge_tracking(old, measured_view(), {"Secondary edge": manual})
        self.assertEqual(update.held, ("Secondary edge",))
        self.assertNotEqual(update.selections["Secondary edge"], update.selections["Primary reflection"])

    def test_manual_center_offset_persists_without_erasing_real_centers(self):
        old = concentric_guides(measured_view(), (205, 202))
        fresh = measured_view((10, 0))
        update = merge_tracking(old, fresh, {}, center_offset=(5, 2))
        self.assertEqual(update.result.guide_center, (215, 202))
        self.assertEqual(update.result.observations[0].center, (210, 200))

    def test_complete_detection_loss_keeps_manual_roles_only_with_unique_ids(self):
        old = measured_view()
        blank = DetectionResult((500, 500), (), {}, ("No rims",), 1)
        update = merge_tracking(old, blank, {"Secondary edge": old.observations[1], "Center mark": old.observations[3]})
        self.assertEqual(set(update.selections), {"Secondary edge", "Center mark"})
        self.assertEqual(len({edge.id for edge in update.result.candidates}), len(update.result.candidates))
        self.assertEqual({edge.center for edge in update.result.candidates}, {update.result.guide_center})


if __name__ == "__main__":
    unittest.main()
