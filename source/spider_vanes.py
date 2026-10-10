"""Offline straight-spider evidence and independently rotatable crosshairs."""

from dataclasses import asdict, dataclass
import math

import cv2
import numpy as np


@dataclass(frozen=True)
class VaneDetection:
    count: int | None = None
    angle_deg: float | None = None
    directions_deg: tuple[float, ...] = ()
    confidence: float = 0.0
    center: tuple[float, float] | None = None
    message: str = "No clear centered vanes. Improve focus and illumination."

    @property
    def blades(self):
        return 3 if self.count == 3 and self.confidence >= .75 else 4

    def to_dict(self):
        return asdict(self)


def _reference(gray, result):
    if result is None:
        return None
    observations = result.observations or result.candidates
    primary_id = result.suggested.get("Primary reflection")
    primary = next((edge for edge in observations if edge.id == primary_id), None)
    if primary is None:
        # Identify a bright reflecting face without relying on the guide center.
        choices = []
        angles = np.linspace(0, 2 * math.pi, 180, endpoint=False)
        for edge in observations:
            if edge.kind != "boundary" or edge.radius < 30:
                continue
            values = []
            for fraction in (.65, 1.06):
                x = np.rint(edge.center[0] + edge.radius * fraction * np.cos(angles)).astype(int)
                y = np.rint(edge.center[1] + edge.radius * fraction * np.sin(angles)).astype(int)
                visible = (x >= 0) & (x < gray.shape[1]) & (y >= 0) & (y < gray.shape[0])
                values.append(float(np.median(gray[y[visible], x[visible]])) if visible.sum() > 100 else 0)
            contrast = values[0] - values[1]
            if contrast > 15:
                choices.append((contrast, edge))
        primary = max(choices, key=lambda item: item[0])[1] if choices else None
    if primary is None:
        return None
    return primary.center, primary.radius


def detect_vanes(frame, result):
    """Count straight radial arms, rejecting weak/partial/non-centered patterns."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Ignore saturated annotation ink in reference photographs. Real low-value
    # dark supports remain intact; raw input/export pixels are never altered.
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    ink = ((hsv[:, :, 0] >= 140) & (hsv[:, :, 0] <= 170) &
           (hsv[:, :, 1] > 35) & (hsv[:, :, 2] > 100)).astype(np.uint8) * 255
    if np.any(ink):
        gray = cv2.inpaint(gray, ink, 3, cv2.INPAINT_TELEA)
    reference = _reference(gray, result)
    if reference is None:
        return VaneDetection(message="Show a focused primary reflection for alignment.")
    center, radius = reference
    scale = min(1, 960 / max(gray.shape))
    gray = cv2.resize(gray, None, fx=scale, fy=scale).astype(np.float32)
    center = np.array(center, dtype=float) * scale
    radius *= scale
    if radius < 25:
        return VaneDetection(message="The reflection is too small. Zoom the camera view or use a larger image.")
    # Line intersections estimate the spider hub independently of circular guides.
    yy, xx = np.indices(gray.shape)
    mask = ((xx - center[0]) ** 2 + (yy - center[1]) ** 2 < (.88 * radius) ** 2)
    edges = cv2.Canny(gray.astype(np.uint8), 35, 90)
    edges[~mask] = 0
    lines = cv2.HoughLinesP(edges, 1, math.pi / 720, max(15, round(radius * .14)),
                            minLineLength=max(15, radius * .27), maxLineGap=radius * .08)
    spokes = []
    for line in (() if lines is None else lines.reshape(-1, 4)):
        point = np.array(line[:2], dtype=float)
        direction = np.array(line[2:], dtype=float) - point
        length = np.linalg.norm(direction)
        direction /= max(length, 1)
        delta = center - point
        distance = abs(direction[0] * delta[1] - direction[1] * delta[0])
        if distance < radius * .18:
            spokes.append((length, point, direction))
    spokes = sorted(spokes, key=lambda item: item[0], reverse=True)[:24]
    crossings = []
    for i, (_, p, u) in enumerate(spokes):
        for _, q, v in spokes[i + 1:]:
            determinant = u[0] * v[1] - u[1] * v[0]
            if abs(determinant) < .45:
                continue
            delta = q - p
            crossing = p + u * (delta[0] * v[1] - delta[1] * v[0]) / determinant
            if np.linalg.norm(crossing - center) < radius * .23:
                crossings.append(crossing)
    if len(crossings) >= 3:
        center = np.median(crossings, axis=0)
    # Compare every radial sample with nearby angular background. A real vane
    # remains dark over most of the radius; clips and arcs do not.
    theta = np.deg2rad(np.arange(720) / 2)
    radii = np.linspace(radius * .40, radius * .86, 128)
    x = (center[0] + np.cos(theta)[:, None] * radii).astype(np.float32)
    y = (center[1] + np.sin(theta)[:, None] * radii).astype(np.float32)
    if ((x < 0) | (x >= gray.shape[1] - 1) | (y < 0) | (y >= gray.shape[0] - 1)).any():
        return VaneDetection(message="Include the full primary reflection for alignment.")
    polar = cv2.remap(gray, x, y, cv2.INTER_LINEAR)
    padded = np.concatenate((polar[-20:], polar, polar[:20]))
    background = cv2.GaussianBlur(padded, (1, 41), 0, sigmaY=8)[20:-20]
    contrast = np.abs(background - polar)
    left, right = np.roll(polar, 8, axis=0), np.roll(polar, -8, axis=0)
    # A support must itself be a narrow local light/dark extremum along most
    # of its length. Smoothing shadows beside a curved arm are not straight arms.
    narrow = ((np.minimum(left - polar, right - polar) > 3) |
              (np.minimum(polar - left, polar - right) > 3))
    support = ((contrast > 7) & narrow).mean(axis=1)
    scores = np.maximum(contrast, 0).mean(axis=1)
    threshold = max(9, min(30, float(scores.max())) * .35)
    peaks = []
    for index in np.argsort(scores)[::-1]:
        if scores[index] < threshold:
            break
        if support[index] < .60:
            continue
        if any(min(abs(int(index) - old), 720 - abs(int(index) - old)) < 22 for old in peaks):
            continue
        peaks.append(int(index))
    if not 2 <= len(peaks) <= 16:
        return VaneDetection()
    # Find a coherent spider among competing roof beams/annotation remnants.
    # One very bright arm must not suppress the other, fainter arms.
    hypotheses = {}
    for count in (3, 4, 2):
        if count == 2 and len(peaks) != 2:
            continue
        step = 360 / count
        for base in peaks:
            group = []
            for arm in range(count):
                target = (base / 2 + arm * step) % 360
                nearest = min(peaks, key=lambda index: abs((index / 2 - target + 180) % 360 - 180))
                if abs((nearest / 2 - target + 180) % 360 - 180) > (5 if count == 3 else 7):
                    break
                group.append(nearest)
            if len(set(group)) != count:
                continue
            indices = tuple(sorted(group))
            if count == 3 and float(support[list(indices)].min()) < .75:
                continue
            angles = np.array(indices, dtype=float) / 2
            phase = np.mean(np.exp(1j * np.deg2rad(angles * count)))
            confidence = float(min(1, support[list(indices)].mean() * abs(phase)))
            if confidence < .75 or abs(phase) < .95:
                continue
            strength = float(np.exp(np.log(scores[list(indices)]).mean()))
            hypotheses[indices] = (strength, confidence, angles)
    if not hypotheses:
        return VaneDetection(message="No coherent straight vane pattern. Improve focus/illumination or set rotation manually.")
    ranked = sorted(hypotheses.values(), key=lambda item: item[0], reverse=True)
    if len(ranked) > 1 and ranked[0][0] < ranked[1][0] * 1.15:
        return VaneDetection(message="Competing line patterns. Set rotation manually.")
    _, confidence, angles = ranked[0]
    display_step = 120 if len(angles) == 3 else 90
    phase = np.mean(np.exp(1j * np.deg2rad(angles * (360 / display_step))))
    alignment = (math.degrees(math.atan2(phase.imag, phase.real)) * display_step / 360) % display_step
    return VaneDetection(len(angles), alignment, tuple(float(a) for a in angles), confidence,
                         tuple(float(v / scale) for v in center), "Alignment measured.")


def draw_crosshair(frame, center, angle_deg=0, blades=4, color=(255, 255, 255),
                   thickness=2, radius=5, transform=None, full_frame=False):
    """Rotate raw-image directions through the same transform as the image."""
    sx = transform.width / transform.crop_width if transform else 1
    sy = transform.height / transform.crop_height if transform else 1
    length = math.hypot(*frame.shape[:2]) * 2 if full_frame else radius
    segments = []
    shift, unit = 8, 256  # Preserve fractional FOV intersection and ray endpoints.
    for index in range(blades // 2 if blades == 4 else blades):
        angle = math.radians(angle_deg + index * 360 / blades)
        raw_vector = (math.cos(angle), math.sin(angle))
        vector = np.array(transform.to_display_vector(raw_vector) if transform else raw_vector)
        vector *= length / np.linalg.norm(vector)
        start = np.array(center) - vector if blades == 4 else np.array(center)
        end = np.array(center) + vector
        # Clip before conversion; centers can be far offscreen after zoom/pan.
        visible, p, q = cv2.clipLine((0, 0, frame.shape[1] * unit, frame.shape[0] * unit),
                                    tuple(int(round(v * unit)) for v in start),
                                    tuple(int(round(v * unit)) for v in end))
        if visible:
            segments.append((p, q))
    if full_frame:
        # Preserve the zero-degree four-blade FOV's original stroke ordering.
        for p, q in reversed(segments):
            cv2.line(frame, p, q, (0, 0, 0), thickness + 2, cv2.LINE_AA, shift=shift)
            cv2.line(frame, p, q, color, thickness, cv2.LINE_AA, shift=shift)
    else:
        for p, q in segments:
            cv2.line(frame, p, q, (0, 0, 0), thickness + 1, cv2.LINE_AA, shift=shift)
        for p, q in segments:
            cv2.line(frame, p, q, color, thickness, cv2.LINE_AA, shift=shift)
        cv2.circle(frame, tuple(round(v * unit) for v in center), unit, color, -1, cv2.LINE_AA, shift=shift)
