"""Bounded offline temporal denoising and local tracking of identified references."""

from collections import deque
from dataclasses import dataclass, replace
import math
from time import perf_counter

import cv2
import numpy as np

from .feature_detection import (DetectionResult, EdgeCandidate, SOFT_EDGE_WIDTH,
                               _fit_contour, _rim_evidence, concentric_guides)


class SteadyFrameAverage:
    """Keep three recent frames; reset on distributed or local visible changes."""

    def __init__(self, max_frames=3, max_age=.12):
        self.max_frames = max_frames
        self.max_age = max_age
        self.reset()

    def reset(self):
        self.frames = deque(maxlen=self.max_frames)
        self.preview = None
        self.shape = None

    def add(self, frame, timestamp):
        height, width = frame.shape[:2]
        scale = min(1, 256 / max(width, height))
        small = cv2.resize(frame, (max(8, round(width * scale)), max(8, round(height * scale))),
                           interpolation=cv2.INTER_AREA)
        preview = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (0, 0), 1)
        if (self.shape != frame.shape or self.frames and
                (timestamp < self.frames[-1][0] or timestamp - self.frames[-1][0] > self.max_age)):
            self.reset()
        if self.preview is not None:
            difference = cv2.absdiff(preview, self.preview)
            # Max local block change catches a moving pupil/mark, not just camera motion.
            blocks = cv2.resize(difference.astype(np.float32),
                                (max(1, preview.shape[1] // 8), max(1, preview.shape[0] // 8)),
                                interpolation=cv2.INTER_AREA)
            noise = float(np.median(difference))
            brightness_shift = abs(float(np.median(preview.astype(np.float32) - self.preview)))
            shift, response = cv2.phaseCorrelate(self.preview.astype(np.float32), preview.astype(np.float32))
            moved = response >= .3 and math.hypot(*shift) > .35
            if (brightness_shift > 3 or moved or difference.mean() > max(1.5, noise * 1.7)
                    or blocks.max() > max(3, noise * 3)):
                self.reset()
        while self.frames and timestamp - self.frames[0][0] > self.max_age:
            self.frames.popleft()
        self.frames.append((timestamp, frame.copy()))
        self.preview = preview
        self.shape = frame.shape

    def snapshot(self, timestamp):
        while self.frames and timestamp - self.frames[0][0] > self.max_age:
            self.frames.popleft()
        return tuple(frame for _, frame in self.frames)


def average_frames(frames):
    if len(frames) == 1:
        return frames[0].copy()
    # OpenCV weighted sums avoid a large float stack; at most three captured frames.
    averaged = frames[0].copy()
    for index, frame in enumerate(frames[1:], start=1):
        averaged = cv2.addWeighted(averaged, index / (index + 1), frame, 1 / (index + 1), 0)
    return averaged


def _eligible(edge):
    return (edge is not None and (edge.fit_quality or 0) >= .65
            and not edge.provenance.startswith("manual")
            and (edge.edge_width or 0) < SOFT_EDGE_WIDTH)


def can_track_locally(previous, selections):
    observations = {edge.id: edge for edge in previous.observations} if previous else {}
    if "Focuser edge" in selections and not _eligible(observations.get(selections["Focuser edge"])):
        return False
    return any(_eligible(observations.get(selections.get(role)))
               for role in ("Focuser edge", "Secondary edge", "Primary reflection"))


def _track_detail(edge, gray, normalized=None):
    """Fit only in the neighborhood of the previously identified mark/pupil."""
    height, width = gray.shape
    pad = edge.radius * 1.5 + 8
    left, top = max(0, int(edge.center[0] - pad)), max(0, int(edge.center[1] - pad))
    right, bottom = min(width, math.ceil(edge.center[0] + pad)), min(height, math.ceil(edge.center[1] + pad))
    roi = (normalized if normalized is not None else gray)[top:bottom, left:right]
    if min(roi.shape, default=0) < 8:
        return None
    contours, _ = cv2.findContours(cv2.Canny(cv2.GaussianBlur(roi, (5, 5), 0), 20, 60),
                                   cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    options = []
    for contour in contours:
        shifted = contour + np.array([[[left, top]]], dtype=contour.dtype)
        if edge.kind == "mark_triangle":
            polygon = cv2.approxPolyDP(shifted, .045 * cv2.arcLength(shifted, True), True)
            if len(polygon) != 3 or not cv2.isContourConvex(polygon):
                continue
            moments = cv2.moments(polygon)
            if moments["m00"] < 8:
                continue
            radius = math.sqrt(moments["m00"] / math.pi)
            found = EdgeCandidate(edge.id, (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]),
                                  (radius, radius), 0, kind=edge.kind, fit_quality=.8, coverage=1)
        else:
            found = _fit_contour(shifted, gray)
        if found is None or (found.fit_quality or 0) < .7:
            continue
        distance, ratio = math.dist(found.center, edge.center), found.radius / edge.radius
        if distance <= max(4, edge.radius * .25) and .8 <= ratio <= 1.2:
            options.append((distance / max(1, edge.radius) + abs(math.log(ratio)), found))
    return replace(min(options, key=lambda item: item[0])[1], id=edge.id, kind=edge.kind,
                   provenance="tracked_local") if options else None


def track_local(frame, previous, selections, max_dimension=960):
    """Return fresh independent evidence or None to request full rediscovery."""
    start = perf_counter()
    height, width = frame.shape[:2]
    if previous is None or previous.image_size != (width, height) or not can_track_locally(previous, selections):
        return None
    scale = min(1.0, max_dimension / max(height, width))
    small = cv2.resize(frame, (round(width * scale), round(height * scale))) if scale < 1 else frame
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    if np.percentile(gray, 99) - np.percentile(gray, 1) < 15:
        return None
    normalized = cv2.createCLAHE(clipLimit=2, tileGridSize=(8, 8)).apply(gray)
    smooth = cv2.GaussianBlur(normalized, (0, 0), 1.8).astype(np.float32)
    gradients = (cv2.Sobel(smooth, cv2.CV_32F, 1, 0), cv2.Sobel(smooth, cv2.CV_32F, 0, 1))
    observations = {edge.id: edge for edge in previous.observations}
    found, roles = [], {}
    for role, candidate_id in selections.items():
        old = observations.get(candidate_id)
        if not _eligible(old):
            continue  # Manual/held geometry is reacquired by periodic full detection.
        seed = replace(old, center=tuple(v * scale for v in old.center), axes=tuple(v * scale for v in old.axes))
        if role in ("Center mark", "Camera pupil"):
            edge = _track_detail(seed, gray, normalized)
        else:
            edge = _rim_evidence(seed, smooth, gradient_field=gradients,
                                 circular=role == "Focuser edge",
                                 max_eccentricity=0 if role == "Focuser edge" else .55,
                                 polarity=-1 if role == "Primary reflection" else None)
        if (edge is None or (edge.fit_quality or 0) < .65 or (edge.edge_width or 0) >= SOFT_EDGE_WIDTH
                or math.dist(edge.center, seed.center) > max(6, seed.radius * .05)
                or not ((.8 if role in ("Center mark", "Camera pupil") else .94)
                        <= edge.radius / seed.radius <= (1.2 if role in ("Center mark", "Camera pupil") else 1.06))):
            return None
        found.append(replace(edge, id=old.id, kind=old.kind, provenance="tracked_local",
                             center=tuple(float(v / scale) for v in edge.center),
                             axes=tuple(float(v / scale) for v in edge.axes)))
        roles[role] = old.id
    if not found:
        return None
    result = DetectionResult((width, height), tuple(found), roles,
                             ("Tracked existing references from fresh local edge evidence.",),
                             (perf_counter() - start) * 1000)
    return concentric_guides(result)


@dataclass(frozen=True)
class LiveDetection:
    result: DetectionResult
    frame: np.ndarray
    mode: str
    averaged_frames: int


def detect_live(frames, previous, selections, shape, full_detector, force_full=False):
    frame = average_frames(frames)
    result = None if force_full else track_local(frame, previous, selections)
    mode = "local" if result is not None else "full"
    if result is None:
        result = full_detector(frame, shape)
    return LiveDetection(result, frame, mode, len(frames))
