"""Offline geometric candidates for Newtonian focuser-view review.

Fit quality describes the visible geometry, not optical identity or collimation.
All centers stay in original image pixels. Nothing here confirms an optical role.
"""

from dataclasses import asdict, dataclass, replace
import math
from time import perf_counter

import cv2
import numpy as np


FEATURE_NAMES = ("Focuser edge", "Secondary edge", "Primary reflection", "Center mark", "Camera pupil")
FEATURE_COLORS = ((255, 170, 0), (0, 210, 255), (60, 230, 110), (235, 130, 255), (255, 90, 90))
SOFT_EDGE_WIDTH = 14


def required_features(center_mark_shape="Unknown"):
    """Unknown/absent primary marks never prevent using the other references."""
    return tuple(role for role in FEATURE_NAMES
                 if role != "Center mark" or center_mark_shape in ("Ring", "Spot", "Triangle"))


def accepts_reference(role, edge, primary=None):
    if role == "Center mark":
        return edge.kind.startswith("mark_")
    if role == "Camera pupil":
        if edge.kind.startswith("pupil_"):
            return True
        return (primary is not None and edge.kind in ("boundary", "mark_round")
                and edge.radius < primary.radius * .3
                and math.dist(edge.center, primary.center) < primary.radius * .5)
    return edge.kind == "boundary"


@dataclass(frozen=True)
class EdgeCandidate:
    id: int
    center: tuple[float, float]
    axes: tuple[float, float]  # Semiaxes, major then minor.
    angle_deg: float
    kind: str = "boundary"
    fit_quality: float | None = None
    coverage: float | None = None
    residual: float | None = None
    provenance: str = "detected"
    support_bins: tuple[int, ...] = ()  # 72 angular bins; absent portions are inferred.
    clipped: bool = False
    edge_width: float | None = None  # Transition width in analysis pixels.

    @property
    def eccentricity(self):
        return math.sqrt(max(0, 1 - (self.axes[1] / self.axes[0]) ** 2))

    @property
    def radius(self):
        return math.sqrt(self.axes[0] * self.axes[1])

    def points(self, count=72):
        theta = np.linspace(0, 2 * np.pi, count, endpoint=False)
        angle = math.radians(self.angle_deg)
        x, y = self.axes[0] * np.cos(theta), self.axes[1] * np.sin(theta)
        return np.column_stack((self.center[0] + x * math.cos(angle) - y * math.sin(angle),
                                self.center[1] + x * math.sin(angle) + y * math.cos(angle)))

    def normalized_distance(self, points):
        points = np.asarray(points, dtype=float) - self.center
        angle = math.radians(self.angle_deg)
        x = points[:, 0] * math.cos(angle) + points[:, 1] * math.sin(angle)
        y = -points[:, 0] * math.sin(angle) + points[:, 1] * math.cos(angle)
        return np.sqrt((x / self.axes[0]) ** 2 + (y / self.axes[1]) ** 2)


@dataclass(frozen=True)
class DetectionResult:
    image_size: tuple[int, int]
    candidates: tuple[EdgeCandidate, ...]
    suggested: dict[str, int]
    messages: tuple[str, ...]
    elapsed_ms: float
    observations: tuple[EdgeCandidate, ...] = ()  # Original independently fitted geometry.
    guide_center: tuple[float, float] | None = None
    guide_master_id: int | None = None

    def candidate(self, candidate_id):
        return next((item for item in self.candidates if item.id == candidate_id), None)

    def to_dict(self):
        return asdict(self)


def _fit_contour(contour, gray):
    points = contour.reshape(-1, 2).astype(float)
    if len(points) < 12:
        return None
    try:
        (cx, cy), (diameter_a, diameter_b), angle = cv2.fitEllipseAMS(contour)
    except cv2.error:
        return None
    if not all(math.isfinite(value) for value in (cx, cy, diameter_a, diameter_b, angle)):
        return None
    a, b = diameter_a / 2, diameter_b / 2
    if a < b:
        a, b, angle = b, a, angle + 90
    if b < 2 or a / b > 2.0:
        return None
    edge = EdgeCandidate(0, (cx, cy), (a, b), angle % 180)
    radial = edge.normalized_distance(points)
    residual = float(np.median(np.abs(radial - 1)))
    if residual > 0.035 or np.quantile(np.abs(radial - 1), 0.9) > 0.09:
        return None
    radians = math.radians(edge.angle_deg)
    delta = points - edge.center
    x = (delta[:, 0] * math.cos(radians) + delta[:, 1] * math.sin(radians)) / a
    y = (-delta[:, 0] * math.sin(radians) + delta[:, 1] * math.cos(radians)) / b
    bins = np.floor((np.arctan2(y, x) + np.pi) / (2 * np.pi) * 36).astype(int) % 36
    coverage = len(np.unique(bins)) / 36
    if coverage < 0.8:
        return None
    height, width = gray.shape
    samples = edge.points()
    # Complete visible rims only; partially clipped arcs need explicit manual review.
    if (samples[:, 0].min() < 2 or samples[:, 1].min() < 2 or
            samples[:, 0].max() > width - 3 or samples[:, 1].max() > height - 3):
        return None
    vectors = samples - edge.center
    vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1)
    inside = np.rint(samples - vectors * 2).astype(int)
    outside = np.rint(samples + vectors * 2).astype(int)
    inside[:, 0] = np.clip(inside[:, 0], 0, width - 1)
    inside[:, 1] = np.clip(inside[:, 1], 0, height - 1)
    outside[:, 0] = np.clip(outside[:, 0], 0, width - 1)
    outside[:, 1] = np.clip(outside[:, 1], 0, height - 1)
    contrast = np.mean(np.abs(gray[inside[:, 1], inside[:, 0]].astype(float) -
                              gray[outside[:, 1], outside[:, 0]].astype(float)))
    quality = 0.45 * coverage + 0.4 * max(0, 1 - residual / 0.08) + 0.15 * min(1, contrast / 80)
    return replace(edge, fit_quality=float(quality), coverage=coverage, residual=residual)


def _merge_duplicates(candidates):
    unique = []
    for edge in sorted(candidates, key=lambda item: item.fit_quality or 0, reverse=True):
        duplicate = False
        for previous in unique:
            tolerance = max(3, min(edge.radius, previous.radius) * 0.025,
                            min(edge.edge_width or 0, previous.edge_width or 0) * 0.5)
            if (np.linalg.norm(np.subtract(edge.center, previous.center)) < tolerance and
                    max(abs(a - b) for a, b in zip(edge.axes, previous.axes)) < tolerance):
                duplicate = True
                break
        if not duplicate:
            unique.append(edge)
    return unique


def _ellipse_from_points(points):
    if len(points) < 12:
        return None
    try:
        (cx, cy), (da, db), angle = cv2.fitEllipseAMS(np.asarray(points, np.float32).reshape(-1, 1, 2))
    except cv2.error:
        return None
    if not all(math.isfinite(v) for v in (cx, cy, da, db, angle)) or min(da, db) < 8:
        return None
    if da < db:
        da, db, angle = db, da, angle + 90
    if da / db > 2.0:
        return None
    return EdgeCandidate(0, (cx, cy), (da / 2, db / 2), angle % 180)


def _circle_fit(points):
    points = np.asarray(points, dtype=float)
    if len(points) < 3 or not np.isfinite(points).all():
        return None
    origin = points.mean(axis=0)
    local = points - origin
    matrix = np.column_stack((2 * local, np.ones(len(points))))
    solution, _, rank, _ = np.linalg.lstsq(matrix, np.sum(local ** 2, axis=1), rcond=None)
    squared_radius = solution[2] + np.sum(solution[:2] ** 2)
    if rank < 3 or squared_radius < 4:
        return None
    radius = float(math.sqrt(squared_radius))
    return EdgeCandidate(0, tuple(float(v) for v in origin + solution[:2]), (radius, radius), 0)


def as_focuser_circle(edge, image_size):
    """Circular constraint from supported geometry; no new photographic evidence."""
    if abs(edge.axes[0] - edge.axes[1]) < 1e-6:
        return edge
    points = edge.points(288)
    if edge.support_bins:
        points = points[np.isin(np.arange(len(points)) // 4, edge.support_bins)]
    fitted = _circle_fit(points)
    if fitted is None:
        raise ValueError("This edge does not constrain a focuser circle. Pick three rim points instead.")
    support = ()
    if edge.support_bins:
        delta = points - fitted.center
        bins = np.floor((np.arctan2(delta[:, 1], delta[:, 0]) % (2 * np.pi)) * 72 / (2 * np.pi)).astype(int)
        support = tuple(int(v) for v in np.unique(bins))
    width, height = image_size
    samples = fitted.points()
    clipped = bool((samples[:, 0] < 2).any() or (samples[:, 0] > width - 3).any() or
                   (samples[:, 1] < 2).any() or (samples[:, 1] > height - 3).any())
    return replace(fitted, id=edge.id, kind="boundary", provenance="focuser_circle_estimate",
                   support_bins=support, clipped=clipped,
                   coverage=len(support) / 72 if support else None)


def _rim_evidence(edge, gray, refine=True, gradient_field=None, max_eccentricity=0.55, circular=False, minimum_support=None, polarity=None):
    """Validate an ellipse against independent, distributed intensity transitions."""
    # Allow one analysis pixel of axis mismatch for rasterized circles.
    if edge.eccentricity > max_eccentricity and edge.axes[0] - edge.axes[1] > 1:
        return None
    height, width = gray.shape
    points = edge.points(180)
    clipped = (points[:, 0].min() < 2 or points[:, 1].min() < 2 or
               points[:, 0].max() > width - 3 or points[:, 1].max() > height - 3)
    minimum_support = minimum_support if minimum_support is not None else (0.48 if clipped else 0.65)
    angle = math.radians(edge.angle_deg)
    theta = np.linspace(0, 2 * np.pi, len(points), endpoint=False)
    normals = np.column_stack((np.cos(theta) / edge.axes[0], np.sin(theta) / edge.axes[1]))
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    normals = normals @ rotation.T
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    offsets = np.arange(-16, 17, dtype=np.float32)
    samples = points[:, None, :] + normals[:, None, :] * offsets[None, :, None]
    valid = ((samples[:, :, 0] >= 1) & (samples[:, :, 0] < width - 2) &
             (samples[:, :, 1] >= 1) & (samples[:, :, 1] < height - 2))
    values = cv2.remap(gray, samples[:, :, 0].astype(np.float32), samples[:, :, 1].astype(np.float32),
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    derivative = np.diff(values, axis=1)
    distance = max(6, edge.radius * .035) if polarity is not None else max(3, edge.radius * .015)
    in_band = np.abs(offsets[:-1] + 0.5) <= distance
    gradients = np.abs(derivative)
    if polarity is not None:
        gradients[derivative * polarity <= 0] = 0
    gradients[:, ~in_band] = 0
    gradients[~(valid[:, :-1] & valid[:, 1:])] = 0
    peak_index = np.argmax(gradients, axis=1)
    peak = gradients[np.arange(len(points)), peak_index]
    if gradient_field is None:
        gradient_field = (cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1))
    locations = points + normals * (offsets[peak_index] + 0.5)[:, None]
    gx, gy = (cv2.remap(component, locations[:, 0].astype(np.float32)[:, None],
                       locations[:, 1].astype(np.float32)[:, None], cv2.INTER_LINEAR).ravel()
              for component in gradient_field)
    alignment = np.abs(gx * normals[:, 0] + gy * normals[:, 1]) / np.maximum(np.hypot(gx, gy), 1e-5)
    background = np.median(np.abs(derivative[:, [0, 1, 2, 29, 30, 31]]), axis=1)
    contrast = values[:, 25] - values[:, 7]
    visible = valid[:, 7] & valid[:, 25]
    supported = visible & (peak >= np.maximum(0.85, background * 1.5)) & (np.abs(contrast) >= 9) & (alignment >= 0.88)
    if np.count_nonzero(supported) < len(points) * minimum_support:
        return None
    # Illumination/reflections can reverse contrast around a real rim. Its sign
    # should nevertheless vary smoothly along arcs, unlike unrelated texture.
    pairs = supported & np.roll(supported, 1)
    coherence = float(np.mean((contrast > 0)[pairs] == np.roll(contrast > 0, 1)[pairs])) if pairs.any() else 0
    if coherence < 0.85:
        return None
    bins = np.unique(np.floor(np.flatnonzero(supported) * 72 / len(points)).astype(int))
    coverage = len(bins) / 72
    if coverage < 0.7:
        # A short arc constrains a fit less than a complete rim. Demand closer
        # agreement between the measured gradient and its fitted normal.
        supported &= alignment >= 0.95
        bins = np.unique(np.floor(np.flatnonzero(supported) * 72 / len(points)).astype(int))
        coverage = len(bins) / 72
    if coverage < minimum_support or len(set((bins // 18).tolist())) < 3:
        return None
    if refine:
        offsets_found = offsets[peak_index] + 0.5
        measured = points[supported] + normals[supported] * offsets_found[supported, None]
        fitted = _circle_fit(measured) if circular else _ellipse_from_points(measured)
        if (fitted is not None and np.linalg.norm(np.subtract(fitted.center, edge.center)) <= max(6, edge.radius * (.05 if polarity is not None else .03))
                and max(abs(a - b) for a, b in zip(fitted.axes, edge.axes)) <= max(6, edge.radius * 0.05)):
            return _rim_evidence(fitted, gray, False, gradient_field, max_eccentricity, circular, minimum_support, polarity)
    widths = []
    for index in np.flatnonzero(supported):
        position = peak_index[index]
        line = np.abs(derivative[index])
        left = right = position
        while left > 0 and line[left - 1] >= peak[index] * 0.5:
            left -= 1
        while right < len(line) - 1 and line[right + 1] >= peak[index] * 0.5:
            right += 1
        widths.append(right - left + 1)
    samples = edge.points()
    clipped = (samples[:, 0].min() < 2 or samples[:, 1].min() < 2 or
               samples[:, 0].max() > width - 3 or samples[:, 1].max() > height - 3)
    quality = 0.55 * coverage + 0.25 * coherence + 0.2 * min(1, np.median(np.abs(contrast[supported])) / 50)
    return replace(edge, coverage=coverage, fit_quality=float(quality),
                   residual=float(np.median(np.abs(offsets[peak_index[supported]] + 0.5)) / edge.radius),
                   support_bins=tuple(int(v) for v in bins), clipped=bool(clipped),
                   edge_width=float(np.median(widths)), provenance="detected_arcs")


def _find_separated_rims(gray, seeds, boundary_min, max_eccentricity, minimum_support=None, circular=False):
    """Search radial transitions, then fit ellipses; no Hough/ML/network model."""
    height, width = gray.shape
    smooth = cv2.GaussianBlur(gray, (0, 0), 1.8).astype(np.float32)
    gradient_field = (cv2.Sobel(smooth, cv2.CV_32F, 1, 0), cv2.Sobel(smooth, cv2.CV_32F, 0, 1))
    max_radius = min(math.ceil(min(height, width) * 1.05), math.ceil(max(height, width) * 0.8))
    radii = np.arange(2, max_radius, dtype=np.float32)
    theta = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    unit = np.column_stack((np.cos(theta), np.sin(theta)))
    results = []
    for center in seeds:
        coordinates = np.asarray(center) + unit[:, None, :] * radii[None, :, None]
        valid = ((coordinates[:, :, 0] >= 2) & (coordinates[:, :, 0] < width - 3) &
                 (coordinates[:, :, 1] >= 2) & (coordinates[:, :, 1] < height - 3))
        values = cv2.remap(smooth, coordinates[:, :, 0].astype(np.float32),
                           coordinates[:, :, 1].astype(np.float32), cv2.INTER_LINEAR)
        gradient = np.abs(np.diff(values, axis=1))
        gradient[~(valid[:, :-1] & valid[:, 1:])] = 0
        profile = cv2.GaussianBlur(np.mean(np.minimum(gradient, 20), axis=0)[None, :],
                                   (0, 0), 2)[0]
        maxima = np.flatnonzero((profile[1:-1] > profile[:-2]) & (profile[1:-1] >= profile[2:])) + 1
        maxima = [i for i in maxima if radii[i] >= boundary_min and profile[i] > 0.45]
        peaks = []
        for index in sorted(maxima, key=lambda i: profile[i], reverse=True):
            if all(abs(radii[index] - radii[previous]) > max(6, radii[index] * 0.055) for previous in peaks):
                peaks.append(index)
            if len(peaks) >= 14:
                break
        for index in peaks:
            radius = radii[index]
            band = max(8, radius * 0.20)
            columns = np.flatnonzero(np.abs(radii[:-1] - radius) <= band)
            # Avoid letting the much brighter primary rim steal samples from a
            # nearby faint secondary edge. Prefer a local transition near this
            # radius rather than the strongest transition anywhere in the band.
            weights = np.exp(-0.5 * ((radii[columns] - radius) / max(5, radius * 0.075)) ** 2)
            scores = np.minimum(gradient[:, columns], 3) * weights
            choices = columns[np.argmax(scores, axis=1)]
            strong = gradient[np.arange(len(theta)), choices] > 0.85
            points = coordinates[np.arange(len(theta)), choices + 1][strong]
            if len(points) < 80:
                continue
            edge = None
            for _ in range(3):
                edge = _circle_fit(points) if circular else _ellipse_from_points(points)
                if edge is None:
                    break
                residual = np.abs(edge.normalized_distance(points) - 1)
                points = points[residual <= max(0.025, float(np.quantile(residual, 0.8)))]
            if edge is None or edge.axes[1] < boundary_min:
                continue
            if (np.linalg.norm(np.subtract(edge.center, center)) > radius * 0.3 or
                    edge.axes[0] > radius * 1.4 or edge.axes[1] < radius * 0.6):
                continue
            evidence = _rim_evidence(edge, smooth, gradient_field=gradient_field, max_eccentricity=max_eccentricity,
                                     minimum_support=minimum_support, circular=circular)
            if evidence is not None:
                results.append(evidence)
    return results


def _search_seeds(candidates, gray, boundary_min):
    seeds = []
    for edge in sorted(candidates, key=lambda item: item.radius, reverse=True):
        if edge.kind == "boundary" and edge.radius >= boundary_min:
            if all(np.linalg.norm(np.subtract(edge.center, point)) > boundary_min * 0.5 for point in seeds):
                seeds.append(edge.center)
        if len(seeds) == 3:
            break
    # A bright mirror face provides a useful anchor even if its contour contains
    # spider lines, clips, or a central obstruction. This is a geometric seed only.
    _, binary = cv2.threshold(cv2.GaussianBlur(gray, (0, 0), 3), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    gap = max(3, round(min(gray.shape) * 0.04) | 1)
    joined = cv2.morphologyEx(binary, cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (gap, gap)))
    joined_contours, _ = cv2.findContours(joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if joined_contours:
        largest = max(joined_contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)
        if cv2.contourArea(largest) >= gray.size * 0.04 and min(w, h) > boundary_min * 2:
            point = (x + w / 2, y + h / 2)
            if all(np.linalg.norm(np.subtract(point, previous)) > boundary_min * 0.5 for previous in seeds):
                seeds.insert(0, point)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:3]:
        x, y, w, h = cv2.boundingRect(contour)
        if cv2.contourArea(contour) >= gray.size * 0.015 and min(w, h) > boundary_min * 2:
            moments = cv2.moments(contour)
            if moments["m00"]:
                point = (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])
                if all(np.linalg.norm(np.subtract(point, previous)) > boundary_min * 0.5 for previous in seeds):
                    seeds.append(point)
    if not seeds:
        seeds.append((gray.shape[1] / 2, gray.shape[0] / 2))
    return seeds[:3]


def _fit_contour_arcs(contours, gray, boundary_min, max_eccentricity):
    """A joined contour can contain good rim arcs plus clips/spider lines."""
    results = []
    gradient_field = (cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1))
    for contour in sorted(contours, key=len, reverse=True)[:24]:
        points = contour.reshape(-1, 2)
        if len(points) < max(60, boundary_min * 4):
            continue
        doubled = np.concatenate((points, points))
        for fraction in (0.25, 0.4):
            length = int(len(points) * fraction)
            for start in np.linspace(0, len(points) - 1, 8, dtype=int):
                edge = _ellipse_from_points(doubled[start:start + length:2])
                if edge is None or edge.axes[1] < boundary_min or edge.axes[0] > min(gray.shape) * 1.1:
                    continue
                if not (0 <= edge.center[0] < gray.shape[1] and 0 <= edge.center[1] < gray.shape[0]):
                    continue
                evidence = _rim_evidence(edge, gray, gradient_field=gradient_field, max_eccentricity=max_eccentricity)
                if evidence is not None:
                    results.append(evidence)
    return results


def _suppress_mixed_rims(candidates):
    """Drop weaker fits that reuse arcs from better fits instead of finding a rim."""
    accepted = []
    main = max((edge for edge in candidates if (edge.coverage or 0) >= 0.7),
               key=lambda item: item.radius, default=None)
    for edge in sorted(candidates, key=lambda item: (item.coverage or 0, item.fit_quality or 0), reverse=True):
        if main and np.linalg.norm(np.subtract(edge.center, main.center)) > main.radius * 0.45:
            continue
        points = edge.points(180)
        observed = np.ones(len(points), bool)
        if edge.support_bins:
            observed = np.isin(np.floor(np.arange(len(points)) * 72 / len(points)).astype(int), edge.support_bins)
        overlapping = np.zeros(len(points), bool)
        for previous in accepted:
            if previous.radius < edge.radius * 0.5 or previous.radius > edge.radius * 1.8:
                continue
            distance = np.abs(previous.normalized_distance(points) - 1) * previous.radius
            overlapping |= distance < max(3, previous.radius * 0.035, (previous.edge_width or 0) * 0.5)
        if np.mean(overlapping[observed]) < 0.55:
            accepted.append(edge)
    return accepted


def _contained(outer, inner):
    return (inner.radius < outer.radius * 0.94 and
            np.max(outer.normalized_distance(inner.points(48))) <= 1.03)


def _face_measurements(edge, gray):
    """Appearance evidence in the original luminance, never enhanced brightness."""
    vectors = edge.points(180) - edge.center
    samples = np.concatenate([edge.center + vectors * factor for factor in (.4, .6, .8, .96, 1.04)])
    values = cv2.remap(gray.astype(np.float32), samples[:, 0].astype(np.float32)[:, None],
                       samples[:, 1].astype(np.float32)[:, None], cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REPLICATE).reshape(5, 180)
    face = float(np.mean(np.median(values[:3], axis=0)))
    positive = float(np.mean(values[3] - values[4] > 9))
    spread = float(np.median(np.ptp(values[:3], axis=0)))
    center_samples = np.concatenate([edge.center + vectors * factor for factor in (.1, .2)])
    center_values = cv2.remap(gray.astype(np.float32), center_samples[:, 0].astype(np.float32)[:, None],
                              center_samples[:, 1].astype(np.float32)[:, None], cv2.INTER_LINEAR).reshape(2, 180)
    dark_center = float(np.median(center_values)) < face * .75
    return face, positive, spread, dark_center


def _suggest_roles(boundaries, marks, gray):
    """Suggest independently observable roles; no complete-triple prerequisite.

    A bright mirror face with a smaller central obstruction anchors the primary.
    A three-layer view is a fallback when that obstruction is unresolved. Close
    sides of the same rim cannot be used to manufacture a separate optical layer.
    """
    if not boundaries:
        return {}, ("No optical references identified.",)
    outer = max(boundaries, key=lambda edge: edge.radius)
    usable = [edge for edge in boundaries if (edge.edge_width or 0) < SOFT_EDGE_WIDTH]
    faces = {edge.id: _face_measurements(edge, gray) for edge in boundaries}
    face_floor = max(20, float(np.percentile(gray, 90)) * .35)
    primary_options = []
    for edge in usable:
        if edge.radius < outer.radius * .25:
            continue
        face, positive, spread, dark_center = faces[edge.id]
        pupils = [pupil for pupil in boundaries + marks
                  if .035 * edge.radius < pupil.radius < .42 * edge.radius
                  and np.linalg.norm(np.subtract(pupil.center, edge.center)) < .3 * edge.radius
                  and (faces[pupil.id] if pupil.id in faces else _face_measurements(pupil, gray))[0] < face * .75]
        if ((not pupils and not dark_center) or face < face_floor
                or spread > face * .3):
            continue
        # The outer illuminated focuser annulus may also surround the pupil.
        # Its interior contains the darker layers; prefer the bright mirror face.
        score = ((face - spread) / 255 + positive * .25 + (edge.fit_quality or 0) * .1
                 - .15 * edge.radius / outer.radius)
        primary_options.append((score, edge))
    primary = max(primary_options, key=lambda item: item[0])[1] if primary_options else None
    if primary is None:
        chains = []
        for middle in usable:
            if not _contained(outer, middle) or middle.radius < .3 * outer.radius:
                continue
            for inner in usable:
                if not _contained(middle, inner) or inner.radius < .5 * middle.radius:
                    continue
                face, positive, _, _ = faces[inner.id]
                if face <= faces[middle.id][0] - 15 or positive < .45:
                    continue
                chains.append((face + 20 * positive + math.log1p(inner.radius), inner))
        if chains:
            primary = max(chains, key=lambda item: item[0])[1]
    if primary is None:
        return {}, ("Visible rims do not yet distinguish the optical elements. Pick an actual edge or improve the view.",)
    suggested = {"Primary reflection": primary.id}
    # A close but clean circular outer rim is still a useful focuser guess.
    # The former 1.3 size gate discarded high-quality tightly framed views.
    tight_outer = (outer.eccentricity <= .2 and (outer.fit_quality or 0) >= .85
                   and (outer.coverage or 0) >= .8 and (outer.edge_width or 0) < SOFT_EDGE_WIDTH
                   and outer.radius - primary.radius >= 4)
    if (outer.id != primary.id and outer.radius > primary.radius * 1.08
            and (outer.radius > primary.radius * 1.3 or tight_outer) and _contained(outer, primary)):
        suggested["Focuser edge"] = outer.id
        secondary_options = [edge for edge in usable
                             if edge.id != outer.id and _contained(outer, edge)
                             and _contained(edge, primary) and edge.radius > primary.radius * 1.08]
        if secondary_options:
            # Prefer the outside of the actual secondary, not a nested rim side.
            secondary = max(secondary_options, key=lambda edge: edge.radius)
            suggested["Secondary edge"] = secondary.id
    plausible_marks = [edge for edge in marks if edge.radius < primary.radius * .15
                       and np.linalg.norm(np.subtract(edge.center, primary.center)) < primary.radius * .4
                       and np.max(primary.normalized_distance(edge.points(12))) < 1]
    if plausible_marks:
        suggested["Center mark"] = min(plausible_marks,
                                       key=lambda edge: np.linalg.norm(np.subtract(edge.center, primary.center))).id
    return suggested, ("Named outlines are automatic best guesses. Blink-check them; replace an incorrect outline or add a missing edge.",)


def _suggest_camera_pupil(boundaries, details, gray, suggested):
    """Find a supported small opening inside a larger dark central reflection.

    The whole reflected secondary shadow is never used as the lens opening.
    A lone center dot cannot distinguish a pupil from a mirror mark.
    """
    primary = next((edge for edge in boundaries if edge.id == suggested.get("Primary reflection")), None)
    if primary is None:
        return None
    primary_face = _face_measurements(primary, gray)[0]
    protected = {value for role, value in suggested.items() if role != "Center mark"}
    all_edges = boundaries + details
    shells = [edge for edge in all_edges if edge.id not in protected
              and edge.kind in ("boundary", "mark_round")
              and primary.radius * .06 < edge.radius < primary.radius * .4
              and math.dist(edge.center, primary.center) < primary.radius * .45
              and _face_measurements(edge, gray)[0] < primary_face * .7]
    options = []
    for shell in shells:
        shell_face = _face_measurements(shell, gray)[0]
        for edge in all_edges:
            if (edge.id in protected or edge.id == shell.id or edge.kind not in ("boundary", "mark_round")
                    or not max(2, primary.radius * .01) <= edge.radius < min(primary.radius * .2, shell.radius / 1.45)
                    or edge.eccentricity > .35 or (edge.fit_quality or 0) < .7
                    or math.dist(edge.center, shell.center) > shell.radius * .35
                    or np.max(shell.normalized_distance(edge.points(36))) >= .95):
                continue
            contrast = abs(_face_measurements(edge, gray)[0] - shell_face)
            if contrast < max(12, primary_face * .08):
                continue
            score = contrast / 255 + (edge.fit_quality or 0) * .3 - math.dist(edge.center, shell.center) / shell.radius
            options.append((score, edge))
    return replace(max(options, key=lambda item: item[0])[1], kind="pupil_round") if options else None


def _recover_secondary(contours, smooth, primary, focuser, max_eccentricity):
    """An occluded secondary must have substantial evidence away from both rims.

    Only search after identifying the primary and outer view. This lower support
    threshold never admits standalone short arcs or freely placed ghost ellipses.
    """
    proposals = []
    for contour in sorted(contours, key=len, reverse=True)[:24]:
        points = contour.reshape(-1, 2)
        if len(points) < 60:
            continue
        doubled = np.concatenate((points, points))
        for fraction in (.15, .25, .4, .6):
            length = int(len(points) * fraction)
            for start in np.linspace(0, len(points) - 1, 16, dtype=int):
                edge = _ellipse_from_points(doubled[start:start + length:2])
                if (edge is None or not primary.radius * 1.05 < edge.radius < focuser.radius * .94
                        or np.max(edge.normalized_distance(primary.points())) > 1.12
                        or np.max(focuser.normalized_distance(edge.points())) > 1.05):
                    continue
                evidence = _rim_evidence(edge, smooth, max_eccentricity=max_eccentricity, minimum_support=.42)
                if (evidence is None or (evidence.coverage or 0) < .68 or not primary.radius * 1.1 < evidence.radius < focuser.radius * .94
                        or np.max(evidence.normalized_distance(primary.points())) > 1.05
                        or np.max(focuser.normalized_distance(evidence.points())) > 1.05):
                    continue
                points_on_rim = evidence.points()
                supported = np.isin(np.arange(72), evidence.support_bins)
                distinct = supported.copy()
                for reference in (primary, focuser):
                    distance = np.abs(reference.normalized_distance(points_on_rim) - 1) * reference.radius
                    distinct &= distance > max(4, reference.radius * .035, (reference.edge_width or 0) * .5)
                if distinct.mean() < .28 or distinct.sum() < supported.sum() * .5:
                    continue
                proposals.append((distinct.mean() + (evidence.fit_quality or 0) * .25, evidence))
    return max(proposals, key=lambda item: item[0])[1] if proposals else None


def _analyze_observations(frame, center_mark_shape="Unknown", max_dimension=960, max_eccentricity=0.55):
    start = perf_counter()
    if (isinstance(max_eccentricity, bool) or not isinstance(max_eccentricity, (int, float)) or
            not math.isfinite(max_eccentricity) or not 0 <= max_eccentricity <= 0.85):
        raise ValueError("Maximum eccentricity must be between 0 and 0.85.")
    if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
        raise ValueError("Analysis needs an 8-bit BGR image with three channels.")
    height, width = frame.shape[:2]
    if min(height, width) < 32:
        raise ValueError("Image is too small to inspect optical edges.")
    scale = min(1.0, max_dimension / max(height, width))
    small = cv2.resize(frame, (max(1, round(width * scale)), max(1, round(height * scale)))) if scale < 1 else frame
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    if float(np.percentile(gray, 99) - np.percentile(gray, 1)) < 15:
        return DetectionResult((width, height), (), {},
                               ("Low contrast: improve illumination or exposure, then detect again.",),
                               (perf_counter() - start) * 1000)
    normalized = cv2.createCLAHE(clipLimit=2, tileGridSize=(8, 8)).apply(gray)
    edges = cv2.Canny(cv2.GaussianBlur(normalized, (5, 5), 0), 20, 60)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    candidates, triangles = [], []
    mark_limit = min(gray.shape) * 0.055
    boundary_min = min(gray.shape) * 0.06
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if min(w, h) < 4:
            continue
        if center_mark_shape in ("Unknown", "Triangle") and max(w, h) <= mark_limit * 2:
            perimeter = cv2.arcLength(contour, True)
            polygon = cv2.approxPolyDP(contour, 0.045 * perimeter, True)
            if len(polygon) == 3 and cv2.isContourConvex(polygon) and abs(cv2.contourArea(polygon)) >= 8:
                moments = cv2.moments(polygon)
                if moments["m00"]:
                    radius = math.sqrt(abs(moments["m00"]) / math.pi)
                    triangles.append(EdgeCandidate(0, (moments["m10"] / moments["m00"],
                                                         moments["m01"] / moments["m00"]),
                                                       (radius, radius), 0, "mark_triangle", 0.8))
        edge = _fit_contour(contour, gray)
        if edge is not None:
            if edge.axes[1] >= boundary_min:
                candidates.append(edge)
            elif edge.radius <= mark_limit:
                candidates.append(replace(edge, kind="mark_round"))
    smooth = cv2.GaussianBlur(normalized, (0, 0), 1.8).astype(np.float32)
    boundaries = []
    for edge in candidates:
        if edge.kind == "boundary":
            evidence = _rim_evidence(edge, smooth, max_eccentricity=max_eccentricity)
            if evidence is not None:
                boundaries.append(evidence)
    boundaries += _find_separated_rims(normalized, _search_seeds(candidates, gray, boundary_min), boundary_min, max_eccentricity)
    boundaries += _fit_contour_arcs(contours, smooth, boundary_min, max_eccentricity)
    boundaries = sorted(_suppress_mixed_rims(_merge_duplicates(boundaries)),
                        key=lambda edge: edge.radius, reverse=True)[:24]
    marks = sorted(_merge_duplicates([edge for edge in candidates if edge.kind != "boundary"] + triangles),
                   key=lambda edge: edge.fit_quality or 0, reverse=True)[:16]
    round_details = [edge for edge in marks if edge.kind == "mark_round"]
    anchors = [edge for edge in boundaries if edge.radius >= min(gray.shape) * 0.12]
    if anchors:
        anchor = min(anchors, key=lambda edge: edge.radius)
        marks = [edge for edge in marks if edge.radius < anchor.radius * 0.15 and
                 np.linalg.norm(np.subtract(edge.center, anchor.center)) < anchor.radius * 0.4]
    else:
        marks = []
    boundaries = [replace(edge, id=index + 1) for index, edge in enumerate(boundaries)]
    marks = [replace(edge, id=len(boundaries) + index + 1) for index, edge in enumerate(marks)]
    optical_marks = ([] if center_mark_shape == "None" else
                     [edge for edge in marks if edge.kind == "mark_triangle"] if center_mark_shape == "Triangle" else marks)
    suggested, messages = _suggest_roles(boundaries, optical_marks, gray)
    messages = list(messages)
    primary_id = suggested.get("Primary reflection")
    if primary_id is not None:
        primary = next(edge for edge in boundaries if edge.id == primary_id)
        bright_face = _rim_evidence(primary, smooth, max_eccentricity=max_eccentricity, polarity=-1)
        if bright_face is not None:
            bright_face = replace(bright_face, id=primary_id)
            boundaries = [bright_face if edge.id == primary_id else edge for edge in boundaries]
    if "Primary reflection" in suggested and "Focuser edge" not in suggested:
        primary = next(edge for edge in boundaries if edge.id == suggested["Primary reflection"])
        wider = _find_separated_rims(normalized, [primary.center], boundary_min, 0,
                                     minimum_support=.48, circular=True)
        wider = [edge for edge in wider if edge.radius > primary.radius * 1.3
                 and edge.radius > max((item.radius for item in boundaries), default=0) * .98
                 and np.max(edge.normalized_distance(primary.points())) <= 1.03]
        if wider:
            focuser = replace(max(wider, key=lambda edge: edge.radius),
                              id=max((edge.id for edge in boundaries + marks), default=0) + 1)
            boundaries.append(focuser)
            suggested["Focuser edge"] = focuser.id
    focuser_id = suggested.get("Focuser edge")
    if focuser_id is not None:
        original = next(edge for edge in boundaries if edge.id == focuser_id)
        constrained = as_focuser_circle(original, (small.shape[1], small.shape[0]))
        circular = _rim_evidence(constrained, smooth, circular=True, minimum_support=.48)
        if circular is None:
            suggested.pop("Focuser edge")
            messages.append("Focuser circle could not be verified. Pick three visible rim points.")
        else:
            circular = replace(circular, id=focuser_id)
            boundaries = [circular if edge.id == focuser_id else edge for edge in boundaries]
            if "Secondary edge" not in suggested:
                primary = next(edge for edge in boundaries if edge.id == suggested["Primary reflection"])
                secondary = _recover_secondary(contours, smooth, primary, circular, max_eccentricity)
                if secondary is not None:
                    secondary = replace(secondary, id=max((edge.id for edge in boundaries + marks), default=0) + 1)
                    boundaries.append(secondary)
                    suggested["Secondary edge"] = secondary.id
    # Keep lens-sized detail that is too large for the center-mark heuristic.
    pupil_details = list(marks)
    next_id = max((edge.id for edge in boundaries + marks), default=0) + 1
    for detail in round_details:
        if not any(math.dist(detail.center, edge.center) < 2 and abs(detail.radius - edge.radius) < 2
                   for edge in pupil_details + boundaries):
            pupil_details.append(replace(detail, id=next_id))
            next_id += 1
    pupil = _suggest_camera_pupil(boundaries, pupil_details, gray, suggested)
    if pupil is not None:
        if suggested.get("Center mark") == pupil.id:
            suggested.pop("Center mark")
            primary = next(edge for edge in boundaries if edge.id == suggested["Primary reflection"])
            other_marks = [edge for edge in optical_marks if edge.id != pupil.id
                           and edge.radius < primary.radius * .15
                           and math.dist(edge.center, primary.center) < primary.radius * .4
                           and math.dist(edge.center, pupil.center) > pupil.radius + edge.radius
                           and np.max(primary.normalized_distance(edge.points(12))) < 1]
            if other_marks:
                suggested["Center mark"] = min(other_marks, key=lambda edge: math.dist(edge.center, primary.center)).id
        suggested["Camera pupil"] = pupil.id
        if any(edge.id == pupil.id for edge in boundaries):
            boundaries = [pupil if edge.id == pupil.id else edge for edge in boundaries]
        elif any(edge.id == pupil.id for edge in marks):
            marks = [pupil if edge.id == pupil.id else edge for edge in marks]
        else:
            marks.append(pupil)
    all_edges = [replace(edge, center=tuple(float(v / scale) for v in edge.center),
                         axes=tuple(float(v / scale) for v in edge.axes)) for edge in boundaries + marks]
    boundaries = all_edges[:len(boundaries)]
    if not all_edges:
        messages = ["No stable rims found. Check focus, steady the camera, and use even illumination; then detect again."]
    if any((edge.edge_width or 0) >= SOFT_EDGE_WIDTH for edge in boundaries):
        messages.insert(0, "Some rims are too blurry for a confident fit. Improve camera focus and steady the camera, then detect again.")
    focuser = next((edge for edge in boundaries if edge.id == suggested.get("Focuser edge")), None)
    if focuser is None or focuser.clipped:
        messages.append("Focuser rim is not identified in full. If it is outside the view, zoom out/reduce camera zoom, reposition, or use a wider-view camera.")
    if any(edge.coverage is not None and edge.coverage < 0.85 or edge.clipped for edge in boundaries):
        messages.append("Partial rims have limited observed support; circular guides extrapolate the missing edge.")
    return DetectionResult((width, height), tuple(all_edges), suggested, tuple(messages),
                           (perf_counter() - start) * 1000)


def concentric_guides(result, center=None):
    """Project observations into circular visual guides; retain observations separately."""
    if not result.candidates:
        return replace(result, guide_center=None, guide_master_id=None)
    if center is None:
        center = result.guide_center
    if center is None:
        anchor = result.candidate(result.suggested.get("Focuser edge"))
        anchor = anchor or max((edge for edge in result.candidates if edge.kind == "boundary"),
                               key=lambda edge: edge.radius, default=max(result.candidates, key=lambda edge: edge.radius))
        result = replace(result, guide_master_id=anchor.id)
        center = anchor.center
    if len(center) != 2 or not all(math.isfinite(value) for value in center):
        raise ValueError("Guide center must contain two finite coordinates.")
    width, height = result.image_size
    center = (float(max(0, min(width - 1, center[0]))), float(max(0, min(height - 1, center[1]))))
    guides = []
    for edge in result.candidates:
        radius = edge.radius
        clipped = center[0] - radius < 0 or center[1] - radius < 0 or center[0] + radius >= width or center[1] + radius >= height
        guides.append(replace(edge, center=center, axes=(radius, radius), angle_deg=0,
                              provenance="manual_drag" if edge.provenance == "manual_drag" else "concentric_guess",
                              fit_quality=None, residual=None, coverage=None, support_bins=(), clipped=clipped))
    return replace(result, candidates=tuple(guides), guide_center=center,
                   observations=result.observations or result.candidates)


def analyze_frame(frame, center_mark_shape="Unknown", max_dimension=960):
    """Best-guess circular radii around one shared center for the collimation overlay."""
    return concentric_guides(_analyze_observations(frame, center_mark_shape, max_dimension))


def circle_from_points(points, candidate_id, image_size):
    points = np.asarray(points, dtype=float)
    if points.shape != (3, 2) or not np.isfinite(points).all():
        raise ValueError("Pick three finite edge points.")
    width, height = image_size
    if np.any(points < 0) or np.any(points[:, 0] >= width) or np.any(points[:, 1] >= height):
        raise ValueError("Pick points inside the image.")
    a = 2 * (points[1:] - points[0])
    span = np.max(np.linalg.norm(points - points[0], axis=1))
    if span < 5 or abs(np.linalg.det(a)) < span * span * 0.01:
        raise ValueError("Spread the three points around the edge, not along a straight line.")
    b = np.sum(points[1:] ** 2, axis=1) - np.sum(points[0] ** 2)
    center = np.linalg.solve(a, b)
    radius = float(np.linalg.norm(center - points[0]))
    if radius < 2 or radius > max(width, height) * 2:
        raise ValueError("These points do not define a usable circle.")
    return EdgeCandidate(candidate_id, tuple(float(value) for value in center),
                         (radius, radius), 0, provenance="manual_circle")


@dataclass(frozen=True)
class DisplayTransform:
    """The exact integer crop/resize mapping shared by drawing and clicking."""
    crop_x: int
    crop_y: int
    crop_width: int
    crop_height: int
    width: int
    height: int

    @classmethod
    def for_image(cls, image_size, zoom, max_width=960, max_height=720, center=None):
        width, height = image_size
        crop_width, crop_height = max(1, int(width / zoom)), max(1, int(height / zoom))
        scale = min(max_width / crop_width, max_height / crop_height)
        crop_x, crop_y = (width - crop_width) // 2, (height - crop_height) // 2
        if center is not None:
            crop_x = max(0, min(width - crop_width, round(center[0] - crop_width / 2)))
            crop_y = max(0, min(height - crop_height, round(center[1] - crop_height / 2)))
        return cls(crop_x, crop_y,
                   crop_width, crop_height, max(1, round(crop_width * scale)),
                   max(1, round(crop_height * scale)))

    def to_display(self, point):
        return ((point[0] - self.crop_x) * self.width / self.crop_width,
                (point[1] - self.crop_y) * self.height / self.crop_height)

    def to_original(self, point):
        return (point[0] * self.crop_width / self.width + self.crop_x,
                point[1] * self.crop_height / self.height + self.crop_y)


def draw_detection(frame_rgb, result, selections, confirmed, transform, show_candidates=True, selected_id=None):
    """Draw measured edges separately from shared-center manual references."""
    centers = []
    label_boxes = []
    for edge in result.candidates:
        role = next((name for name, candidate_id in selections.items() if candidate_id == edge.id), None)
        if role is None and not show_candidates:
            continue
        palette = ((255, 215, 65), (80, 225, 255), (255, 125, 230), (150, 255, 170))
        color = FEATURE_COLORS[FEATURE_NAMES.index(role)] if role else palette[(edge.id - 1) % len(palette)]
        pts = np.rint([transform.to_display(point) for point in edge.points(288)]).astype(np.int32)
        is_confirmed = result.guide_center is not None or role in confirmed
        thickness = 2 if edge.id == selected_id else 1
        # Missing portions stay empty: the fitted geometry is not observed evidence.
        # Supported portions are solid only after confirmation.
        loop = np.vstack((pts, pts[:1]))
        support = set(edge.support_bins)
        for start in range(0, len(pts), 4):
            observed = not support or start // 4 in support
            if not observed:
                if role == "Focuser edge" and start // 4 % 2 == 0:
                    segment = loop[start:start + 2]
                    inferred_color = tuple(round(v * 0.65) for v in color)
                    cv2.polylines(frame_rgb, [segment], False, (0, 0, 0), 2, cv2.LINE_AA)
                    cv2.polylines(frame_rgb, [segment], False, inferred_color, 1, cv2.LINE_AA)
                continue
            length = 5 if is_confirmed else 3
            if not is_confirmed and observed and start // 4 % 3 == 2:
                continue
            segment = loop[start:start + length]
            cv2.polylines(frame_rgb, [segment], False, (0, 0, 0), thickness + 1, cv2.LINE_AA)
            cv2.polylines(frame_rgb, [segment], False, color, thickness, cv2.LINE_AA)
        center = tuple(round(value) for value in transform.to_display(edge.center))
        centers.append((center, color))
        text = (f"{edge.id}: {role}" if show_candidates else role) if role else f"{edge.id}: candidate"
        if role and not is_confirmed:
            text += " ?"
        if edge.provenance == "focuser_circle_estimate":
            text += " [circle estimate]"
        if edge.provenance == "manual_drag":
            text += " [manual]"
        if edge.clipped or edge.coverage is not None and edge.coverage < 0.85:
            text += " [partial]"
        if (edge.edge_width or 0) >= SOFT_EDGE_WIDTH:
            text += " [soft]"
        if edge.id == selected_id:
            text = "> " + text
        supported_points = pts[np.isin(np.arange(len(pts)) // 4, tuple(support))] if support else pts
        visible = supported_points[(supported_points[:, 0] >= 0) & (supported_points[:, 0] < frame_rgb.shape[1]) &
                                   (supported_points[:, 1] >= 0) & (supported_points[:, 1] < frame_rgb.shape[0])]
        if not len(visible):
            continue
        anchor = visible[np.argmin(visible[:, 1])]
        (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        x = max(5, min(frame_rgb.shape[1] - text_width - 8, int(anchor[0]) - text_width // 2))
        y = max(text_height + 8, min(frame_rgb.shape[0] - baseline - 8, int(anchor[1]) - 10))
        # Keep nearby rim labels readable instead of piling them on one another.
        for offset in (0, -1, 1, -2, 2, -3, 3, -4, 4, -5, 5):
            proposed_y = y + offset * (text_height + baseline + 12)
            if not text_height + 8 <= proposed_y <= frame_rgb.shape[0] - baseline - 8:
                continue
            box = (x - 4, proposed_y - text_height - 5, x + text_width + 4, proposed_y + baseline + 4)
            if all(box[2] < previous[0] or box[0] > previous[2] or
                   box[3] < previous[1] or box[1] > previous[3] for previous in label_boxes):
                y = proposed_y
                break
        label_boxes.append((x - 4, y - text_height - 5, x + text_width + 4, y + baseline + 4))
        cv2.rectangle(frame_rgb, (x - 4, y - text_height - 5), (x + text_width + 4, y + baseline + 4), (0, 0, 0), -1)
        cv2.putText(frame_rgb, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    if result.guide_center is not None and centers:
        centers = [(centers[0][0], (255, 255, 255))]
    center_thickness = 2 if result.guide_center is not None else 1
    for center, color in centers:
        cv2.drawMarker(frame_rgb, center, (0, 0, 0), cv2.MARKER_CROSS, 11, center_thickness + 1)
    for center, color in centers:
        cv2.drawMarker(frame_rgb, center, color, cv2.MARKER_CROSS, 11, center_thickness)
        cv2.circle(frame_rgb, center, 1, color, -1)
