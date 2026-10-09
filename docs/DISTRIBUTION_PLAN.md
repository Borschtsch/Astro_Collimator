# Distribution plan — 2026-10-07

Prepare Astro Collimator for sharing with Newtonian imagers. Keep runtime offline
and perform no Git operations. Preserve the existing integration scenarios and
historical coverage references; this change does not complete coverage migration.

- One source entry: start.py. Move implementation into source/ with
  package-relative imports. Keep settings at the source root, or next to the
  portable executable, independent of the working directory.
- Move actual app workflows into tests/integration, reusable camera/image
  fixtures into tests/fixtures, and historical component cases into tests/legacy.
  Update mocks/imports and TestImages paths without weakening assertions.
- README is a short astronomy-focused introduction and documentation index.
  Put installation, Newtonian workflow and controls into dedicated docs pages;
  put architecture, tests and release building into developer documentation.
- Build a Windows portable folder and ZIP using PyInstaller; one visible EXE
  with bundled dependencies beneath _internal. Exclude personal options, tests,
  sample photos, developer history and local environment. Include user docs and
  dependency notices. Do not publish or upload the release.
- Validate relocated app integration scenarios, source launch from another
  working directory, settings-path behavior, a frozen launch and real image
  detection/export through a diagnostic application workflow.
- Preserve UTF-8 BOM state and line endings. Document commands and limitations.

Completed: source and tests reorganized, user/developer documentation separated,
51 integration scenarios passed, and source/frozen/extracted-archive workflows
verified. See CONTINUATION.md and DISTRIBUTION_VALIDATION.json for results.

## Image fixture relocation — 2026-10-07

User moved the local image set into tests/images. Update active integration and
historical reference paths through one shared fixture directory constant, retain
all image assertions, and run the native-photo app integration workflow. Update
current layout documentation; earlier paths in historical checkpoints remain history.

## Package naming — 2026-10-07

User requested the application package be named source. Rename the package,
update launcher/imports/mock targets/package discovery/build references and
current documentation, then validate source and portable launches and the
existing integration workflows. Preserve the product/distribution name Astro
Collimator, user settings, historical assertions and previous release artifacts.

Package rename completed: 51 integration scenarios passed, source startup and
the existing portable release passed smoke checks. Existing release files were
preserved; future builds import source. See CONTINUATION.md for details.

## Cross-platform follow-up — 2026-10-07

The shared application now uses native Windows/Linux window/input and capture
paths. Detailed plan, implemented behavior and native VM handoff are in
PLATFORM_SUPPORT.md. Shared release assembly is scripts/build_portable.py;
build_windows.py and build_linux.py invoke it on their respective native OS.
Outputs now live in dist/<platform>-<architecture> and build checks in matching
build subfolders. The original flat Windows release is preserved. Linux release
assembly must run in the Linux desktop VM; Windows builds cannot verify Linux.
