from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from source.app_options import OptionsStore, TelescopeProfile


class OptionsTests(unittest.TestCase):
    def test_absent_primary_mark_is_saved_and_legacy_unknown_is_optional(self):
        from source.feature_detection import required_features
        profile = TelescopeProfile(center_mark_shape="None")
        self.store.save(profile)
        self.assertEqual(self.store.load(), profile)
        self.assertNotIn("Center mark", required_features(profile.center_mark_shape))
        self.assertNotIn("Center mark", required_features(TelescopeProfile().center_mark_shape))
        self.assertIn("Camera pupil", required_features("None"))
        self.assertIn("Center mark", required_features("Ring"))

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = OptionsStore(Path(directory.name) / "options.json")

    def test_unknown_values_stay_unknown_and_profile_round_trips(self):
        self.assertEqual(self.store.load(), TelescopeProfile())
        profile = TelescopeProfile(name="Newtonian é", aperture_mm=130, focal_length_mm=650,
                                   secondary_minor_axis_mm=45, center_mark_shape="Triangle")
        self.store.save(profile)
        self.assertEqual(self.store.load(), profile)
        self.assertEqual(profile.focal_ratio, 5)
        self.assertIsNone(self.store.load().secondary_offset_mm)
        self.assertFalse(self.store.path.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(list(self.store.path.parent.glob(".options-*.tmp")), [])

    def test_invalid_physical_values_are_rejected_without_overwriting(self):
        profile = TelescopeProfile(aperture_mm=130)
        self.store.save(profile)
        before = self.store.path.read_bytes()
        for invalid in (replace(profile, aperture_mm=0), replace(profile, focal_length_mm=float("nan")),
                        replace(profile, secondary_minor_axis_mm=140), replace(profile, secondary_offset_mm=-1),
                        replace(profile, center_mark_shape="Square"), replace(profile, name=12),
                        replace(profile, aperture_mm=True)):
            with self.assertRaises(ValueError):
                self.store.save(invalid)
            self.assertEqual(self.store.path.read_bytes(), before)

    def test_legacy_eccentricity_is_ignored_and_removed_on_save(self):
        self.store.path.write_bytes(b'{"schema_version":1,"telescope":{"name":"Older scope","max_eccentricity":0.85}}')
        profile = self.store.load()
        self.assertEqual(profile.name, "Older scope")
        self.assertFalse(hasattr(profile, "max_eccentricity"))
        self.store.save(profile)
        self.assertNotIn(b'max_eccentricity', self.store.path.read_bytes())

    def test_failed_atomic_replace_keeps_original_and_cleans_temporary_file(self):
        original = TelescopeProfile(name="Original")
        self.store.save(original)
        with patch("source.app_options.os.replace", side_effect=PermissionError("Locked file")):
            with self.assertRaises(PermissionError):
                self.store.save(TelescopeProfile(name="New"))
        self.assertEqual(self.store.load(), original)
        self.assertEqual(list(self.store.path.parent.glob(".options-*.tmp")), [])

    def test_corrupt_and_future_formats_are_reported_and_preserved(self):
        for text in ('{bad', '{"schema_version":2,"telescope":{}}',
                     '{"schema_version":1,"telescope":{"aperture_mm":"130"}}'):
            self.store.path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                self.store.load()
            self.assertEqual(self.store.path.read_text(encoding="utf-8"), text)


if __name__ == "__main__":
    unittest.main()
