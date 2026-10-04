"""Read Windows camera capabilities without setting any camera values.

OpenCV's DirectShow backend and this module both use the system video-device
moniker order. Call only on the camera worker, before opening the video stream.
No COM pointers leave the querying thread and every reference is released.

API: https://learn.microsoft.com/en-us/windows/win32/api/strmif/nf-strmif-iamcameracontrol-getrange
"""

import ctypes as ct
from contextlib import contextmanager
from dataclasses import dataclass
import sys
from uuid import UUID


@dataclass(frozen=True)
class PropertyInfo:
    # Unknown is distinct from a driver explicitly reporting no support.
    status: str = "unknown"
    minimum: int = 0
    maximum: int = 0
    step: int = 1
    default: int = 0
    flags: int = 0

    @property
    def adjustable(self):
        return self.status == "supported" and bool(self.flags & 2) and self.minimum < self.maximum

    def normalize(self, value):
        last_step = (self.maximum - self.minimum) // self.step
        position = round((value - self.minimum) / self.step)
        return self.minimum + max(0, min(last_step, position)) * self.step


class GUID(ct.Structure):
    _fields_ = [("data1", ct.c_uint32), ("data2", ct.c_uint16),
                ("data3", ct.c_uint16), ("data4", ct.c_uint8 * 8)]

    @classmethod
    def parse(cls, value):
        return cls.from_buffer_copy(UUID(value).bytes_le)


SYSTEM_DEVICE_ENUM = GUID.parse("62BE5D10-60EB-11D0-BD3B-00A0C911CE86")
CREATE_DEVICE_ENUM = GUID.parse("29840822-5B84-11D0-BD3B-00A0C911CE86")
VIDEO_INPUT_CATEGORY = GUID.parse("860BB310-5D01-11D0-BD3B-00A0C911CE86")
BASE_FILTER = GUID.parse("56A86895-0AD4-11CE-B03A-0020AF0BA770")
CAMERA_CONTROL = GUID.parse("C6E13370-30AC-11D0-A18C-00A0C9118956")
VIDEO_PROC_AMP = GUID.parse("C6E13360-30AC-11D0-A18C-00A0C9118956")
HRESULT = ct.c_int32
LONG = ct.c_int32
ULONG = ct.c_uint32
VOID = ct.c_void_p
GUID_PTR = ct.POINTER(GUID)
VOID_PTR = ct.POINTER(VOID)
LONG_PTR = ct.POINTER(LONG)


def _invoke(pointer, slot, result_type, argument_types, *arguments):
    if not pointer:
        raise OSError("Missing COM interface")
    table = ct.cast(pointer, ct.POINTER(ct.POINTER(VOID))).contents
    method = ct.WINFUNCTYPE(result_type, VOID, *argument_types)(table[slot])
    return method(pointer, *arguments)


def _release(pointer):
    if pointer:
        _invoke(pointer, 2, ULONG, ())


def _check(result):
    if result < 0:
        raise OSError(f"DirectShow query failed (0x{result & 0xffffffff:08X})")


@contextmanager
def _com_apartment():
    # WinDLL returns HRESULTs unchanged, including failure codes we inspect.
    ole = ct.WinDLL("ole32")
    ole.CoInitializeEx.argtypes = (VOID, ULONG)
    ole.CoInitializeEx.restype = HRESULT
    ole.CoUninitialize.argtypes = ()
    ole.CoUninitialize.restype = None
    ole.CoCreateInstance.argtypes = (GUID_PTR, VOID, ULONG, GUID_PTR, VOID_PTR)
    ole.CoCreateInstance.restype = HRESULT
    result = ole.CoInitializeEx(None, 2)  # COINIT_APARTMENTTHREADED
    # An existing apartment is usable; do not uninitialize it on changed mode.
    initialized = result >= 0
    if result & 0xffffffff != 0x80010106:  # RPC_E_CHANGED_MODE
        _check(result)
    try:
        yield ole
    finally:
        if initialized:
            ole.CoUninitialize()


@contextmanager
def _device_filter(ole, camera_index):
    device_enum, moniker_enum, moniker, capture_filter = VOID(), VOID(), VOID(), VOID()
    try:
        _check(ole.CoCreateInstance(ct.byref(SYSTEM_DEVICE_ENUM), None, 1,
                                    ct.byref(CREATE_DEVICE_ENUM), ct.byref(device_enum)))
        result = _invoke(device_enum, 3, HRESULT, (GUID_PTR, VOID_PTR, ULONG),
                         ct.byref(VIDEO_INPUT_CATEGORY), ct.byref(moniker_enum), 0)
        _check(result)
        if result != 0 or not moniker_enum:
            raise OSError("No DirectShow cameras")
        for index in range(camera_index + 1):
            fetched = ULONG()
            result = _invoke(moniker_enum, 3, HRESULT, (ULONG, VOID_PTR, ct.POINTER(ULONG)),
                             1, ct.byref(moniker), ct.byref(fetched))
            _check(result)
            if result != 0 or not moniker:
                raise OSError("Camera no longer present")
            if index == camera_index:
                # IMoniker inherits IPersistStream; BindToObject is slot 8.
                _check(_invoke(moniker, 8, HRESULT, (VOID, VOID, GUID_PTR, VOID_PTR),
                               None, None, ct.byref(BASE_FILTER), ct.byref(capture_filter)))
            else:
                _release(moniker)
                moniker = VOID()
        yield capture_filter
    finally:
        for pointer in (capture_filter, moniker, moniker_enum, device_enum):
            _release(pointer)


def _read_interface_properties(capture_filter, interface_id, properties):
    interface = VOID()
    try:
        result = _invoke(capture_filter, 0, HRESULT, (GUID_PTR, VOID_PTR),
                         ct.byref(interface_id), ct.byref(interface))
        if result & 0xffffffff == 0x80004002:  # E_NOINTERFACE
            return {name: PropertyInfo("unsupported") for name in properties}
        _check(result)
        results = {}
        for name, property_id in properties.items():
            outputs = [LONG() for _ in range(5)]
            result = _invoke(interface, 3, HRESULT, (LONG, *([LONG_PTR] * 5)),
                             property_id, *(ct.byref(value) for value in outputs))
            if result == 0:
                minimum, maximum, step, default, flags = [value.value for value in outputs]
                if minimum <= maximum and (step > 0 or minimum == maximum):
                    results[name] = PropertyInfo("supported", minimum, maximum,
                                                 max(1, step), default, flags)
                else:
                    results[name] = PropertyInfo()
            elif result & 0xffffffff in (0x80070490, 0x80070492, 0x80070057):
                # E_PROP_ID_UNSUPPORTED, E_PROP_SET_UNSUPPORTED, E_INVALIDARG.
                results[name] = PropertyInfo("unsupported")
            else:
                results[name] = PropertyInfo()
        return results
    finally:
        _release(interface)


def query_camera_properties(camera_index):
    """Return driver ranges by control name, or unknown on query failure.

    Only use with CAP_DSHOW: other backends may enumerate devices differently.
    Generic failures never masquerade as proof that a property is unsupported.
    """
    if sys.platform != "win32" or camera_index < 0:
        return {}
    try:
        with _com_apartment() as ole, _device_filter(ole, camera_index) as capture_filter:
            results = {}
            for interface, properties in ((VIDEO_PROC_AMP, {"Gain": 9}),
                                          (CAMERA_CONTROL, {"Exposure": 4, "Zoom": 3, "Focus": 6})):
                try:
                    results.update(_read_interface_properties(capture_filter, interface, properties))
                except OSError:
                    results.update({name: PropertyInfo() for name in properties})
            return results
    except OSError:
        return {}
