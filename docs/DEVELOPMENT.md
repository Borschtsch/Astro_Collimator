# Development and releases

## Project layout

```text
start.py                 Source entry point
source/                  Application, camera interface and image analysis
docs/                    User guides and technical documentation
scripts/                 Integration runner, native release builders and Linux validation
tests/integration/       Application workflow checks
tests/fixtures/          Optical scenes and capture substitutes
tests/legacy/            Historical coverage references
tests/images/            Local validation images; excluded from releases
```

Application imports stay inside the package. Do not add source entry wrappers
for individual modules. `start.py` and the packaged executable share the same
launcher. Startup runs directly in the interpreter selected by the caller or
Windows file association. The startup wrapper reports failures and hides an app-only Windows console; it
does not spawn another Python process or select an environment. CLI arguments and frozen
launches remain supported. The application version is defined in `source/__init__.py`.

## Validation

Run the explicit integration suite:

```powershell
python -B scripts/test_integration.py
```

Use integration tests only. Preserve the previous behavior and failure-case
coverage; [the coverage map](INTEGRATION_COVERAGE.md) records remaining migration
work. Historical component tests are retained but excluded from the runner.

The release smoke workflow checks actual Tk startup, settings persistence,
Unicode image import, detection, guidance, rendering and paired PNG/JSON export.
It substitutes only unavailable camera hardware and uses temporary settings.
It does not change the user's `options.json` or require a connected camera.

```powershell
python -B start.py --smoke-test --report build/source-check.json
```

## Build portable releases

Build on the target operating system with native 64-bit Python. Windows builds
produce ZIPs; Linux builds produce tar archives with executable permissions and
symbolic links preserved. The release contains Python, Tk,
OpenCV, NumPy and Pillow, so recipients do not need to install them.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
.venv\Scripts\python.exe scripts/build_windows.py
```

On Linux, install the dependencies described in [Getting started](GETTING_STARTED.md)
and the build utilities `binutils` (with `ldd` supplied by the system C library).
Then run:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-build.txt
.venv/bin/python scripts/build_linux.py
```

Both wrappers use scripts/build_portable.py. Windows x64 and Linux x64/arm64 are
accepted build targets; each must be validated natively before distributing it.
Build Linux releases on the oldest supported distribution because PyInstaller
does not bundle glibc. The native build host and libc version are recorded in
build-info.json. No universal Linux compatibility is claimed.

The builder checks source startup, creates the portable application, checks the
actual executable from another working directory, and writes an archive under
`dist/<platform>-<architecture>`.
It extracts the archive into a separate folder with spaces and a Unicode name,
then verifies launch without build-environment Python paths. The Windows child
PATH contains only System32; the Linux child retains system binary paths.
It includes user documentation, build versions and third-party dependency notices. Personal settings, captures, tests and validation images are excluded.

A repeat build stops if `dist/<platform>-<architecture>/AstroCollimator` already exists.
Use `--output-dir <folder>` for a separate output location. Move the previous
release aside first; the builder does not delete a folder that might contain
user settings or captures. Release generation does not publish or upload files.

The application is packaged in one-folder mode using
[PyInstaller](https://pyinstaller.org/en/stable/usage.html). Keep `_internal`
beside the executable and distribute the complete archive. Python dependency
installation is a build-time step; application use remains fully offline.

Read `build/<platform>-<architecture>/source-check.json`, `portable-check.json`
and `archive-check.json` for smoke results.
The smoke workflow verifies the bundled application, not physical camera drivers
or optical accuracy. Check a real camera and telescope before announcing a
release as telescope-validated.

## Native Linux VM validation

Use the VM desktop terminal, or SSH attached to that same desktop display:

```bash
.venv/bin/python scripts/validate_linux.py
# Add --build after installing requirements-build.txt to validate a Linux release.
```

This runs the entire explicit integration suite and the source smoke workflow.
Results, host details and logs are written to build/linux-validation/. Physical
camera checks remain a separate desktop task. See [platform support](PLATFORM_SUPPORT.md)
for SSH display setup and the camera checklist.

## Technical references

- [Windows and Linux support](PLATFORM_SUPPORT.md)
- [Application design](DESIGN.md)
- [Integration coverage](INTEGRATION_COVERAGE.md)
- [Distribution plan](DISTRIBUTION_PLAN.md)
- [Continuation notes](CONTINUATION.md)
- [Detection development history](DETECTION_IMPROVEMENTS.md)

## Windows source console and error reports

Before GUI imports, the bootstrap checks the processes attached to the native
console. It hides the window only when every attached process is this app or
`py.exe`. A shared shell/Python console, failed ownership query or oversized
process list is left untouched. The associated interpreter, streams and process
are preserved. Version/CLI invocations do not hide the console; the release
smoke workflow exercises the GUI console policy. Frozen windowed builds already
have no console.

Startup errors include `sys.executable` in the message and UTF-8 log; the log also
includes `sys.version` and the traceback. The project log falls back to the
system temporary folder when the project cannot be written. Smoke JSON reports
already record `python_executable` with any workflow failure.

This uses [GetConsoleProcessList](https://learn.microsoft.com/en-us/windows/console/getconsoleprocesslist),
[GetConsoleWindow](https://learn.microsoft.com/en-us/windows/console/getconsolewindow)
and [ShowWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-showwindow).
Windows allocates a console before source code executes, so a brief startup flash
is possible. A Windows Terminal pseudoconsole does not expose its visible terminal
window through GetConsoleWindow; hiding that window is not claimed or validated.
Native Linux GUI/release checks remain pending the desktop VM.

## Fine-resolution wheel input

The shared wheel binder handles MouseWheel/X11 button events and, when Tk exposes
its decoder, TouchpadScroll. Tk uses the latter for touchpads and high-resolution
mice; listening only for MouseWheel misses those native inputs. The binder uses
::tk::PreciseScrollDeltas to decode signed vertical movement separately from the
horizontal component. Ordinary events keep their existing step behavior. Windows
precise zoom uses the vertical delta / 120, giving immediate smaller increments
for packets below one traditional wheel step. Pure horizontal input does not zoom.
Control-wheel radius editing and camera/manual guide controls share the binder.

The native Windows integration scenario opens/detects a real image and sends
WM_MOUSEWHEEL packets to owned app HWNDs with both video and sidebar focus. It
checks positive/negative 30- and 120-unit packets through actual Windows/Tk routing,
rendered crop changes and untouched raw/guide geometry. Native routing needs a
briefly visible opaque window; an alpha-zero test window fails Windows hit testing.
No system mouse position is changed and no messages are sent to other apps.
A second app workflow checks packed two-axis TouchpadScroll events, horizontal
rejection, Control-wheel sizing and raw export. Older Tk without precise events
explicitly skips these additional scenarios; ordinary-wheel coverage remains.

References: [Tk high-resolution scroll specification](https://core.tcl-lang.org/tips/doc/main/tip/684.md)
and [Tk Windows mouse compatibility issue](https://core.tcl-lang.org/tk/tktview/7a17cfd1b55980aa2bfbaf521600d95b12551432).

## Optional local input diagnosis

Set ASTRO_COLLIMATOR_INPUT_LOG to a local JSON file path before starting the app
to inspect difficult input-routing issues. Logging is disabled by default. The
file records interpreter, loaded source path, Tk version, scroll axes/modifiers,
receiving widget/callback and before/after zoom/guide radii. It keeps only the last
40 events and debounces writes by 100 ms; it captures no images or network data.
Writes failing due to permissions do not interrupt normal input. Source startup
automatically enabled this trace briefly for the touchpad field investigation,
but that temporary default was removed after the user confirmed the fix.

The additional file-open integration scenario checks actual displayed Tk pixels:
a distinct source color patch grows to approximately four times its visible area
at 2x zoom, while raw pixels and detected radii remain unchanged. It also checks
the opt-in diagnostic file and paired raw export. This supplements metadata-only
zoom checks and preserves earlier navigation assertions.
