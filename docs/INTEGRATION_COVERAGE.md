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

## Windows and Linux portability — 2026-10-07

All previous 51 active integration scenarios remain. Three application workflows
were added (54 total, all passed on Windows in 163.735 s):

- Linux wheel events through real Tk bindings: driver slider/debounce, viewport
  zoom, detected circle pixel radius and manual-guide radius. These also check
  that camera control scrolling does not zoom the viewport.
- Linux native camera flow: production device-node enumeration, explicit OpenCV
  V4L2 open and raw control units, production ioctl range parsing on the camera
  worker, slider adjustment, device switching, detection and paired export.
  Non-contiguous/high indices, unsupported controls, failed queries, malformed
  ranges and inactive automatic controls are included.
- Native query permission failure: preserve unknown ranges/numeric fallback,
  stream continuity, detection/export and clean capture shutdown.

Only OS video-node enumeration/open/close/ioctl and physical VideoCapture are
substituted in the native-query scenarios. Production capability parsing,
CameraWorker, Tk widgets, detection and export are used. On Windows the substitute
provides the Linux-only fcntl boundary and O_NONBLOCK flag; these results are not
native Linux driver or desktop validation.

The existing startup/fullscreen workflow now queries the Tk window-system state,
waits for asynchronous window-manager requests and checks title-bar preservation
and restoration of both normal and maximized states. The additional maximized
restoration assertions passed in a targeted application rerun (0.909 s).
No historical assertions were removed and no unit classes ran. Earlier historical
coverage migration gaps remain; portability work does not close those gaps.
Native Linux execution of the full suite, real camera checks and Linux frozen /
extracted-release checks remain pending the desktop VM.

## Explorer/source startup — 2026-10-07

Three additional integration workflows preserve the previous 54 scenarios:
source launch from an unrelated working directory using a real offline-created
.venv, missing dependencies with nonzero exit/readable error/log, and actual
Windows file-association launches of start.py and start.cmd. GUI launch runs the
real Tk/setup/detection/render/export smoke workflow through pythonw, without a
console or personal settings writes. Copies use spaces/Unicode paths. No launcher
or application component is mocked. Camera substitution remains inside the existing
production release smoke workflow at its hardware boundary.

The Explorer/.cmd scenario is Windows-specific and explicitly skipped on Linux;
the local-environment and dependency-failure scenarios run on both platforms.
Historical migration gaps above remain. No unit classes are added or executed.
Targeted execution: all three launch scenarios passed (4.393 s).

Combined startup follow-up: all 57 active integration scenarios passed in one run
(178.231 s), with no skipped Windows cases. New source/frozen/extracted-release
smoke checks passed. Evidence: STARTUP_VALIDATION.json. The launch fixture uses
an explicit .pth path to real installed dependencies, supporting a runner inside
a virtual environment without network installs. Linux native results remain pending.

## Direct interpreter correction — 2026-10-07

User explicitly rejected the extra CMD launcher and interpreter switching. The
three source-launch integration scenarios now verify direct explicit Python from
an unrelated directory, readable missing-dependency failure, and real Explorer
association startup while ignoring an unusable local .venv. All three passed
(3.300 s). The old windowed/CMD/automatic-selection expectations were replaced
because that behavior was rejected; image/detection/render/export assertions
remain. Test count remains 57; no unit tests run. The full preceding 57-test run
belongs to the previous launcher implementation, not this correction. Native
Linux and historical migration gaps remain pending.

## Central crosshair overlay — 2026-10-07

Added a real Tk rendering scenario for overlapping FOV and shared-center guides.
It checks the thicker white stroke above the red FOV, the red reference beyond
the marker, blink/release restoration and FOV toggling without altering detected
geometry. This scenario and four existing FOV/blink/raw-export workflows passed
(5 checks, 9.850 s). Existing assertions and historical cases are retained; the
full suite was not rerun for this small rendering change. Native Linux validation
and historical coverage migration gaps remain. No unit tests were run.

## Console visibility and interpreter errors — 2026-10-07

All 58 prior integration scenarios remain, with one new shared-console workflow
(59 total). Explorer association startup now checks the native console window is
hidden while the same associated Python completes actual Tk/setup/detection and
paired export. A second actual Python process shares a new native console with
the app; that workflow checks the console remains visible and the app completes
the same production smoke checks. Neither native console APIs nor ownership are
mocked. Missing-dependency startup checks the exact interpreter path in the UTF-8
log and terminal error, including a Unicode checkout path. The test explicitly
sets UTF-8 for the child terminal stream; the production log already uses UTF-8.

Four targeted startup workflows passed (5.030 s). Existing image, guidance,
persistence and failure assertions are retained. No historical unit classes were
run. The full prescribed runner result is recorded in CONTINUATION.md. Historical
coverage-equivalence gaps above and native Linux validation remain outstanding.
Windows Terminal pseudoconsole visibility is not covered by this native HWND check.

Prescribed combined execution: all 59 integration scenarios passed on Windows
(176.255 s), including the central-crosshair workflow. No unit tests or broad
discovery were run. This does not close the historical equivalence gaps.

## Opened-image navigation — 2026-10-08

Retain all previous 59 scenarios. Added one real file-open/detect/render workflow
using widget-generated MouseWheel and Button-4/5 events, then margin left-drag and
Reset view. It checks exact zoom changes/crop displacement, no guide movement,
unchanged raw pixels and full-image reset. The test does not assign zoom_factor
or call pan methods directly. The existing camera wheel scenario now passes on
Tk 9.0.4 as well, verifying the Windows symbolic-button number normalization
through the real camera controls, debounce and image/circle workflows.

Five targeted scenarios passed (10.642 s): new opened-image navigation, driver
wheel behavior, existing pan/zoom geometry, Control-wheel circle editing and
click-versus-drag manual picks. Tk 9's installed ZIP libraries were extracted
locally for child-process validation; no interpreter installation was altered.
The full prescribed runner result is recorded in CONTINUATION.md. Historical
coverage-equivalence gaps and native Linux validation remain outstanding.

Prescribed combined execution on Python 3.14.8/Tk 9.0.4: 59 of 60 scenarios
passed in 177.263 s. Explorer association startup failed before app launch:
os.startfile returned PermissionError [WinError 5] Access is denied for the
temporary checkout. That case remains retained and explicitly unvalidated in
this environment. All application/navigation assertions in the other 59 cases
passed. Evidence: build/gui-validation/navigation-integration.log. This is not
a full-suite pass or a claim of historical component coverage equivalence.

## Precise/native wheel delivery — 2026-10-08

Retain all 60 previous workflows and add two integration scenarios (62 total):

- Native Windows WM_MOUSEWHEEL packets through an opaque production Tk app after
  real file import/detection. Both positive/negative 30-unit high-resolution
  packets and 120-unit ordinary packets change zoom/rendered crop with video and
  sidebar focus; horizontal WM_MOUSEHWHEEL does not zoom. Raw pixels and optical
  geometry stay unchanged. This uses actual Windows/Tk routing, not event_generate,
  direct zoom calls or mouse/decoder mocks. Only owned app HWNDs receive messages.
- Actual file import/detection followed by packed TouchpadScroll events. Positive
  Y, negative Y with nonzero X, horizontal-only input, Control-scroll circle radius
  and raw export are checked through real widgets/production handlers.

Four focused workflows passed in 8.799 s, including prior ordinary wheel/margin
navigation and Linux-symbolic wheel camera/circle controls. The precise scenarios
explicitly skip when Tk lacks the event/decoder; the native scenario also skips
on Linux. They supplement rather than replace existing input assertions.
The native pre-fix reproduction delivered TouchpadScroll to the image label but
left zoom at 1.0; after the fix the same 30-unit packet changed it to 1.025.

The prescribed full-run result is recorded in CONTINUATION.md. Historical migration
gaps, native Linux desktop/camera validation and the known Explorer-launch OS
permission issue remain separate limitations; no unit tests were run.

Prescribed combined execution: 61/62 scenarios passed in 184.673 s on Windows,
including both new precise/native scenarios; no skips. Explorer association
startup again failed before application launch with os.startfile WinError 5.
No assertion was weakened or removed. The full-suite result remains a failure
because that OS-dependent workflow cannot execute here. Log:
build/gui-validation/precise-wheel-integration.log. Historical migration gaps
and native Linux validation remain outstanding.

## Rendered pixels and real touchpad session — 2026-10-08

Retain the previous 62 workflows and add one actual image-import/detect/render/
export scenario (63 total). With overlays hidden, a distinct source pixel patch
must enlarge to approximately 4x area at 2x zoom in the displayed Tk image.
It also checks unchanged raw pixels/detected geometry and opt-in diagnostic
interpreter/source/input/callback/before-after fields. No source implementation
or decoder is mocked. The actual user's two-finger trace independently verifies
vertical zoom/crop changes, ignored horizontal input, no Ctrl modifier and zero
measured-radius changes; the user confirmed "Yes, it works now" after restarting.

Three focused cases passed (5.510 s). Prescribed combined runner: 62/63 passed
(187.730 s), with the retained Explorer case failing at os.startfile WinError 5
before app launch; no skips or unit classes. Default tracing was subsequently
removed; optional bounded local tracing remains. This does not close historical
coverage-equivalence gaps or native Linux validation. Evidence:
build/gui-validation/touchpad-field-integration.log and
touchpad-session-validation.json in that folder.

## Startup and manual-guide navigation — 2026-10-09

- test_startup_only_fov_and_manual_tab_visibility: actual rendered startup
  pixels contain only the independent FOV reference; review sizing is disabled
  without detections; manual presets are ordered and draggable; returning to
  review removes presets; selected/unselected tabs have distinct colors and
  bold labels.
- test_manual_missing_guides_anchor_resize_and_follow_detected_center: actual
  image decoding/detection followed by production reference-clearing controls
  exercises each possible single-ring anchor. Missing rings have ordered sizes;
  measured rings retain their radii; missing estimates never enter selections;
  resizing survives navigation/zoom; group centers follow together; detected
  circles remain resizable/hideable; Detect and a new image clear overrides.
- Historical manual rendering/movement and detection-resume assertions remain.
  Manual rendering now explicitly selects Manual guides; resumed review expects
  no presets and then verifies their availability on the manual tab. This is the
  requested startup/tab behavior change, not a reduction in failure coverage.
- All previously recorded coverage gaps remain, including native Linux desktop
  validation and the environment's Explorer launch access-denied failure.

The partial-guide workflow additionally checks that hidden manual sliders cannot
change detected measurements; a displayed rounded value must not itself become
a manual resize. Native Windows fine-wheel routing retains its original assertions.

Final runner result: 65 scenarios in 87.898 s, 64 passed; only the existing
Explorer os.startfile WinError 5 remains. All new and retained GUI/layout and
native Windows wheel scenarios passed. Evidence:
build/gui-validation/startup-guides-final-integration.log. No skips or assertion
removals. Native Linux desktop and previously mapped equivalence gaps remain.

## Manual-session persistence — 2026-10-09

User clarified that leaving Manual guides must not hide the configured circles.
Startup and partial-guide scenarios now assert persistence after entering the
manual tab, rather than removal on return to review. Original startup-only FOV,
manual rendering, pixel sizes, center movement, tab styling and source-reset
assertions remain. Detect now retains the manual guide session and missing-role
size overrides; its production measurement reacquisition remains covered.

New test_manual_session_survives_automatic_restart_and_live_missing_edges uses
real analysis of blank and optical frames through the capture hardware fixture.
It verifies auto-only missing references stay hidden, manual entry restores all
three visibility flags, configured circles are rendered/hit-testable on review,
blank detection restart preserves radii/center, successful detection replaces
fallbacks without duplicates, a missing secondary retains its manually set size
and follows a shifted detected master, and a new source clears setup. No mocks
of detection, rendering, session state or tracking. Previously mapped gaps remain.

Validation: 66 integration scenarios, 65 passed; only the existing Explorer
WinError 5 check remains. Log: build/gui-validation/manual-session-integration.log.
The complete persistence workflow also passed after adding Ctrl+wheel resizing
of retained guides in review (2.888 s). Startup-only visibility, hidden slider
protection, FOV/blink, small-screen layout, input, camera and tracking coverage
remain. Native Linux desktop and earlier equivalence gaps remain documented.
