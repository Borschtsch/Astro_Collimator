# Integration coverage contract — 2026-10-06

User decision: **integration tests only, with the same behavioral and failure-case
coverage as before**. Test count is not the acceptance criterion. Preserve the
historical files as the coverage reference; do not execute their unit classes.
No commits or runtime internet access. Optional phone input uses the local network only.

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

## Literal Windows cache path prevention — 2026-10-09

New test_source_startup_repairs_windows_paths_without_literal_cache_folders runs
the real source launcher/smoke workflow from an isolated checkout. Its first
child omits Windows path variables and supplies unexpanded ProgramData/WINDIR;
startup must repair paths before native Tk/shell initialization. A second child
supplies valid caller ProgramData/ALLUSERSPROFILE paths, which must be preserved.
Both must complete actual rendering/export and leave no %SystemDrive% folder in
the working directory or project. Existing Explorer and other startup assertions
remain intact. Native Linux is unaffected by the Windows-only repair and remains
subject to the previous VM validation gap. Explorer WinError 5 persists separately.

Full validation: 67 integration scenarios in 84.525 s, 66 passed; unchanged
Explorer WinError 5 is the only error. The literal cache folder remains absent
after the shell check and entire suite. Evidence:
build/gui-validation/windows-cache-path-integration.log. Existing assertions
and historical tests remain; no unit tests or broad discovery were run.

## Spider vanes and crosshair controls — 2026-10-09

| Workflow | Production behavior and failure coverage |
| --- | --- |
| SpiderTests.test_auto_alignment_and_shared_controls | PNG loading, actual full edge/vane analysis, centered two/three/four vanes at several angles, correct automatic blade shape, explicit alignment, unchanged circle assignments/raw pixels, shared manual switch, separate normalized angles, invalid NaN input, complete controls on both tabs at 1280x720/1024x768, raw capture and JSON metadata |
| SpiderTests.test_uncertain_spiders_and_stale_alignment | No supports, curved supports, displaced supports, severe blur, empty image; four-blade fallback with unchanged angles; pending alignment rejected after manual angle change or source change |
| SpiderTests.test_crosshair_visibility_rotation_blink_and_live_capture | Hardware-boundary capture substitute with production camera worker, detection, rendering and UI; live three-vane evidence, explicit/manual shape, both tab visibility controls, independent rotation, optical/FOV pixel output and distinct three/four ray geometry, press/release blink, disabling tracking preserves camera capture |

All earlier integration scenarios and assertions remain registered. Crosshair
layering, startup-only FOV, pan/zoom/FOV-center transforms, tracking/manual
persistence, capture advice stability, platform/launcher failure cases and native
input checks continue through the existing mapped workflows. Historical tests
were retained. No unit tests or broad discovery were run. Earlier coverage
mapping gaps remain, including native Linux GUI/camera/release validation and
Explorer shell invocation in this restricted Windows environment. Synthetic
straight/curved spider fixtures do not establish accuracy for every real camera,
exposure or unusual support design; field photographs remain a continuation
validation target.

Validation: 70 integration scenarios, 69 passed, sole existing Explorer WinError
5 (80.769 s). Strengthened spider-only integration follow-up: all three workflows
passed (5.544 s). Log: build/gui-validation/spider-crosshair-integration.log.

## Real spider photos and whole-image rotation — 2026-10-10

| Workflow | Production behavior and failure coverage |
| --- | --- |
| SpiderTests.test_real_photographs_recognize_clear_vanes_without_moving_image | Actual PNG/JPEG loading, full optical/vane analysis and Auto-align on all three supplied native photographs; four-arm count/direction, annotated-crosshair rejection, bright/faint/partly blocked vanes, unchanged source pixels/circle assignments/image rotation |
| SpiderTests.test_repeated_image_rotation_preserves_manual_circle_size | Actual image loading/manual-tab setup, explicit missing-circle resize, repeated production rendering through a 0→90→0 degree rotation cycle, exact restored radius/manual override with no invented detection or modified raw pixels |
| SpiderTests.test_drag_angles_rotate_image_and_preserve_rotated_mouse_workflows | Real drag entry events including Shift precision, actual rotated landmark pixels and preserved frame corners, FOV-only angle changes, raw geometry preserved, rotated FOV-center dragging/rim hits/cursor-anchored zoom/empty-space pan/reset, raw PNG plus separate image/FOV-angle JSON export |

The previous spider UI assertions (image shape, visibility, angles,
invalid values, stale work, uncertain patterns, blink, camera capture, raw export
and compact layout) remain in the existing spider workflows. Independent Optical
angle was intentionally replaced by image rotation; Auto-align now affects FOV
only. Corresponding semantic assertions were updated, not removed. Toolbar
bounds are now checked against the shared sidebar instead of tab-local bounds.
Existing zero-rotation startup/FOV/layering/zoom/pan/manual/tracking workflows
remain registered. No unit tests or broad discovery. Historical equivalence gaps
remain; these three photos do not establish reliability for every physical spider,
exposure, camera or complex background. Native Linux desktop GUI/camera/release
and restricted Explorer shell invocation remain documented platform gaps.

Final validation: 73 integration scenarios, 72 passed (106.025 s), only the
existing Explorer WinError 5. Continuous coarse-to-Shift-fine dragging was added
and the complete rotated mouse/render/export workflow passed again (1.188 s).
Evidence: build/gui-validation/image-rotation-integration.log. No earlier
behavioral or failure-case assertions were deleted; documented gaps remain.

## One crosshair, complete view reset and fixed-scale pivot — 2026-10-10

| Workflow | Production behavior and failure coverage |
| --- | --- |
| GuiTests.test_crosshair_drag_moves_guides_and_follows_full_frame_through_view_changes | Single intersection/rim hit targets, shared group dragging and recentering, raw measurements unchanged, full-field rendering through zoom/reset, ordinary pan space outside the intersection, picking-mode protection |
| GuiTests.test_crosshair_follows_tracking_detect_exports_and_recenters_on_source_change | Crosshair follows the detected master during live movement and fresh detection, actual capture metadata, source/camera recentering, raw-image integrity |
| GuiTests.test_single_crosshair_has_thicker_center_and_hides_as_one_reference | Thin long arms and brighter center layer together, one visibility toggle, blink and raw-image preservation |
| SpiderTests.test_crosshair_visibility_rotation_blink_and_live_capture | Sole checkbox available above both tabs, no second crosshair state, one toggle hides/restores both long arms and center; retained three/four rays, live capture, rotation, blink and tracking pause coverage |
| SpiderTests.test_drag_angles_rotate_image_and_preserve_rotated_mouse_workflows | Fixed-scale rotated landmark rendering, coarse/fine drag angles, crosshair-only angle changes, measured geometry unchanged, shared pivot dragging, rim hit testing, cursor-anchored zoom, screen-space pan, Reset view clears both angles, raw PNG and rotation metadata |
| SpiderTests.test_rotation_uses_crosshair_pivot_at_fixed_scale_and_source_load_resets_view | Actual loaded image at zoom 1 and 2, off-center pivot fixed through 23.57/45/90/180 degrees, unchanged distances and scale, exact inverse mapping, rotated pixels outside the unrotated zoom crop, Reset view rejects pending alignment and clears angles/pan/zoom while retaining the chosen center, loading another PNG resets viewport/angles/source guides |

The old independent guide/FOV visibility and center invariants are intentionally
replaced by the user's request for one reference. The old angle-dependent corner
fit is intentionally replaced by fixed scale with viewport clipping. Existing
raw-measurement, source-reset, mouse, camera, blink, stale-work, invalid-angle,
uncertain-vane and small-screen assertions remain covered by these updated and
unchanged production workflows. The legacy fov_crosshair JSON key aliases the
canonical crosshair metadata; it does not represent another state. Historical
tests and earlier coverage gaps remain, including restricted Explorer shell
launch and native Linux desktop/camera/release validation.

Validation: `python -B scripts/test_integration.py` ran 74 integration scenarios
in 104.303 s: 73 passed, with only the existing Explorer `os.startfile` WinError
5 before application launch. Evidence:
`build/gui-validation/unified-crosshair-rotation-integration.log`. Four focused
shared-center/rotation/reset/image-load workflows also passed (4.708 s).
No unit tests were added or run. Previously documented coverage gaps remain.

## Independent FOV, stable overlay edits and antialiased rendering — 2026-10-10

| Workflow | Behavioral and failure coverage |
| --- | --- |
| GuiTests.test_fov_drag_keeps_guides_fixed_and_follows_full_frame_through_view_changes | Independent FOV drag/recenter across pan/zoom/reset, unchanged detection/group center, rim drags leave FOV fixed, small intersection target, picking protection |
| GuiTests.test_fov_position_survives_tracking_detect_exports_and_recenters_on_source_change | Actual rotated live capture and new detected master: FOV position and image affine mapping remain unchanged; fresh detection/export, source/camera resets and raw pixels retained |
| SpiderTests.test_overlay_edits_keep_rotated_pixels_fixed_and_angle_edits_use_current_center | Actual loaded-file rendering for FOV-only/manual/detected modes at zoom 1/2 and angles 0/37.25/90; inverse-rotation drags, independently fixed guide/FOV centers, pixel-identical image after drags/arrows/recentering/detection; next angle edit pivots around current FOV screen intersection; composed-transform cursor zoom and screen-space pan verified against landmarks; source load clears prior composition |
| SpiderTests.test_manual_tab_on_rotated_zoomed_file_has_no_frame_jitter | Actual PNG load at zoom 2/37.25 degrees, 24 rendered frames and repeated automatic/manual tab switches: identical pixel output, image matrix, guide center and radii, independent FOV position, unchanged raw frame and no invented detection |
| SpiderTests.test_auto_alignment_and_shared_controls | Existing real analysis workflow additionally checks Aligning…/Aligned feedback without vane count; invalid angles, uncertain designs, stale result and layout/export checks retained |
| GuiTests startup/manual/center-layer workflows and SpiderTests live visibility workflow | Antialiased stroke colors/geometry and startup feather pixels; circle visibility, center layering, three/four ray shapes, one crosshair toggle, blink and live stream remain covered |

Latest user clarification restores independent FOV and guide centers, replacing
the prior shared-reference-center assertions while retaining their underlying
mouse/raw-measurement/camera/reset coverage. Image transforms are composed only
on image-angle edits; moving references no longer rebases image pixels. Overlay
drags again use the inverse rotated-image mapping; viewport panning remains in
screen axes. Exact jagged-line pixel assumptions were replaced by strong color,
location, feathering and visibility checks for antialiased rendering; unchanged
raw landmarks and frame identity remain exact. New JSON pivot/translation fields
describe the composed image transform. Historical tests and documented coverage
gaps remain, including native Linux desktop/camera/releases and Explorer shell
launch under restricted Windows. No unit tests were added or run.

Validation: final prescribed runner, 76 scenarios in 112.783 s, 75 passed;
only existing Explorer shell-start WinError 5 remains. The overlapping-center
scenario hides the FOV handle before dragging the guide center, retaining all
group geometry, raw image, export and fresh-detection reset assertions and adding
unchanged FOV position. Evidence:
`build/gui-validation/independent-fov-antialiasing-integration.log`.

## FOV Crosshair group and exact rendered pivot — 2026-10-10

| Workflow | Behavioral and failure coverage |
| --- | --- |
| SpiderTests.test_fov_group_order_enablement_and_pending_alignment | Actual shared controls above both tabs; FOV Crosshair legend and adjacent blade switch; Center/Auto-align/status order above Reset view at 1280×720 and 1024×768; checkbox disables angle/shape/center/alignment, ignores disabled drag/button actions, rejects pending alignment, reenables valid alignment; independent image angle and Reset view stay enabled |
| SpiderTests.test_fractional_image_pivot_and_white_fov_marker_independence | Actual loaded PNG, Tk-rendered image centroid at fractional FOV center for zoom 1/2 and image angles 0/0.01/37.25/90/180; pixel sampling consistent at zero angle; white center stays at FOV when manual group moves, follows only FOV, hides with checkbox; raw image exact |
| GuiTests.test_maximized_startup_and_keyboard_fullscreen_keep_source_and_view | Decorated maximized startup, fullscreen button absent; optional keyboard-bound fullscreen actions retain source/session/zoom, restore normal or maximized state and title decorations |
| Existing startup/layering/visibility, live capture, overlay-drag, image-rotation, tab-jitter and compact-layout workflows | Retain rays, shape changes, one FOV checkbox, blink, circle visibility, stale work, invalid angles, source resets, transform geometry and raw exports; full review text and controls fit ordinary screen sizes without jumping |

The removed fullscreen button is an intentional UI change; its window-state and
source-preservation checks remain through the retained keyboard action. The
white center accent now appears with FOV even before guides/detection, replacing
an old guide-dependent visibility assumption. Strong red ray checks accept
antialiasing at fractional pixel positions while still checking red dominance,
geometry and startup feathering. The image centroid test checks rendered pixels,
not only mathematical transform agreement. The thicker white accent retains
three adjacent bright neutral pixels; fractional antialiasing permits a feathered
side pixel instead of requiring every side pixel to be exactly 255. Native Linux desktop/camera/release,
restricted Explorer launch and previously recorded equivalence gaps remain.

Final validation: `python -B scripts/test_integration.py` ran 78
integration scenarios in 139.751 s: 77 passed, with only the existing
restricted Explorer `os.startfile` WinError 5 before application launch. Evidence:
`build/gui-validation/fov-group-pixel-pivot-integration.log`. No new behavioral
or failure-case coverage gaps; previously documented platform/equivalence gaps
remain. No Git operations or unit tests.

## White circle-center marker, centered reset and quiet success — 2026-10-10

| Workflow | Retained coverage and corrected behavior |
| --- | --- |
| GuiTests.test_startup_only_fov_and_manual_tab_visibility | Startup has red FOV only, no white guide marker; manual circle presets, layering, tab visibility, colors and hit targets retained |
| GuiTests.test_white_guide_center_is_thicker_and_independent_of_fov_visibility | Actual detected circles render a thick white center; FOV toggle removes red rays while white guide marker stays; blink removes/restores both; raw detection unchanged |
| SpiderTests.test_fractional_image_pivot_and_white_circle_center_independence | Loaded image pixel centroid for fractional FOV pivots at zoom 1/2 and rotations 0/0.01/37.25/90/180 retained; white marker follows manual circle center, FOV edits/toggle keep marker fixed, guide visibility removes marker, raw pixels exact |
| GuiTests.test_fov_drag_keeps_guides_fixed_and_follows_full_frame_through_view_changes; SpiderTests.test_rotation_uses_crosshair_pivot_at_fixed_scale_and_source_load_resets_view | Reset explicitly centers FOV while retaining guide geometry; existing independent dragging, inverse transform, zoom/pan, fixed-scale rotation, stale alignment rejection and source resets retained |
| SpiderTests.test_auto_alignment_and_shared_controls; test_fov_group_order_enablement_and_pending_alignment; test_crosshair_visibility_rotation_blink_and_live_capture | Successful alignment updates angles without Aligned announcement or replacing capture advice; progress, uncertain designs, invalid angles, generation rejection, control enablement, shape, live stream, blink and export retained |

The user's clarification intentionally replaces white-at-FOV and reset-keeps-FOV
assumptions. The small white marker belongs to circle guides; the large red FOV
remains independent and remains the image-rotation pivot. Historical assertions
and coverage entries above describe earlier behavior. Integration tests retain
all underlying mouse, pixel, source, failure and platform coverage under the
corrected semantics. Previously documented Explorer/native Linux/equivalence
gaps remain; no unit tests or Git operations.

Final layout steering: the angle entry occupies the former alignment-status
position inside the group, beside Auto-align; the legend holds only checkbox
and blade switch. The production widget workflow checks matching row positions,
angle below the legend, removal of status widget, disabled input, pending-result
rejection and compact layout. Busy feedback is displayed in the disabled
Auto-align button; uncertain/error advice remains.

Final validation: `python -B scripts/test_integration.py` ran 78
integration scenarios in 148.285 s: 77 passed; only the existing
restricted Explorer `os.startfile` WinError 5 occurred before application launch.
Evidence: `build/gui-validation/circle-center-reset-angle-layout-integration.log`.
No new coverage gaps; documented native Linux and historical equivalence gaps
remain. No unit tests or Git operations.

## Matching white guide-marker shape and angle — 2026-10-10

SpiderTests.test_white_guide_marker_matches_fov_shape_and_angle uses actual
loaded PNGs, Tk rendering and shared controls to check white/red ray positions
for four blades at 0/45 degrees and three blades at 0/90/13.37 degrees, including
37.25/90-degree image rotations. Missing diagonal/opposing rays distinguish
three/four patterns. FOV hides independently without changing the white patch;
raw source pixels remain exact. Production detection and Auto-align on three
and four straight-vane fixtures update the white marker's rays automatically.
The earlier fixed white-angle/four-blade behavior is intentionally replaced;
independent centers, circle/FOV visibility, blink, pixel transforms, source/reset,
error and pending-work coverage remain. Existing native Linux, Explorer launch
and historical equivalence gaps remain. No unit tests or Git operations.

## Image-based Auto-align and Detect alignment — 2026-10-10

| Workflow | Behavior and failure coverage |
| --- | --- |
| SpiderTests.test_detect_rotates_image_once_and_keeps_crosshair_fixed | Loaded PNG at zoom 2, nonzero image/FOV angles and off-center pivot; Detect rotates actual raw landmark pixels, preserves visible FOV orientation/position and numeric crosshair angle, aligns measured vanes; repeated Auto-align yields identical pixels/matrix; export records shared compensation and retains exact raw PNG; Reset clears compensation while keeping guides; reset or angle edit during in-flight detection rejects automatic rotation |
| SpiderTests.test_auto_alignment_and_shared_controls | Detect + Auto-align on 3/4/2/3 supports at several angles; image-angle accuracy replaces old crosshair-angle mutation; crosshair angle/raw image/selections unchanged; progress/silent success, manual blade switching, invalid angles, compact layout and export checks retained |
| SpiderTests.test_real_photographs_recognize_clear_vanes_and_rotate_display_only | Same three real photographs and detector accuracy; displayed image turns, FOV angle/raw pixels/edge selection remain unchanged |
| SpiderTests.test_uncertain_spiders_and_stale_alignment; existing live/overlay/image mouse workflows | Uncertain/blurred/curved/offset inputs retain rotations; source and manual-angle changes reject in-flight alignment; matching markers, live stream, held tracking, rotated drags, pivot and zoom/pan remain covered |

Auto-align intentionally replaces the former FOV-angle change with image rotation
and a shared render compensation that keeps crosshair orientation fixed. Only
explicit Detect aligns automatically; background analysis refreshes vane
evidence without changing rotation. Reset/source load clears compensation.
Metadata retains the user angle and adds rotation_compensation_deg and
render_angle_deg; existing JSON aliases/raw exports remain. All historical
tests and coverage gaps remain; native Linux desktop/camera/releases and
restricted Explorer launch are still unvalidated.

Final validation: `python -B scripts/test_integration.py` ran 80
integration scenarios in 160.966 s: 79 passed; only existing restricted
Explorer `os.startfile` WinError 5 before application launch remains. Evidence:
`build/gui-validation/image-auto-align-detect-integration.log`. No new coverage
gaps; previously documented Linux desktop/release and historical equivalence
gaps remain. No unit tests or Git operations.

## Rotation steps, radius dragging and application rename — 2026-10-10

| Workflow | Behavior and failure coverage |
| --- | --- |
| SpiderTests.test_rotation_step_buttons_branding_and_view_order | Actual ± buttons give 0.01° steps, 0/360 wrap, pending typed value and invalid-text recovery; FOV buttons disabled with checkbox, image buttons remain available; raw center preserved; both tabs at 1280×720/1024×768, view toolbar above FOV group above tabs, Rotation label, visible button bounds; Advanced Astro Collimator window title and actual start.py --version subprocess |
| GuiTests.test_radius_horizontal_drag_tracks_pixels_and_cancels_safely | Real focused Tk press/motion/release at zoom 2/37.25°; whole raw-image radius with coarse-to-Shift fine motion, selected radius only, common center and other sizes preserved, tracking/image held through drag and stream resumes on release; lower-bound clamping/reversal, invalid values, Escape and mid-drag source-change cancellation without new-source advice corruption |
| Existing radius entry/buttons/wheel/tracking and image/marker/angle workflows | Typed Enter/Escape validation, exact radius, manual references, tracking retention, image and crosshair drag angles, matching rays, auto-alignment, disabled controls, raw exports, errors and compact guidance coverage retained |

The requested ordering intentionally replaces Auto-align above Reset view with
view controls above the FOV group. Package metadata, launcher/error UI, native
release build configuration and current user documentation use Advanced Astro
Collimator / AdvancedAstroCollimator. Historical release evidence and archives
retain their original names; new native release binaries have not been built.
This release-artifact branding and native Linux desktop/camera/release behavior
remain explicit validation gaps, together with restricted Explorer launch and
previously documented historical equivalence gaps. No unit tests or Git operations.

Rounded-scale follow-up: retained the strict Auto-align displayed-direction
assertion by deriving correction/compensation through real forward/inverse
vectors when viewport dimensions round to nonuniform scales. White marker
checks still require three contiguous bright neutral pixels; fractional
subpixel placement permits a feathered side pixel ≥180 (measured 181 at half
pixel) instead of demanding exact 255. Blink, layering, location and red-ray
checks remain. Native build CLI reports no CPU architecture in this isolated
64-bit environment, so artifact-branding validation remains pending.

Final validation: `python -B scripts/test_integration.py` ran 82 integration
scenarios in 163.621 s: 81 passed; one existing Explorer association scenario
failed before application launch with `os.startfile` WinError 5 (Access denied).
No application workflow failures remain. Evidence:
`build/gui-validation/rotation-radius-branding-integration.log`. Coverage mapping
retains existing workflows and failure cases, plus the two new GUI scenarios.
Release artifacts remain unbuilt; native Linux desktop/camera/releases, Explorer
launch in this restricted environment and earlier historical equivalence gaps
remain explicitly unvalidated. No unit tests or Git operations.

## Named camera selection and detection action — 2026-10-10

| Workflow | Behavior and failure coverage |
| --- | --- |
| WorkflowTests.test_named_camera_selection_refresh_fallback_and_detection_label | Production Linux discovery/worker/Tk with sysfs/ioctl/capture hardware boundary; duplicate names map to separate indices, real selector event switches stream, refresh retains index after rename or inaccessible names, resume selected camera after image detection/export; exact detection button label and ordinary-screen width |
| WorkflowTests.test_windows_native_camera_names_scan_stream_and_refresh | Actual Windows DirectShow names, worker scan and Tk selector with capture boundary substitute; labels agree with native enumeration, switch to second index and retain it on refresh |
| Existing Linux query/permission and no-camera/switch/stale/stream workflows | Driver control ranges, resources, permission fallback, no-camera recovery, selection and stream lifecycle remain; labels intentionally now include available names |

Two integration workflows added without removing prior behavioral/failure
coverage. Windows FriendlyName query succeeds on this host (USB2.0 HD UVC
WebCam). Name-read permission failure and blank fallback covered through Linux
hardware boundary. Windows COM failure/cleanup branches not directly forced;
native Linux desktop/camera/release and existing Explorer/historical equivalence
gaps remain. Runtime uses only native local APIs. Full runner result follows.

Camera-name validation before the outline-chooser steering: the full explicit
runner completed 84 scenarios in 174.754 s; 83 passed and the existing Explorer
os.startfile WinError 5 remained. Evidence: build/gui-validation/camera-names-integration.log.

## Direct circle editing replaces outline navigation — 2026-10-10

| Existing workflow adapted | Preserved behavioral/failure coverage |
| --- | --- |
| GuiTests.test_static_detection_draws_guides_without_confirmation | Automatic named guides, no confirmation, live stream, clear selected reference and resume/manual state; clear action replaces chooser's unassigned selection |
| GuiTests.test_outline_replacements_keep_roundness_and_the_master_center | Same oval fixture rejects unverified focuser; actual three-point manual replacement establishes master; actual typed radius events edit each role while preserving roundness and common center; fresh Detect retains no-confirmation/roundness |
| GuiTests.test_named_outlines_hide_extra_hypotheses_and_guidance_advances | Added unused hypothesis changes no rendered pixels; chooser widgets absent; manual replacement yields distinct id, one per role, new focuser master/shared center; clear selects another master, restart restores best guesses, capture advice and compact layout |

Candidate cycling/selection UI is intentionally retired by user request, and its
geometry/master/clear/uniqueness coverage is exercised through supported direct
editing/manual replacement. Detector ranking/thresholds, uncertain-input advice,
raw observation metrics, tracking retention, mouse/typed/drag radius editing and
platform workflows remain covered. Historical cases preserved; no new coverage
gaps apart from the already recorded platform/native COM failure paths.

Final validation: `python -B scripts/test_integration.py` completed 84 scenarios
in 163.678 s: 83 passed; only the existing Explorer `os.startfile` WinError 5
(Access denied, before app launch) remains. Evidence:
`build/gui-validation/camera-names-direct-guides-integration.log`. Afterward, the
missing-guide hint was corrected to name Pick center for the mark and Pick edge
for rims; the complete named-outline/manual replacement/guidance/layout scenario
passed again in 1.998 s, including both exact action-label assertions. Evidence:
`build/gui-validation/direct-guide-action-label-integration.log`. All previous
behavioral/failure coverage is mapped; chooser navigation is intentionally retired.
Native Linux desktop/camera/release, forced Windows COM name-query failure cleanup,
restricted Explorer launch and historical equivalence gaps remain documented.
Runtime stays offline; no unit tests, Git operations or new release builds.

## Consistent rotation adjustment layout — 2026-10-10

SpiderTests.test_rotation_step_buttons_branding_and_view_order now also verifies
actual horizontal widget ordering/nonoverlap and shared row alignment for minus,
label, entry, degree unit and plus on both rotation rows, both guide tabs and
1280x720/1024x768. Existing angle-step/wrap/invalid input/disabled controls, raw
center and launcher assertions retained. Existing group/pending-alignment and
rotated-angle dragging workflows pass. No scenarios removed or coverage gaps
introduced; native Linux/COM failure/Explorer/historical gaps remain.

Final validation: `python -B scripts/test_integration.py` ran 84 scenarios in
178.085 s: 83 passed, with only existing Explorer os.startfile WinError 5
(Access denied before app launch). Evidence:
`build/gui-validation/rotation-control-order-integration.log`. Existing scenario
coverage retained and layout assertions extended; no new validation gaps. Native
Linux desktop/camera/releases, forced Windows COM failure cleanup and earlier
historical/Explorer gaps remain. No unit tests, Git operations or release build.

## Phone photo/video source and local certificate identity — 2026-10-10

The previous 84 workflow scenarios remain explicitly selected. The no-camera
scenario now verifies a selectable phone option instead of a disabled camera
selector, while retaining physical-camera refresh/recovery assertions. No old
scenario or historical file was removed. New PhoneTests workflows use real Tk,
local HTTP/HTTPS sockets, production image decoders, detection/tracking/averaging
and raw PNG/JSON export. The browser runs the actual bundled HTML/JS with virtual
camera hardware; its test context accepts local HTTPS without installing OS trust.
Separate real TLS requests verify CA chain, IP hostname and the peer fingerprint.

| Behavior / failure path | Production integration workflow |
| --- | --- |
| Camera selection, actual displayed QR decoding, original PNG bytes, EXIF orientation, HEIC, fresh view/detection, clean paired export, ordinary screen bounds | PhoneTests.test_photo_qr_exif_heic_auto_detection_and_raw_export |
| PC dialog/page/actual TLS peer SHA-256 agreement, root download, certificate-only iOS profile, locally unique identities, persistent root, HTTPS photo receipt | PhoneTests.test_local_tls_identity_matches_pc_phone_peer_and_persists |
| Damaged/incomplete optional certificate identity is retained; HTTP photos/detection still work and trust controls are unavailable | PhoneTests.test_http_photos_survive_failed_optional_certificate_setup |
| Live source independent of USB controls, latest-only mailbox, tracking pause keeps preview, stale advice excluded from export, unmatched manual radius retained, stop/restart and manual reconnect retention | PhoneTests.test_live_phone_tracking_pause_latest_frame_manual_retention_and_disconnect |
| Actual paced phone frames average while steady, real four-second stream-loss timeout, QR restoration and unchanged zoom/rotation on reconnect | PhoneTests.test_live_phone_averaging_timeout_and_reconnect_keep_view |
| New photo during pending detection is analyzed with matching pixels/size and at most one analysis worker | PhoneTests.test_new_photo_during_detection_uses_latest_image_without_parallel_analysis |
| Incomplete slow upload bounds decoding, simultaneous image rejected with 503, stop still responds, late frame rejected and next photo succeeds | PhoneTests.test_slow_upload_backpressure_allows_stop_and_rejects_late_frame |
| Wrong Host/token/cross-origin, corrupt/tiny/excessive-pixel/oversize photos, malformed stream JSON, duplicate/out-of-order/wrong-stream frames and photo ending video | PhoneTests.test_receiver_rejects_bad_inputs_origins_tokens_and_stale_frames |
| File/phone/webcam switches, Live camera returning to chosen phone, stopped ports, startup cancellation/shutdown and receiver threads retiring | PhoneTests.test_phone_switch_to_file_webcam_and_shutdown_releases_ports |
| Real mobile-size browser photo receipt, raw-file fidelity, shown fingerprint, HTTP→HTTPS video navigation, actual media/canvas/frame uploads, stop, no JS errors or external page requests | PhoneTests.test_mobile_browser_photo_and_video_use_production_page_and_receiver |

Gaps explicitly retained: real Android/iPhone capture and certificate-install/trust
UI, physical LAN/firewall/adapter behavior, native Linux desktop/camera/receiver
and rebuilt native releases. Pixel-limit rejection is exercised using a valid
PNG header, not a full 60 MP image allocation. Browser permission-denial and
phone-specific HEIC/orientation variants remain device validation. Previous
historical equivalence and forced native COM failure-path gaps remain recorded
above. Browser tooling missing from a test environment is an explicit skipped
workflow, never a claim of coverage. No unit tests or broad discovery are used.

Final validation: `.venv/Scripts/python.exe -B scripts/test_integration.py`
passed all 94 scenarios in 235.656 s, with no skips. Evidence:
`build/gui-validation/phone-native-final-integration.log`. This retains the prior
84 workflows and adds 10 complete phone-source workflows. Real Windows native
wheel input and Explorer association passed in this run. The source wheel was
built and its mobile assets/personal-key/test exclusions verified. Real Android/
iPhone capture and trust UI, physical LAN/firewalls, native Linux desktop/adapter/
camera behavior and rebuilt portable executables remain unvalidated; earlier
historical equivalence/native COM failure gaps remain recorded. No Git operations,
unit tests, broad discovery, OS trust changes or firewall changes.

## Startup dependency gate and main-view QR — 2026-10-10

All previous 94 workflows remain selected. The existing missing-dependency launch
workflow now checks the aggregate report for every required package and retains
nonzero exit, interpreter/log and untouched-settings assertions. The new
WorkflowTests.test_source_launcher_rejects_missing_phone_packages_and_broken_native_codec_then_recovers
uses an isolated real installation: copies the existing optical dependencies,
omits the three phone dependencies, installs real packages offline, removes only
the copied native HEIF extension, then repairs it and completes the production
launcher/detection/export smoke workflow. No import/detector substitutions.

The photo workflow additionally decodes the main-view QR, checks actual widget
bounds at 1024x768 and 1280x720, verifies received images replace the card, toggles
QR/image without losing pixels, and checks hidden-image wheel/drag isolation.
Existing stop/timeout/reconnect workflows retain QR restoration and manual/view
retention assertions. Damaged local identity keeps HTTP photos and now checks the
shown cause and token-free error log with interpreter location.

Coverage gaps retained: real phone trust/capture UI and LAN/firewalls, native Linux
desktop/camera/releases, forced native COM failure and historical equivalence.
Tk/display failure is checked at production startup but is not induced in the
Windows integration environment; catastrophic native-library process crashes
cannot be converted into Python startup dialogs. No unit tests or broad discovery.

Final validation: `.venv/Scripts/python.exe -B scripts/test_integration.py`
passed all 95 production integration scenarios in 222.335 s, without skips.
Evidence: `build/gui-validation/startup-phone-view-integration.log`. This includes
actual Explorer startup through the associated system interpreter, the repaired
real-package/native-codec workflow, main-view QR decoding/layout/state transitions,
local HTTP/TLS and the production mobile browser page. Native Linux desktop, real
iPhone/Android capture/trust UI, physical LAN/firewall behavior and rebuilt portable
releases remain unvalidated; historical equivalence/native COM failure gaps are
still recorded. No Git operations, unit tests, broad discovery or trust changes.

## Browser shutter and shared camera zoom — 2026-10-10

All prior 95 scenarios remain selected. Existing real mobile-browser workflow
retains original HTTP file fidelity, certificate display/navigation, real video
frames/stop, no external requests and JS-error checks. It now verifies browser
preview/shutter with no native-camera capture input, actual still receipt and
desktop detection, reusable preview after Stop video, and camera release. Browser
route callbacks are serviced until real successful frame/photo responses before
waiting separately on Tk; receipts include both frames and stills.

New PhoneTests.test_browser_camera_zoom_stills_live_transition_and_hardware_failures
uses the production page, real browser track/image capture/canvas, local HTTPS
receiver, desktop analysis and raw PNG export. The fixture decorates only camera
hardware interfaces to expose reported ranges and camera-specific failures.
Coverage: reported min/max/step, serial/latest zoom requests, native still with
shared zoom, rejected and ignored constraints reverting to actual setting, zoom
during real video, native-still failure producing an uncropped PNG preview frame,
video-to-photo receipt/source switch, unsupported zoom retaining photo capture,
permission denial with file upload still available, and cancelled acquisition
releasing late tracks. No detector/server/Tk/transfer substitutions.

Gaps retained: actual mobile optical versus digital/lens-switch behavior, Safari/
iOS-specific fallback and permission/trust UI, real LAN/firewalls, Linux desktop/
camera/releases, native COM failure and historical equivalence. Browser without
the ImageCapture constructor is handled in production but not reproduced by a
second real browser engine here; native-still hardware rejection covers the
preview PNG path. Captured zoom correctness on physical optics requires a phone.
No unit tests, broad discovery or Git operations.

Final validation: `.venv/Scripts/python.exe -B scripts/test_integration.py`
passed all 96 production integration scenarios in 214.512 s, without skips.
Evidence: `build/gui-validation/browser-photo-zoom-integration.log`. All previous
95 scenarios remain selected, with the existing browser workflow extended and
one complete camera-capability/failure workflow added. Native browser still
capture, full-frame PNG fallback, shared camera zoom control, unsupported/ignored/
rejected zoom, permission denial, cancellation, video/photo switching and raw
export passed through production components. Screenshot:
`build/gui-validation/phone-camera-zoom.png` (390px mobile view, inspected).
The user reports existing phone video works; device/browser identity is not
recorded. Physical optical zoom and new browser still capture on real phones,
Safari/iOS-specific capture/permissions/trust, LAN/firewall behavior, native Linux
desktop/camera/releases, rebuilt portable executables, native COM failure and
historical equivalence gaps remain. No Git operations, unit tests, broad discovery,
certificate installation or added runtime dependencies.
