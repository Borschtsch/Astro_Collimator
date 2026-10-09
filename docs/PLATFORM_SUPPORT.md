# Windows and Linux support

## Implementation plan — 2026-10-07

Keep one application in source/ and one entry point, start.py. Runtime remains
fully offline; no commits or Git operations.

- Use platform-aware decorated maximization and preserve the window state around
  optional fullscreen. Support Linux mouse-wheel button events throughout the UI.
- Use explicit DirectShow capture on Windows and V4L2 capture on Linux. Discover
  Linux video nodes, including non-contiguous indices. Query gain, exposure, zoom
  and focus ranges through the native API without changing camera values.
- Share portable-release assembly and smoke checks; build Windows ZIPs on Windows
  and Linux tar archives on Linux, preserving executable permissions.
- Document Linux dependencies, camera access, source launch, release creation and
  native VM validation. Keep the README brief.
- Preserve all existing integration scenarios. Add complete UI/camera workflows
  for Linux input and native camera capability failures at the hardware boundary.

Windows validation can run here. Linux GUI, window-manager behavior, physical
V4L2 cameras and Linux frozen releases require the Linux VM; do not claim they
have passed until native results are recorded. Remaining historical integration
coverage migration gaps remain recorded in INTEGRATION_COVERAGE.md.

## Implemented

- start.py and source/ are shared. Settings still live beside the source launcher
  or portable executable; Windows settings are not moved or overwritten.
- Tk maximizes a decorated window through the desktop's native mechanism. F11
  and Escape preserve the prior maximized/normal state. X11 applies these requests
  asynchronously; a desktop window manager is required to verify them.
- MouseWheel and X11 Button-4/5 work on the viewport, camera controls, manual
  guides and pixel-radius controls. Drag/pan, hold-to-blink and reset remain shared.
- Linux enumerates numeric /dev/video* nodes, including indices above 9. Capture
  uses the same device path and V4L2 backend as the capability query. OpenCV range
  normalization is disabled so sliders and get/set share native driver units.
- V4L2 integer ranges are read with VIDIOC_QUERYCTRL. Missing/disabled controls
  are unavailable; query/permission errors and malformed ranges stay unknown.
  Read-only, busy, inactive and automatically changing controls cannot be edited.
  Queries never change gain, exposure, zoom, focus or automatic modes. Vendor SDK
  cameras and non-V4L2 camera pipelines are outside this capture interface.
- scripts/build_portable.py performs common assembly and real application smoke
  checks. build_windows.py and build_linux.py are native entry points. Linux tar
  archives preserve executable bits and PyInstaller symbolic links. Outputs are
  separate under dist/windows-x64 and dist/linux-<architecture>. Existing bundles
  are never overwritten; --output-dir allows a separate build destination.
- scripts/validate_linux.py records environment, full integration logs and source
  smoke results. With --build it also runs the native Linux release checks.

## Linux VM handoff

Use an actual Linux VM with a desktop. Native Linux results are still pending;
no WSL installation is needed. The VM needs Python 3.11+ with Tk, dependencies
from requirements.txt, and a writable project copy. See GETTING_STARTED.md.
Do not transfer .venv, .build-venv, build or dist from Windows: environments and
binary releases are specific to their OS. Include source, scripts, docs, tests
(including tests/images), start.py and the requirements files. Leave personal
options.json out if the VM should use separate telescope settings.

From a terminal in the VM desktop:

```bash
.venv/bin/python scripts/validate_linux.py
.venv/bin/python start.py
# After installing requirements-build.txt and binutils:
.venv/bin/python scripts/validate_linux.py --build
```

Reports are in build/linux-validation/results.json and the adjacent logs.
Portable checks are in build/linux-<architecture>/. A native release must pass
source, frozen-executable and relocated-archive checks before distribution.
Build on the oldest intended Linux baseline and test each supported architecture;
a successful x64 VM check does not validate arm64 or every distribution.

For SSH work, supply the VM host/port and user plus an available authentication
method; no password needs to be written into project files. The VM desktop user
must be logged in. Record DISPLAY and XAUTHORITY in that desktop terminal, then
use their actual values in the SSH session to reach the same desktop. XWayland
also exposes DISPLAY. A plain SSH shell without display authorization cannot
run Tk GUI integration checks. SSH X11 forwarding is an alternative, but then
window-manager behavior belongs to the forwarded desktop. Native VM desktop
validation is preferred. Keep display access restricted to the logged-in user;
there is no need to enable unrestricted xhost access.

Manually verify title bar/window controls, F11/Escape, wheel zoom, drag/pan,
radius editing and hold-right blink on the VM's normal desktop. Pass the USB
camera through to the guest, check the desktop user's video-device access, then
verify scan/select, supported slider ranges, exposure/focus behavior, live
tracking on/off, stream continuity, mirror movement and saved capture. Automated
checks substitute cameras and do not certify actual USB passthrough or drivers.

## Technical references

- [Tk window management](https://www.tcl-lang.org/man/tcl8.6/TkCmd/wm.htm)
- [V4L2 control queries and flags](https://docs.kernel.org/userspace-api/media/v4l/vidioc-queryctrl.html)
- [V4L2 camera control units](https://docs.kernel.org/userspace-api/media/v4l/ext-ctrls-camera.html)
- [OpenCV V4L2 capture implementation](https://github.com/opencv/opencv/blob/4.x/modules/videoio/src/cap_v4l.cpp)
- [PyInstaller native builds and Linux compatibility](https://pyinstaller.org/en/stable/usage.html)
- [Ubuntu Tk](https://packages.ubuntu.com/noble/python3-tk),
  [OpenGL](https://packages.ubuntu.com/noble/libgl1) and
  [GLib](https://packages.ubuntu.com/noble/libglib2.0-0t64) packages

## Recorded validation — 2026-10-07

Windows: all 54 integration scenarios passed (163.735 s). Added maximized-state
restoration assertions passed in a targeted UI rerun (0.909 s). Source, rebuilt
Windows executable and relocated ZIP smoke checks passed through the shared
builder. The new portable archive is
`dist/windows-x64/AstroCollimator-0.1.0-windows-x64.zip`.
The previous flat dist/AstroCollimator release remains untouched.
See PLATFORM_VALIDATION.json for the archive checksum and smoke evidence.

Linux: implementation and three boundary-based integration workflows are ready;
native desktop, camera and Linux release checks have not run. They require the
actual graphical Linux VM. No unit tests or Git operations were performed.
