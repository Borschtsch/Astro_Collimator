"""V4L2 hardware-boundary substitute; application queries and UI remain real."""

from contextlib import ExitStack
import errno
import os
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import patch

import cv2

from source.linux_camera import CONTROL, CONTROL_IDS, QUERY_CONTROL
from .camera import FakeCapture
from .images import pupil_fixture


class LinuxCameraHardware:
    def __init__(self, permission_denied=False):
        self.permission_denied = permission_denied
        self.captures = []
        self.queries = []
        self.closed = []

    def __enter__(self):
        self.stack = ExitStack()
        original_open, original_close, original_glob = os.open, os.close, Path.glob

        def open_device(path, flags, *args, **kwargs):
            if str(path).startswith("/dev/video"):
                if self.permission_denied:
                    raise PermissionError(errno.EACCES, "Camera permission denied")
                return 100000 + int(str(path)[10:])
            return original_open(path, flags, *args, **kwargs)

        def close_device(descriptor):
            if descriptor in (100002, 100014):
                self.closed.append(descriptor)
            else:
                original_close(descriptor)

        def glob_devices(path, pattern, *args, **kwargs):
            if path == Path("/dev") and pattern == "video*":
                return iter([Path("/dev/video14"), Path("/dev/video2"), Path("/dev/video-bad")])
            return original_glob(path, pattern, *args, **kwargs)

        def ioctl(descriptor, request, buffer, mutate):
            assert request == QUERY_CONTROL and mutate
            control_id = CONTROL.unpack(buffer)[0]
            self.queries.append((descriptor, control_id, threading.get_ident()))
            if control_id == CONTROL_IDS["Exposure"]:
                raise OSError(errno.EINVAL, "No such control")
            if control_id == CONTROL_IDS["Zoom"]:
                raise OSError(errno.EIO, "Driver query failed")
            flags = 0x10 if control_id == CONTROL_IDS["Focus"] else 0
            step = 0 if descriptor == 100014 and control_id == CONTROL_IDS["Gain"] else 4
            buffer[:] = CONTROL.pack(control_id, 1, b"Hardware control", 3, 19, step, 7, flags, 0, 0)
            return 0

        def capture(path, backend):
            assert backend == cv2.CAP_V4L2 and path in ("/dev/video2", "/dev/video14")
            cap = FakeCapture(int(path[10:]))
            cap.values[cv2.CAP_PROP_GAIN] = 7
            cap.frame = pupil_fixture()
            self.captures.append(cap)
            return cap

        for context in (patch("sys.platform", "linux"),
                        patch.dict("sys.modules", {"fcntl": SimpleNamespace(ioctl=ioctl)}),
                        patch("os.O_NONBLOCK", getattr(os, "O_NONBLOCK", 2048), create=True),
                        patch("os.open", side_effect=open_device),
                        patch("os.close", side_effect=close_device),
                        patch.object(Path, "glob", glob_devices),
                        patch("cv2.VideoCapture", side_effect=capture)):
            self.stack.enter_context(context)
        return self

    def __exit__(self, *args):
        return self.stack.__exit__(*args)
