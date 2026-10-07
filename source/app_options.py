"""Validated local telescope setup; no runtime network dependencies."""

from dataclasses import asdict, dataclass
import json
import math
import os
import sys
from pathlib import Path
import tempfile


CENTER_MARK_SHAPES = ("Unknown", "None", "Ring", "Spot", "Triangle")


@dataclass(frozen=True)
class TelescopeProfile:
    name: str = ""
    aperture_mm: float | None = None
    focal_length_mm: float | None = None
    secondary_minor_axis_mm: float | None = None
    focuser_inner_diameter_mm: float | None = None
    secondary_offset_mm: float | None = None
    center_mark_shape: str = "Unknown"
    camera_description: str = ""
    mounting_notes: str = ""

    def validate(self):
        for key in ("name", "camera_description", "mounting_notes"):
            if not isinstance(getattr(self, key), str):
                raise ValueError(f"{key.replace('_', ' ')} must be text.")
        if self.center_mark_shape not in CENTER_MARK_SHAPES:
            raise ValueError("Choose a supported center-mark shape.")
        for key in ("aperture_mm", "focal_length_mm", "secondary_minor_axis_mm",
                    "focuser_inner_diameter_mm", "secondary_offset_mm"):
            value = getattr(self, key)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{key.replace('_', ' ')} must be a finite number.")
            if value < 0 or (value == 0 and key != "secondary_offset_mm"):
                raise ValueError(f"{key.replace('_', ' ')} must be positive (offset may be zero).")
        if self.aperture_mm and self.secondary_minor_axis_mm and self.secondary_minor_axis_mm >= self.aperture_mm:
            raise ValueError("Secondary minor axis must be smaller than the primary aperture.")
        return self

    @property
    def focal_ratio(self):
        if self.aperture_mm and self.focal_length_mm:
            return self.focal_length_mm / self.aperture_mm
        return None

    @property
    def summary(self):
        title = self.name.strip() or "Telescope not configured"
        if self.aperture_mm:
            title += f" · {self.aperture_mm:g} mm"
        if self.focal_ratio:
            title += f" · f/{self.focal_ratio:g}"
        return title

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("Telescope settings must be an object.")
        fields = cls.__dataclass_fields__
        return cls(**{key: value for key, value in data.items() if key in fields}).validate()


def default_options_path():
    """Keep user settings beside the portable app or source launcher, never in a bundle."""
    directory = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    return directory / "options.json"


class OptionsStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else default_options_path()

    def load(self):
        if not self.path.exists():
            return TelescopeProfile()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Cannot read telescope options: {error}") from error
        if (not isinstance(data, dict) or type(data.get("schema_version")) is not int or
                data.get("schema_version") != 1):
            raise ValueError("Unsupported telescope-options format.")
        return TelescopeProfile.from_dict(data.get("telescope"))

    def save(self, profile):
        profile.validate()
        body = json.dumps({"schema_version": 1, "telescope": asdict(profile)},
                          ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                             dir=self.path.parent, prefix=".options-", suffix=".tmp",
                                             delete=False) as stream:
                temporary_path = Path(stream.name)
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
