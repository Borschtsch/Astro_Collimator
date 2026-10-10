"""Read V4L2 camera ranges without changing device values or automatic modes.

Uses the stable Linux UAPI for integer controls on x86_64/aarch64. No external
command, vendor SDK or Python dependency is needed. Imported lazily on Linux.
"""

import errno
import os
from pathlib import Path
import struct

from .camera_properties import PropertyInfo


# linux/videodev2.h: struct v4l2_queryctrl (64 bytes), VIDIOC_QUERYCTRL.
QUERY_CONTROL = 0xC0405624
CONTROL = struct.Struct("=II32siiiiI2I")
CONTROL_IDS = {"Gain": 0x00980913, "Exposure": 0x009A0902,
               "Zoom": 0x009A090D, "Focus": 0x009A090A}


def camera_indices():
    return sorted(int(path.name[5:]) for path in Path("/dev").glob("video*")
                  if path.name[5:].isdigit())


def query_camera_properties(index):
    import fcntl

    results = {}
    try:
        descriptor = os.open(f"/dev/video{index}", os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        # Permissions, disconnected devices and busy drivers are not evidence
        # that controls are unsupported. The UI retains its numeric fallback.
        return results
    try:
        for name, control_id in CONTROL_IDS.items():
            buffer = bytearray(CONTROL.pack(control_id, 0, b"", 0, 0, 0, 0, 0, 0, 0))
            try:
                fcntl.ioctl(descriptor, QUERY_CONTROL, buffer, True)
            except OSError as error:
                results[name] = PropertyInfo("unsupported" if error.errno == errno.EINVAL else "unknown")
                continue
            _, control_type, _, minimum, maximum, step, default, flags, _, _ = CONTROL.unpack(buffer)
            if flags & 0x0001:  # V4L2_CTRL_FLAG_DISABLED
                results[name] = PropertyInfo("unsupported")
            elif control_type != 1 or minimum > maximum or (step <= 0 and minimum != maximum):
                results[name] = PropertyInfo()
            else:
                # PropertyInfo flags describe manual/automatic availability,
                # not native V4L2 bit values. Never enable locked controls.
                availability = 0 if flags & (0x0002 | 0x0004) else 1 if flags & 0x0010 else 2
                if flags & 0x0080 and not flags & 0x0200:
                    availability = 1  # volatile auto value: writes are ignored
                results[name] = PropertyInfo("supported", minimum, maximum, max(1, step), default, availability)
    finally:
        os.close(descriptor)
    return results


def query_camera_names(indices):
    names = {}
    for index in indices:
        try:
            names[index] = Path(f"/sys/class/video4linux/video{index}/name").read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            continue
    return names
