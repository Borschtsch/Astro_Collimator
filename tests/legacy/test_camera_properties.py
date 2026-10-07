import ctypes as ct
import sys
import unittest

from source.camera_properties import (
    CAMERA_CONTROL, GUID_PTR, HRESULT, LONG, LONG_PTR, ULONG, VOID, VOID_PTR,
    PropertyInfo, _device_filter, _read_interface_properties,
)


class RangeTests(unittest.TestCase):
    def test_steps_are_anchored_to_minimum_and_clamped(self):
        info = PropertyInfo("supported", 3, 19, 4, 7, 2)
        self.assertTrue(info.adjustable)
        for requested, expected in ((-100, 3), (4, 3), (8, 7), (14, 15), (100, 19)):
            self.assertEqual(info.normalize(requested), expected)
        # A non-aligned upper bound must not produce an invalid last step.
        self.assertEqual(PropertyInfo("supported", 3, 20, 4, 7, 2).normalize(20), 19)

    def test_auto_only_fixed_unsupported_and_unknown_are_not_adjustable(self):
        for info in (PropertyInfo(), PropertyInfo("unsupported"),
                     PropertyInfo("supported", 0, 100, 1, 50, 1),
                     PropertyInfo("supported", 7, 7, 1, 7, 2)):
            self.assertFalse(info.adjustable)


class FakeCom:
    """Real ctypes COM-shaped vtables for testing pointer sizes and calls."""

    def __init__(self, slots):
        self.callbacks = []
        self.table = (VOID * (max(slots) + 1))()
        for slot, (restype, argtypes, callback) in slots.items():
            function = ct.WINFUNCTYPE(restype, VOID, *argtypes)(callback)
            self.callbacks.append(function)
            self.table[slot] = ct.cast(function, VOID)
        self.table_pointer = ct.cast(self.table, ct.POINTER(VOID))
        self.instance = ct.pointer(self.table_pointer)
        self.pointer = ct.cast(self.instance, VOID)


@unittest.skipUnless(sys.platform == "win32", "Windows COM ABI")
class NativeQueryTests(unittest.TestCase):
    def test_queries_marshal_ranges_and_distinguish_failures(self):
        released = []

        def get_range(this, prop, minimum, maximum, step, default, flags):
            if prop == 3:
                return ct.c_int32(0x80070490).value
            if prop == 99:
                return ct.c_int32(0x80004005).value  # E_FAIL is unknown.
            values = (-13, -1, 1, -6, 3) if prop == 4 else (0, 255, 5, 125, 1)
            for pointer, value in zip((minimum, maximum, step, default, flags), values):
                pointer[0] = value
            return 0

        control = FakeCom({
            2: (ULONG, (), lambda this: released.append("control") or 0),
            3: (HRESULT, (LONG, LONG_PTR, LONG_PTR, LONG_PTR, LONG_PTR, LONG_PTR), get_range),
        })

        def query(this, iid, pointer):
            pointer[0] = control.pointer
            return 0

        capture = FakeCom({0: (HRESULT, (GUID_PTR, VOID_PTR), query)})
        result = _read_interface_properties(capture.pointer, CAMERA_CONTROL,
                                            {"Exposure": 4, "Zoom": 3, "Focus": 6, "Other": 99})
        self.assertEqual(result["Exposure"], PropertyInfo("supported", -13, -1, 1, -6, 3))
        self.assertEqual(result["Zoom"].status, "unsupported")
        self.assertFalse(result["Focus"].adjustable)
        self.assertEqual(result["Other"].status, "unknown")
        self.assertEqual(released, ["control"])

    def test_missing_interface_disables_only_its_controls(self):
        capture = FakeCom({0: (HRESULT, (GUID_PTR, VOID_PTR),
                               lambda *args: ct.c_int32(0x80004002).value)})
        result = _read_interface_properties(capture.pointer, CAMERA_CONTROL, {"Zoom": 3, "Focus": 6})
        self.assertEqual([info.status for info in result.values()], ["unsupported", "unsupported"])

    def test_moniker_order_and_cleanup_on_success_and_missing_device(self):
        for camera_index in (1, 3):
            with self.subTest(camera_index=camera_index):
                released = []
                bound = []

                def release(name):
                    return lambda this: released.append(name) or 0

                capture = FakeCom({2: (ULONG, (), release("capture"))})
                monikers = []
                for index in range(2):
                    def bind(this, context, left, iid, output, index=index):
                        bound.append(index)
                        output[0] = capture.pointer
                        return 0
                    monikers.append(FakeCom({
                        2: (ULONG, (), release(f"moniker{index}")),
                        8: (HRESULT, (VOID, VOID, GUID_PTR, VOID_PTR), bind),
                    }))
                position = 0

                def next_moniker(this, count, output, fetched):
                    nonlocal position
                    if position >= len(monikers):
                        return 1
                    output[0] = monikers[position].pointer
                    fetched[0] = 1
                    position += 1
                    return 0

                enumerator = FakeCom({
                    2: (ULONG, (), release("enumerator")),
                    3: (HRESULT, (ULONG, VOID_PTR, ct.POINTER(ULONG)), next_moniker),
                })

                def create_class_enum(this, category, output, flags):
                    output[0] = enumerator.pointer
                    return 0

                devices = FakeCom({
                    2: (ULONG, (), release("devices")),
                    3: (HRESULT, (GUID_PTR, VOID_PTR, ULONG), create_class_enum),
                })

                class FakeOle:
                    def CoCreateInstance(self, clsid, outer, context, iid, output):
                        ct.cast(output, VOID_PTR)[0] = devices.pointer
                        return 0

                if camera_index == 1:
                    with _device_filter(FakeOle(), camera_index) as result:
                        self.assertEqual(result.value, capture.pointer.value)
                    self.assertEqual(bound, [1])
                    self.assertIn("capture", released)
                else:
                    with self.assertRaises(OSError):
                        with _device_filter(FakeOle(), camera_index):
                            pass
                    self.assertEqual(bound, [])
                self.assertEqual(released.count("moniker0"), 1)
                self.assertEqual(released.count("moniker1"), 1)
                self.assertEqual(released.count("enumerator"), 1)
                self.assertEqual(released.count("devices"), 1)


if __name__ == "__main__":
    unittest.main()
