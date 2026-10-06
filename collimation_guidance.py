"""Offline next-action advice from observations, never from concentric overlays."""

from dataclasses import asdict, dataclass
import math

from feature_detection import FEATURE_NAMES, SOFT_EDGE_WIDTH, required_features


@dataclass(frozen=True)
class AlignmentAdvice:
    stage: str
    instruction: str
    metrics: dict

    def to_dict(self):
        return asdict(self)


def image_direction(delta):
    x, y = delta
    parts = []
    if abs(x) > 1:
        parts.append("right" if x > 0 else "left")
    if abs(y) > 1:
        parts.append("down" if y > 0 else "up")
    return " and ".join(parts) or "toward the crosshair"


def alignment_advice(result, selections, profile=None):
    shape = getattr(profile, "center_mark_shape", "Unknown")
    required = required_features(shape)
    missing = [role for role in required
               if result is None or result.candidate(selections.get(role)) is None]
    if missing:
        if missing == ["Camera pupil"]:
            return AlignmentAdvice("capture", "Camera pupil missing: improve illumination/focus or pick the reflected lens opening. The large dark secondary shadow is not the pupil.", {"missing": missing})
        names = {"Focuser edge": "Focuser", "Secondary edge": "Secondary",
                 "Primary reflection": "Primary", "Center mark": "Mark", "Camera pupil": "Pupil"}
        instruction = "Missing " + ", ".join(names[role] for role in missing) + ". Improve illumination/focus or add circles manually."
        if "Focuser edge" in missing:
            instruction += " Widen the camera view."
        return AlignmentAdvice("capture", instruction, {"missing": missing})
    observations = {edge.id: edge for edge in result.observations}
    refs = {role: observations.get(candidate_id) for role, candidate_id in selections.items()}
    unavailable = [role for role in selections if refs.get(role) is None]
    stale = [role for role, edge in refs.items() if edge is not None and edge.provenance == "manual_hold"]
    if unavailable or stale:
        return AlignmentAdvice("capture", "Improve illumination/focus to reacquire held or unmeasured references before adjusting mirrors.",
                               {"unmeasured": unavailable, "held_manual": stale})
    focuser, secondary, primary = (refs[role] for role in FEATURE_NAMES[:3])
    mark, pupil = refs.get("Center mark"), refs.get("Camera pupil")
    metrics = {"eccentricity": {role: refs[role].eccentricity for role in FEATURE_NAMES[:3]},
               "manual": [role for role, edge in refs.items() if edge.provenance.startswith("manual")],
               "center_mark_present": mark is not None, "camera_pupil_present": pupil is not None}
    if pupil is not None:
        metrics["pupil_from_focuser_px"] = tuple(pupil.center[i] - focuser.center[i] for i in (0, 1))
        target = mark or primary
        metrics["pupil_from_primary_reference_px"] = tuple(pupil.center[i] - target.center[i] for i in (0, 1))
    if any((edge.edge_width or 0) >= SOFT_EDGE_WIDTH for edge in (focuser, secondary, primary)):
        return AlignmentAdvice("capture", "Measured mirror edges are soft. Improve focus and steady the camera before adjusting mirrors.", metrics)
    if any(edge.coverage is not None and edge.coverage < .85 for edge in (secondary, primary)):
        return AlignmentAdvice("capture", "A mirror edge is incomplete. Improve illumination/focus to measure its shape before adjusting mirrors.", metrics)
    if focuser.clipped:
        return AlignmentAdvice("capture", "Widen the camera view to show the full focuser rim before evaluating mirror placement.", metrics)
    # Pixel heuristics: these are not calibrated telescope tolerances.
    uncertainty = max(3, focuser.radius * .015,
                      max((edge.edge_width or 0) * .75 for edge in (focuser, secondary, primary)))
    metrics["uncertainty_px"] = uncertainty
    similar_ovals = (secondary.eccentricity > .35 and primary.eccentricity > .35
                     and abs(secondary.eccentricity - primary.eccentricity) < .1
                     and abs((secondary.angle_deg - primary.angle_deg + 90) % 180 - 90) < 20)
    if similar_ovals:
        return AlignmentAdvice("camera", "Both mirror outlines have similar oval distortion. Seat and center the camera squarely in the focuser, then reacquire before changing telescope alignment.", metrics)
    if secondary.eccentricity > .4:
        return AlignmentAdvice("secondary_shape", "The actual secondary edge looks oval. With the camera seated squarely, adjust secondary rotation in small steps to make its face rounder; watch tracking after each step.", metrics)
    delta = (secondary.center[0] - focuser.center[0], secondary.center[1] - focuser.center[1])
    metrics["secondary_from_focuser_px"] = delta
    if math.hypot(*delta) > uncertainty:
        return AlignmentAdvice("secondary_placement", f"Center the actual secondary face under the focuser: move its apparent outline {image_direction((-delta[0], -delta[1]))}. Adjust placement/rotation in small steps; do not center the dark reflected shadow.", metrics)
    target = mark or primary
    aim_uncertainty = uncertainty if mark else max(uncertainty * 2, primary.radius * .03)
    metrics["aim_reference"] = "Center mark" if mark else "Primary rim center (approximate)"
    delta = (target.center[0] - focuser.center[0], target.center[1] - focuser.center[1])
    metrics["aim_from_focuser_px"] = delta
    metrics["aim_uncertainty_px"] = aim_uncertainty
    if math.hypot(*delta) > aim_uncertainty:
        if mark:
            metrics["primary_mark_from_focuser_px"] = delta
            instruction = f"Adjust secondary tilt in small steps to bring the primary center mark {image_direction((-delta[0], -delta[1]))} onto the observed focuser center. Watch the real mark, not its forced guide circle."
        else:
            instruction = f"No center mark: roughly aim the secondary by moving the primary reflection {image_direction((-delta[0], -delta[1]))} toward the focuser center. This rim-center estimate needs optical verification."
        return AlignmentAdvice("secondary_tilt", instruction, metrics)
    metrics["pupil_from_focuser_px"] = tuple(pupil.center[i] - focuser.center[i] for i in (0, 1))
    if (pupil.edge_width or 0) >= SOFT_EDGE_WIDTH or pupil.clipped or pupil.coverage is not None and pupil.coverage < .85:
        return AlignmentAdvice("capture", "Camera pupil is soft or incomplete. Improve focus/illumination or pick its actual lens opening before primary adjustment.", metrics)
    delta = tuple(pupil.center[i] - target.center[i] for i in (0, 1))
    metrics["pupil_from_primary_reference_px"] = delta
    metrics["primary_reference"] = "Center mark" if mark else "Primary rim center (approximate)"
    if math.hypot(*delta) > aim_uncertainty:
        target_name = "center mark" if mark else "estimated primary rim center"
        prefix = "" if mark else "Unmarked primary: this is approximate. "
        instruction = prefix + f"With the camera centered and square, make small primary-tilt changes to move the reflected pupil {image_direction((-delta[0], -delta[1]))} toward the {target_name}. Verify with a star test."
        return AlignmentAdvice("primary_tilt", instruction, metrics)
    instruction = ("Pupil and mirror references are within the image estimate. Verify optically with a star test; this does not certify alignment."
                   if mark else "Unmarked primary: pupil and rim centers are within the rough image estimate. Verify with a star test before relying on alignment.")
    return AlignmentAdvice("verification", instruction, metrics)
