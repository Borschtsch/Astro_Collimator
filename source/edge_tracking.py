"""Keep manually supplied optical roles across bounded offline image analyses."""

from dataclasses import dataclass, replace
import math

from .feature_detection import concentric_guides, SOFT_EDGE_WIDTH, accepts_reference


@dataclass(frozen=True)
class TrackingUpdate:
    result: object
    selections: dict
    manual_references: dict
    held: tuple
    recovered: tuple


def merge_tracking(previous, fresh, manual_references, center_offset=(0, 0)):
    observations = list(fresh.observations or fresh.candidates)
    selections = dict(fresh.suggested)
    updated = {}
    held, recovered = [], []
    delta = (0, 0)
    if previous is not None and previous.guide_center is not None and fresh.guide_center is not None:
        delta = (fresh.guide_center[0] + center_offset[0] - previous.guide_center[0],
                 fresh.guide_center[1] + center_offset[1] - previous.guide_center[1])
    primary = next((edge for edge in observations if edge.id == selections.get("Primary reflection")), None)
    next_id = max((edge.id for edge in observations), default=0) + 1
    used = set()
    for role, old in manual_references.items():
        predicted = (old.center[0] + delta[0], old.center[1] + delta[1])
        matches = []
        for edge in observations:
            if edge.id in used or not accepts_reference(role, edge, primary):
                continue
            if (edge.fit_quality or 0) < .65 or (edge.coverage is not None and edge.coverage < .6) or (edge.edge_width or 0) >= SOFT_EDGE_WIDTH:
                continue
            ratio = edge.radius / max(old.radius, 1)
            distance = math.dist(edge.center, predicted)
            if (old.kind == "mark_point" or .8 <= ratio <= 1.2) and distance <= max(6, old.radius * .25):
                owner = next((name for name, value in selections.items() if value == edge.id), role)
                if owner != role:
                    continue
                matches.append((distance / max(old.radius, 1) + abs(math.log(ratio)), edge))
        if matches:
            edge = min(matches, key=lambda item: item[0])[1]
            recovered.append(role)
            used.add(edge.id)
        else:
            edge = replace(old, id=next_id, center=predicted, provenance="manual_hold",
                           fit_quality=None, coverage=None, residual=None, support_bins=())
            next_id += 1
            observations.append(edge)
            held.append(role)
        selections[role] = edge.id
        updated[role] = edge
    # Construct the shared guides from actual observations so automatic fits and
    # retained manual radii are not confused with last frame's forced geometry.
    merged = replace(fresh, candidates=tuple(observations), observations=tuple(observations),
                     suggested=selections, guide_center=None, guide_master_id=None)
    merged = concentric_guides(merged)
    if merged.guide_center is not None and center_offset != (0, 0):
        merged = concentric_guides(merged, (merged.guide_center[0] + center_offset[0], merged.guide_center[1] + center_offset[1]))
    return TrackingUpdate(merged, selections, updated, tuple(held), tuple(recovered))
