# Integration coverage contract — 2026-10-06

User decision: **integration tests only, with the same behavioral and failure-case
coverage as before**. Test count is not the acceptance criterion. Preserve the
historical files as the coverage reference; do not execute their unit classes.
No commits or runtime network access.

Run `C:\Python313\python.exe -B scripts/test_integration.py`. This explicitly selects
43 existing app workflows and the new `WorkflowTests` scenarios. It excludes
`WorkerTests`, `FrameTests`, `OptionsTests`, `RangeTests`, `NativeQueryTests`,
`DetectionTests`, `LocalImageTests`, `SharedCircleGuideTests`, `AlignmentTests`
and `TrackingTests`. Image/capture fixtures live in tests/fixtures and contain no test classes. Do not use broad test discovery.

New workflows use actual Tk, image import, the production analysis worker,
detection/tracking/guidance, rendering, setup persistence and raw PNG/JSON export.
Camera capture substitutes are at the hardware boundary; the atomic-save failure
substitute is at the filesystem boundary. Existing GUI race/error scenarios also
use controlled delays or event delivery to exercise application handling.

## Mapping and migration status

The previous baseline contained 123 cases: 43 GUI workflows and 80 component
cases. One native-photo case was skipped because `lox/image (1).jpg` is absent.
The map below distinguishes existing integration coverage from remaining
equivalence work. **The migration is not yet certified to have identical
coverage.** Keep every listed gap as required work; do not silently drop it or
declare equivalence because the integration run passes.

| Historical coverage | App-level replacement / evidence | Remaining equivalence work |
| --- | --- | --- |
| `GuiTests` (43) | All 43 explicitly retained in the runner: camera selection/disconnect/recovery, controls, setup, rendering, compact stable layouts, picks, group movement, radius edits, pan/zoom/reset/blink/FOV, source tokens, one-worker scheduling, tracking pauses/manual recovery and PNG/JSON pairing | None removed; new averaging/local-tracking workflows supplement them |
| `OptionsTests` (6) | Setup save/cancel, startup loading/corrupt reporting, optional mark, Unicode raw export; new invalid-edit/atomic failure, legacy resave and future-schema startup workflows | Add startup type-corruption cases (numeric string, boolean physical value, non-text name), invalid mark shape and round-trip setup with every dimension/mark shape; UI strings alone do not cover malformed saved JSON |
| `WorkerTests` (6) | GUI startup/refresh, failed open/disconnect, camera switching/debounce, supported ranges, invalid controls and thread-owning capture substitute | Add sparse camera enumeration plus probe release assertions, repeated switching/session control rejection, real rejected/clamped/throwing driver responses through UI, blocked-read shutdown, query-before-open ordering |
| `FrameTests` (2) | Actual rendered images, source-preserving reset/pan/zoom and clean exports | Extend portrait/landscape/odd-dimension colored-frame render comparisons and center-crop checks at multiple zoom levels |
| `RangeTests` (2) | GUI driver ranges, step scroll, auto-only/unsupported/unknown controls | Add out-of-range requests, non-aligned upper bound and fixed-value driver range through actual camera controls |
| `NativeQueryTests` (3) | Current GUI capability substitutes cover presentation, not native COM calls | Required: fake device at the DirectShow/COM boundary through real query -> camera worker -> UI; verify ctypes ranges/failure codes, missing-interface isolation, enumeration order and all release paths. Actual telescope hardware validation remains separate |
| `DetectionTests` (23) | New PNG import -> Detect -> render -> export table covers raw-scale pupil/mark identity, independent raw centers, unique assignments, blank/noise/soft/dim/clipped/shadow captures. Existing mouse/render workflows cover transforms and manual geometry | Add tight duplicate rims, triangle/oval scenes, moderate blur/noise, lone primary/shadow, short arcs, severe stretch, straight lines/faint rims and spider occlusion with their historical numerical/negative assertions. Add invalid image files and collinear/too-small manual picks. Internal-only invalid argument guards must get an explicit integration path or remain reported as gaps |
| `LocalImageTests` (12) | New native-photo import/render/export workflow visits all 14 available photos; checks historical role-radius bounds, missing secondary/focuser, soft focuser and ghost rejection | Add historical raw-center/support/message assertions, unmarked pupil identity and scaled merged-rim case. Missing `image (1).jpg` remains an explicit unavailable fixture |
| `SharedCircleGuideTests` (5) | Every imported scene/native photo asserts round shared-center guides; GUI group drag/reset/master replacement/raw export assertions | Extend oval raw-evidence preservation, fallback-largest master with unassigned boundaries, empty master and invalid recenter boundary cases |
| `AlignmentTests` (13) | Existing GUI tests check missing pupil/optional mark, capture advice, guide-only offsets and held-manual deferral; new quality workflow checks exported capture advice | Required: actual image/pick workflows for camera seating, secondary shape/placement, secondary aim with/without mark, primary pupil direction, verification/star-test wording, soft pupil, partial/clipped evidence and guides lacking fresh measurements. Assert stages, directions and exported raw metrics, not only nonempty text |
| `TrackingTests` (8) | Existing live manual loss/master motion/reacquisition, radius retention and offset tests; new full-search loss/recovery asserts unique IDs and matching pixels | Extend pupil-versus-mark recovery, repeated recovered/lost cycles, soft/distant/low-coverage/poor-fit rejection, one-point mark recovery, cross-role theft rejection and complete loss retaining only manual references |

## New live-detection coverage

- Actual noisy capture -> full discovery -> local updates -> three-frame steady
  averaging -> exact exported image/metadata and measured noise reduction.
- Editing/tracking disable clears accumulation; preview/session behavior stays
  covered by retained GUI workflows.
- Actual complete image -> lost edges -> full fallback -> shifted latest image
  -> recovered roles -> local tracking, with a one-frame capture queue and exact
  analyzed/exported pixels.
- Maximized decorated startup and optional F11/Escape fullscreen retain source
  and view. This supersedes the former fullscreen-at-start assertion.

Further required checks: localized mark/pupil motion and focus/brightness changes,
120 ms expiration and low-FPS gaps through paced capture, source/resolution changes
with pending averaged work, periodic missing/manual reacquisition, scaled detail
tracking and native-photo timing. Verify absence of temporal ghost edges and never
substitute shared display centers for independently measured raw positions.

## Completion gate

For each remaining historical case, name the integration scenario and preserve
its meaningful positive/negative assertions. Record the command and results,
including unavailable fixtures and hardware limits. Do not remove historical
tests or weaken their expected behavior without an explicit product decision.
Only claim equivalent coverage after the gaps above have been closed or an
explicit scope change has been agreed with the user.

Recorded execution: 43 retained GUI scenarios passed in the combined run; after
correcting test render cadence, all 8 new workflow methods passed in a targeted
rerun (29.282 s). No historical unit class ran. The larger-render averaging check
initially observed two recent samples, not three; its revised 900x700 test window
exercises three samples within the unchanged 120 ms bound. See CONTINUATION.md
for the run history. This evidence does not close the equivalence gaps above.

## Distribution refactor — 2026-10-07

The runner is now scripts/test_integration.py. All 51 active scenarios are in
tests/integration (43 GuiTests plus 8 WorkflowTests); the 80 historical component
cases are preserved in tests/legacy. Reusable fixtures are in tests/fixtures.
No assertion was removed for the layout change. Local photos are in TestImages;
the old lox references above describe the earlier baseline. All 51 relocated
integration scenarios passed in one run (156.586 s). Historical migration gaps
remain; reorganizing files does not certify equivalent component coverage.

Additional release integration checks passed through start.py, the frozen Windows
executable and the extracted ZIP with Python absent from the child PATH. These
checks use the actual app for startup, persistence, Unicode image import,
recognition, guidance, Tk rendering and paired PNG/JSON export. They substitute
only unavailable camera hardware and do not write personal settings.

Image relocation follow-up (2026-10-07): native fixtures now live in tests/images.
All active/historical image references use TEST_IMAGES from tests/fixtures/images.py.
The native-photo application integration workflow passed all 14 images (9.414 s).
No assertions changed and no historical unit tests were executed.

Package naming follow-up (2026-10-07): astro_collimator was renamed to source.
Imports/mock targets and build metadata were adapted without changing assertions.
All 51 integration scenarios passed (160.750 s); the 80 legacy references remain.
Source and existing portable-release smoke workflows passed. No unit tests ran.
