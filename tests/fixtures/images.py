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

