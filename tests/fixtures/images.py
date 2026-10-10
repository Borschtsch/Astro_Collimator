from pathlib import Path

import cv2
import numpy as np


TEST_IMAGES = Path(__file__).resolve().parents[1] / "images"


def optical_fixture(size=(800, 600), ellipse=False, triangle=False, circular_focuser=False):
    frame = np.full((600, 800, 3), 25, dtype=np.uint8)
    for center, radius, value in (((400, 300), 250, 120), ((412, 296), 200, 40),
                                  ((418, 300), 160, 190)):
        oval = ellipse and not (circular_focuser and radius == 250)
        cv2.ellipse(frame, center, (radius, round(radius * 0.85) if oval else radius),
                    18 if oval else 0, 0, 360, (value,) * 3, -1, cv2.LINE_AA)
    if triangle:
        cv2.fillPoly(frame, [np.array([[421, 290], [410, 310], [432, 310]])], (20,) * 3, cv2.LINE_AA)
    else:
        cv2.circle(frame, (421, 302), 10, (20,) * 3, -1, cv2.LINE_AA)
    return cv2.resize(frame, size)


def pupil_fixture(size=(800, 600), mark=True, opening=True):
    frame = optical_fixture()
    cv2.circle(frame, (405, 285), 36, (24,) * 3, -1, cv2.LINE_AA)
    if opening:
        cv2.circle(frame, (405, 285), 12, (160,) * 3, -1, cv2.LINE_AA)
    if mark:
        cv2.circle(frame, (447, 330), 7, (10,) * 3, 2, cv2.LINE_AA)
    return cv2.resize(frame, size)



def spider_fixture(count=4, angle=0, design="straight", blur=0):
    """Raw reflecting face with centered, curved or offset spider supports."""
    import math
    frame = optical_fixture()
    center = (418, 300)
    for index in range(count):
        direction = math.radians(angle + index * 360 / count)
        points = []
        for radius in range(25, 161):
            theta = direction + (radius / 160 * .6 if design == "curved" else 0)
            points.append((round(center[0] + radius * math.cos(theta)),
                           round(center[1] + radius * math.sin(theta) + (45 if design == "offset" else 0))))
        cv2.polylines(frame, [np.array(points, np.int32)], False, (20, 20, 20), 4)
    cv2.circle(frame, center, 30, (30, 30, 30), -1)
    return cv2.GaussianBlur(frame, (0, 0), blur) if blur else frame


def red_pixels(rgb):
    """Recognize visible red references, allowing antialiased edge intensity."""
    rgb = np.asarray(rgb)[..., :3].astype(float)
    return (rgb[..., 0] > 140) & (rgb[..., 0] > 1.8 * np.maximum(rgb[..., 1], rgb[..., 2]))


def color_matches(rgb, color):
    """Allow feathered stroke intensity while distinguishing reference colors."""
    return np.max(np.abs(np.asarray(rgb, dtype=int) - color)) <= 65
