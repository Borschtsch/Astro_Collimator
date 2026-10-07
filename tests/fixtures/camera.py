import threading

import cv2
import numpy as np


class FakeCapture:
    def __init__(self, index, opened=True, read_ok=True, setting="accept"):
        self.index = index
        self.opened = opened
        self.read_ok = read_ok
        self.setting = setting
        self.released = False
        self.owner = threading.get_ident()
        self.values = {cv2.CAP_PROP_GAIN: 500.5, cv2.CAP_PROP_EXPOSURE: 12.25}
        self.set_calls = []
        self.frame = np.zeros((90, 160, 3), dtype=np.uint8)

    def check_owner(self):
        if self.owner != threading.get_ident():
            raise AssertionError("Camera accessed from another thread")

    def isOpened(self):
        self.check_owner()
        return self.opened and not self.released

    def get(self, prop):
        self.check_owner()
        return self.values.get(prop, 0)

    def set(self, prop, value):
        self.check_owner()
        self.set_calls.append((prop, value))
        if self.setting == "reject":
            return False
        if self.setting == "error":
            raise cv2.error("Unsupported property")
        self.values[prop] = min(value, 20) if self.setting == "clamp" else value
        return True

    def read(self):
        self.check_owner()
        if self.released:
            raise AssertionError("Read after release")
        return self.read_ok, self.frame.copy() if self.read_ok else None

    def release(self):
        self.check_owner()
        self.released = True

