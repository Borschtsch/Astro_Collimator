# Development and releases

## Project layout

```text
start.py                 Source entry point
source/        Application, camera interface and image analysis
docs/                    User guides and technical documentation
scripts/                 Integration runner and Windows release builder
tests/integration/       Application workflow checks
tests/fixtures/          Optical scenes and capture substitutes
tests/legacy/            Historical coverage references
tests/images/            Local validation images; excluded from releases
```

Application imports stay inside the package. Do not add source entry wrappers
for individual modules. `start.py` and the packaged executable share the same
launcher. The application version is defined in `source/__init__.py`.

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

## Build a portable Windows release

Build on 64-bit Windows with 64-bit Python. The release contains Python, Tk,
OpenCV, NumPy and Pillow, so recipients do not need to install them.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
.venv\Scripts\python.exe scripts/build_windows.py
```

The builder checks source startup, creates the portable application, checks the
actual executable from another working directory, and writes a ZIP under `dist`.
It also extracts the ZIP into a separate folder and verifies launch with Python
removed from the process search path. It includes user documentation, build
versions and third-party dependency
notices. Personal settings, captures, tests and validation images are excluded.

A repeat build stops if `dist/AstroCollimator` already exists. Move the previous
release aside first; the builder does not delete a folder that might contain
user settings or captures. Release generation does not publish or upload files.

The application is packaged in one-folder mode using
[PyInstaller](https://pyinstaller.org/en/stable/usage.html). Keep `_internal`
beside the executable and distribute the complete ZIP. Python dependency
installation is a build-time step; application use remains fully offline.

Read `build/source-check.json`, `build/portable-check.json` and
`build/archive-check.json` for smoke results.
The smoke workflow verifies the bundled application, not physical camera drivers
or optical accuracy. Check a real camera and telescope before announcing a
release as telescope-validated.

## Technical references

- [Application design](DESIGN.md)
- [Integration coverage](INTEGRATION_COVERAGE.md)
- [Distribution plan](DISTRIBUTION_PLAN.md)
- [Continuation notes](CONTINUATION.md)
- [Detection development history](DETECTION_IMPROVEMENTS.md)
