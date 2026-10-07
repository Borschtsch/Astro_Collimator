from dataclasses import replace
import gc
import threading
import time
import tkinter as tk
import unittest
import tempfile
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np
from PIL import ImageTk

from source.app import CameraWorker, WebcamApp, prepare_frame
from source.camera_properties import PropertyInfo
from source.app_options import OptionsStore, TelescopeProfile
from tests.fixtures.images import optical_fixture
from tests.fixtures.camera import FakeCapture


class WorkerTests(unittest.TestCase):
    def start_worker(self, factory, capability_provider=None):
        worker = CameraWorker(factory, max_cameras=4, capability_provider=capability_provider)
        worker.start()
        self.addCleanup(self.stop_worker, worker)
        return worker

    def stop_worker(self, worker):
        worker.stop_event.set()
        worker.join(2)
        self.assertFalse(worker.is_alive())

    def event(self, worker, kind):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            session, actual_kind, data = worker.events.get(timeout=2)
            if actual_kind == kind:
                return session, data
        self.fail(f"Missing {kind} event")

    def test_discovery_checks_gaps_and_releases_all_probes(self):
        captures = []

        def factory(index):
            cap = FakeCapture(index, opened=index in (0, 2))
            captures.append(cap)
            return cap

        worker = self.start_worker(factory)
        worker.commands.put((1, "scan", None))
        session, cameras = self.event(worker, "cameras")
        self.assertEqual((session, cameras), (1, [0, 2]))
        self.assertEqual(len(captures), 4)
        self.assertTrue(all(cap.released for cap in captures))

    def test_open_failure_and_disconnect_release_device(self):
        captures = []

        def factory(index):
            cap = FakeCapture(index, opened=index != 0, read_ok=False)
            captures.append(cap)
            return cap

        worker = self.start_worker(factory)
        worker.commands.put((1, "open", 0))
        self.assertIn("Failed to open", self.event(worker, "error")[1])
        worker.commands.put((2, "open", 1))
        self.event(worker, "opened")
        self.assertEqual(self.event(worker, "disconnected")[0], 2)
        self.assertTrue(all(cap.released for cap in captures))

    def test_switches_and_properties_stay_on_one_thread(self):
        captures = []

        def factory(index):
            cap = FakeCapture(index)
            captures.append(cap)
            return cap

        worker = self.start_worker(factory)
        worker.commands.put((1, "open", 0))
        self.event(worker, "opened")
        for session in range(2, 12):
            worker.commands.put((session, "open", session))
        worker.commands.put((1, "set", (cv2.CAP_PROP_GAIN, 99)))
        worker.commands.put((11, "set", (cv2.CAP_PROP_GAIN, 123.5)))
        session, (prop, actual, message) = self.event(worker, "property")
        self.assertEqual((session, actual), (11, 123.5))
        self.assertTrue(all(cap.released for cap in captures[:-1]))
        self.assertTrue(all(not cap.set_calls for cap in captures[:-1]))
        self.assertEqual(captures[-1].set_calls, [(cv2.CAP_PROP_GAIN, 123.5)])
        self.assertEqual(len({cap.owner for cap in captures}), 1)
        self.stop_worker(worker)
        self.assertTrue(captures[-1].released)

    def test_rejected_clamped_and_exceptional_controls(self):
        for setting, expected in (("reject", "rejected"), ("clamp", "adjusted or ignored"),
                                  ("error", "operation failed")):
            with self.subTest(setting=setting):
                worker = self.start_worker(lambda index: FakeCapture(index, setting=setting))
                worker.commands.put((1, "open", 0))
                self.event(worker, "opened")
                worker.commands.put((1, "set", (cv2.CAP_PROP_GAIN, 100)))
                _, data = self.event(worker, "error" if setting == "error" else "property")
                self.assertIn(expected, data if isinstance(data, str) else data[2])
                self.stop_worker(worker)

    def test_shutdown_during_blocked_read_keeps_release_on_owner_thread(self):
        reading = threading.Event()
        unblock = threading.Event()
        captures = []

        class BlockingCapture(FakeCapture):
            def read(self):
                reading.set()
                unblock.wait(2)
                return super().read()

        def factory(index):
            cap = BlockingCapture(index)
            captures.append(cap)
            return cap

        worker = self.start_worker(factory)
        worker.commands.put((1, "open", 0))
        self.assertTrue(reading.wait(2))
        worker.stop_event.set()
        self.assertFalse(captures[0].released)
        unblock.set()
        self.stop_worker(worker)
        self.assertTrue(captures[0].released)

    def test_capabilities_are_queried_before_open_and_enforced(self):
        order = []
        captures = []
        ranges = {"Gain": PropertyInfo("supported", 3, 19, 4, 7, 2),
                  "Zoom": PropertyInfo("unsupported"),
                  "Focus": PropertyInfo("supported", 0, 100, 1, 50, 1)}

        def query(index):
            order.append("query")
            return ranges

        def factory(index):
            order.append("open")
            cap = FakeCapture(index)
            captures.append(cap)
            return cap

        worker = self.start_worker(factory, query)
        worker.commands.put((1, "open", 0))
        _, (values, capabilities) = self.event(worker, "opened")
        self.assertEqual(order, ["query", "open"])
        self.assertEqual(capabilities[cv2.CAP_PROP_GAIN], ranges["Gain"])
        self.assertEqual(captures[0].set_calls, [])
        for prop in (cv2.CAP_PROP_ZOOM, cv2.CAP_PROP_FOCUS):
            worker.commands.put((1, "set", (prop, 50)))
            self.assertIn("unavailable", self.event(worker, "property")[1][2])
        worker.commands.put((1, "set", (cv2.CAP_PROP_GAIN, 14)))
        self.assertEqual(self.event(worker, "property")[1][1], 15)
        self.assertEqual(captures[0].set_calls, [(cv2.CAP_PROP_GAIN, 15)])


class FrameTests(unittest.TestCase):
    def test_aspect_ratio_and_color_are_preserved(self):
        for height, width in ((720, 1280), (480, 640), (1280, 720)):
            for zoom in (1, 2, 3):
                with self.subTest(size=(width, height), zoom=zoom):
                    frame = np.zeros((height, width, 3), dtype=np.uint8)
                    frame[:, :] = (10, 20, 30)
                    result = prepare_frame(frame, zoom, 960, 720)
                    h, w = result.shape[:2]
                    self.assertLessEqual(w, 960)
                    self.assertLessEqual(h, 720)
                    self.assertAlmostEqual(w / h, width / height, delta=0.01)
                    np.testing.assert_array_equal(result[h // 2, w // 2], (30, 20, 10))

    def test_zoom_crops_center_instead_of_stretching(self):
        frame = np.zeros((120, 120, 3), dtype=np.uint8)
        frame[40:80, 40:80] = (0, 0, 255)
        result = prepare_frame(frame, 3, 120, 120)
        self.assertTrue(np.all(result[:, :, 0] == 255))
        self.assertTrue(np.all(result[:, :, 1:] == 0))

