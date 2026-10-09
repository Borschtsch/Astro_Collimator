# Continuation checkpoint — updated 2026-10-09

## Direct Python startup correction — 2026-10-07

User clarified that Explorer already invokes the associated Python interpreter;
no CMD file or alternate interpreter is wanted. Remove start.cmd and automatic
venv/pythonw switching. Keep the existing start.py entry (the latest message says
setup.py; clarification is pending because that file does not exist here).
Retain visible startup errors/logging and validate direct source startup via the
existing association without windowed flags. Earlier bootstrap/venv selection
notes below describe the rejected approach, not current behavior. No commits.

## Source double-click startup plan — 2026-10-07

Make start.py a source bootstrap: prefer a configured local .venv, use pythonw on
Windows for GUI launches, preserve CLI arguments and the shared frozen launcher,
and show startup failures with a log instead of an invisible exit. Add start.cmd
as an association-independent Windows entry that still calls start.py. Do not
modify system file associations or install dependencies at runtime. Validate real
source launches, virtual-environment selection and Explorer file association via
complete app smoke workflows. No unit tests or Git operations.

## Windows and Linux support — 2026-10-07

Implemented native Linux portability in the existing source package, keeping
start.py and offline runtime. Plan/handoff: PLATFORM_SUPPORT.md. Tk window-state
helpers use X11 -zoomed instead of unsupported wm state zoomed; wheel helpers
support MouseWheel and Button-4/5 everywhere. Fullscreen restoration preserves
normal/maximized state. Windows native DirectShow behavior remains.

Linux cameras use explicit /dev/videoN + CAP_V4L2 with raw property units, enumerate
non-contiguous/high video indices, and query ranges via the read-only V4L2 ioctl
interface. Inactive/locked/unsupported controls are disabled; failures stay unknown
with numeric fallback. Automatic modes are never changed by range querying.

scripts/build_portable.py shares assembly, source/frozen/archive workflow checks
and documentation/license copying. Windows and Linux wrappers enforce native OS;
ZIP for Windows, tar.gz for Linux preserving symlinks and permissions. Build outputs
use separate platform/architecture folders and refuse existing application folders.
The old flat Windows portable folder and ZIP are unchanged.

Validation: 54 integration scenarios passed on Windows (163.735 s); additional
maximized fullscreen restoration assertions passed in a targeted UI rerun (0.909 s).
Three new complete UI/camera/export workflows exercise Linux wheel input, native
range parsing/device scan/control/switch and query permission failure. Only the
physical capture/device/OS ioctl boundary is substituted. Historical tests and
previous assertions are retained; historical coverage-equivalence gaps remain.
No unit tests or Git operations. UTF-8 BOM state and line endings preserved.

The rebuilt Windows release passed source, executable and extracted/relocated ZIP
checks. Archive: dist/windows-x64/AstroCollimator-0.1.0-windows-x64.zip.
Machine-readable evidence: docs/PLATFORM_VALIDATION.json.

Next: obtain SSH to the user's actual Linux VM with a logged-in graphical desktop
(no WSL). Install the documented Linux dependencies in a native venv; use the same
user's actual DISPLAY/XAUTHORITY. Run scripts/validate_linux.py, then --build after
installing requirements-build.txt/binutils. Reports under build/linux-validation.
Native Linux desktop behavior, real V4L2 drivers and frozen/relocated Linux releases
are NOT validated yet. Pass a USB camera through to the guest for the separate
real-camera checklist. Linux baseline/architecture support must be determined by
native results; x64 checks do not certify arm64 or every distro.

## Current package name: source — 2026-10-07

User requested source as the application package name. The folder is renamed;
start.py imports source.launcher. All active/historical test imports and mock
targets, build-script imports, setuptools package discovery/version metadata,
AGENTS.md and current architecture/layout documentation now use source.
Relative application imports and source-root settings behavior are unchanged.
Astro Collimator remains the product/distribution name.

Validation: all 51 existing integration scenarios passed (160.750 s). Source
startup from another working directory passed the real application smoke workflow.
The existing self-contained portable release also passed; its files were left
unchanged and future builds use the renamed source package. All 80 historical
component cases remain; no unit tests were run. No commits or Git operations.
Earlier package names and paths below describe historical checkpoints only.


## Latest maintenance: test images relocated — 2026-10-07

User moved the native image fixtures into tests/images. TEST_IMAGES in
tests/fixtures/images.py now resolves that folder independently of cwd. Both
active integration and historical image checks use the shared constant; no
image assertions changed. Development layout documentation is updated.
Validation: the targeted native-photo application integration workflow passed
(1 scenario covering all 14 photos, 9.414 s). No unit tests or Git operations.
Application and portable release are unchanged; test images remain excluded.


## Current: shareable source layout and verified portable Windows release — 2026-10-07

User requested a clean source layout, one start.py entry point, a concise
astronomy-focused README, separate user documentation and simple distribution.
Plan recorded in DISTRIBUTION_PLAN.md before moving files.

- Only start.py remains as a root Python file. Application code is packaged in
  astro_collimator/ with relative imports; app.py contains the original app shell.
  Source and frozen launch share launcher.py. Version metadata is 0.1.0.
- Existing root options.json remains in place. Source settings resolve beside
  start.py; frozen settings resolve beside AstroCollimator.exe. Neither depends
  on cwd or PyInstaller's internal data directory. Release checks use temporary
  settings and do not change personal options.
- Active scenarios moved to tests/integration, fixtures to tests/fixtures and all
  80 historical component cases to tests/legacy. No test assertion was removed.
  Fixture paths use the user's TestImages folder. Explicit runner is now
  scripts/test_integration.py; no legacy/unit classes are selected or executed.
- README introduces Newtonian collimation assistance for astrophotographers and
  links GETTING_STARTED.md, USER_GUIDE.md and DEVELOPMENT.md. Controls and optical
  interpretation are in the user guide; technical history stays in developer docs.
- scripts/build_windows.py builds a versioned windowed x64 portable application
  and ZIP, includes user docs/build versions/dependency notices, excludes personal
  options/tests/photos and refuses to overwrite an existing release folder.
  Requirements pin validated runtime/build versions. Build uses an isolated venv,
  leaving shared Python unchanged. No runtime network dependency was introduced.
- Validation: all 51 relocated integration scenarios passed in one run (156.586 s).
  Source startup from another working directory, actual frozen app and relocated
  extracted ZIP passed production workflows: decorated maximized Tk, options,
  Unicode PNG import, role detection, guidance and exact paired export. The ZIP
  check removed Python-related search paths and used spaces/Unicode in its path.
- Artifact: dist/AstroCollimator-0.1.0-windows-x64.zip (74,479,300 bytes).
  See DISTRIBUTION_VALIDATION.json for checksum, build versions and actual results.
  Nothing was published/uploaded, and no commits/Git operations were performed.

Deployment smoke support is hidden from normal CLI help: start.py --smoke-test
--report <file>. It substitutes only absent hardware and uses real app components.
It is a release integration workflow, not a unit test. Camera/telescope hardware
validation and the historical coverage-equivalence gaps remain outstanding.

Next: use the supplied portable ZIP for Windows distribution; review real camera
behavior on a second computer before announcing hardware compatibility. Close
existing integration-equivalence gaps and calibrate optical advice as separately
recorded. Earlier flat-module entry/test commands below are historical only.

## Previous checkpoint: live tracking and validation policy

## Fast tracking, steady-frame averaging, decorated maximized startup

User confirmed both changes: improve live detection with fast rim tracking and
short averaging while steady, and restore the missing title bar. Also recorded
the latest validation decision: **integration tests only, with the same behavior
and failure-case coverage as before**. See AGENTS.md and INTEGRATION_COVERAGE.md.
No unit classes/discovery should be run from this checkpoint onward. Historical
results below are retained as history, not current instructions.

- New live_detection.py updates assigned raw rims/details from local image
  evidence. Round/shared display guides are never used as measured centers.
  Local fits preserve role IDs and independent measured shape/centers; weak,
  missing or distant evidence falls back to the existing full detector.
- Successful local cadence is 100 ms minimum; full-only cadence remains 350 ms.
  Full discovery runs periodically: 1.5 seconds with missing/held required roles,
  3 seconds otherwise. One analysis worker and latest-frame scheduling remain.
  Manual geometry remains held/reacquired through the existing merge pipeline.
- A small preview checks distributed and local changes, camera translation and
  illumination. Keep at most three recent captures over 120 ms while steady;
  clear on motion, source/size/time gaps and editing/tracking pauses. Average in
  the analysis worker. Display/export the exact analyzed average; JSON records
  analysis.mode and analysis.averaged_frames. Raw preview continues when tracking
  is off, with stale observation/advice rules unchanged.
- Startup uses root.state("zoomed") after widgets are laid out, with fullscreen
  disabled, keeping normal Windows decorations. Optional F11 remembers and
  restores previous window state; Escape/Windowed exits. Source/view remain intact.
- Explicit runner: `C:\Python313\python.exe -B run_integration_tests.py` selects
  the 43 existing GUI workflows plus new complete application scenarios; it does
  not execute historical component/unit classes. New scenarios cover native PNG
  import -> detection -> render -> raw export, raw-scale pupil identity, quality
  captures, setup atomic failure/legacy/future formats, noisy live averaging,
  loss/full fallback/recovery and scaled camera-reference tracking.

Integration validation on Windows/Python 3.13: all 43 retained GUI scenarios
passed in the combined runner. Its first new noisy-camera check failed because
three UI-delivered captures did not fit the 120 ms window at the larger test
render size (two-frame averaging correctly remained active). The test now uses
900x700 rendering without changing the production age/count bounds or assertions.
All 8 new WorkflowTests methods then passed in an explicit targeted integration
rerun (29.282 s), including 14 native photos. Thus 43 retained plus 8 new scenarios
have passed across runs; this is not a claim of a clean final combined run or
identical historical component coverage. No unit classes or discovery were run
after the decision. Hardware/model calibration remains unverified.

Coverage equivalence is a required acceptance gate, not a claim based on test
count. INTEGRATION_COVERAGE.md maps all historical categories and explicitly
lists missing equivalents (notably native COM, optical advice branches and some
tracking/negative-input cases). Migration remains incomplete until those are
covered. Keep historical tests as the reference. Do not delete them or silently
relax expectations. A missing local image fixture remains unavailable.

Limits: local tracking is conservative and does not improve initial optical
identity. Abrupt motion, soft/merged rims and scaled small details may trigger
full searches; manual/soft focuser references require full discovery. Temporal
averaging is bounded denoising, not a calibrated optical measurement. Native
photos and synthetic camera playback do not certify real telescope alignment.
Further work: close integration-coverage gaps, validate paced low-FPS/focus/local
motion resets, record real hardware cadence and collect labelled optical views
before calibrated screw advice or a harmonized forward model.

## Previous checkpoint: independent movable startup FOV reference

Latest request: an on/off control for the absolute FOV crosshair and movement;
user clarified the startup crosshair already exists. The plan was recorded in
DETECTION_IMPROVEMENTS.md before implementation and updated for that clarification.

- Reuse the existing startup red full-field crosshair, default on. Render one
  crosshair only; old manual circle rendering no longer draws a duplicate.
  The independent FOV crosshair checkbox and Center FOV control stay above tabs.
- Left-drag within 12 display pixels of its intersection moves only the reference,
  with the move cursor. At a coincident guide center, FOV drag takes priority.
  Circle-rim dragging still moves all optical guides; Ctrl+wheel sizes circles.
  Distant crosshair line portions/empty space still pan. Picking blocks grabbing.
- Position uses normalized full raw-frame coordinates. Zoom/pan, window resize,
  Reset view, Detect and live tracking cannot recenter it. Center FOV explicitly
  resets to full-frame center. A new image/camera source resets position but keeps
  the selected visibility. The existing manual guide center/d-pad stays separate.
- Show overlays and press/release blink hide it too. Thin red lines with black halo
  remain readable; no extra central circle or second full-field crosshair is added.
  Moving this viewing aid changes neither raw observations nor alignment advice.
- Capture JSON stores visible, center_fraction and center_px in fov_crosshair;
  raw PNG stays overlay-free. This reference is not physical field-angle or optical
  calibration. It is not added to saved telescope options.
- To fit the added global controls, capture messages use four fixed lines with
  shorter focus advice; selection remains three fixed lines. Compact two-line
  mouse help and existing fixed slots preserve regular-screen no-scroll layout
  and stable interactive controls. Previous tracking/fullscreen behavior persists.

Validation: `C:\Python313\python.exe -B -m unittest discover -q` — **123 run,
122 passed, 1 skipped** (absent local `lox/image (1).jpg`). New UI checks cover
startup default, independent toggle/blink/global visibility, forgiving mouse drag,
unchanged guides, pan/zoom/reset mapping, circle-rim movement independence,
tracking/Detect retention, capture export, source reset and controls across tabs.
Existing stable-layout/camera/pupil/pixel-radius checks remain. UTF-8 flavor is
preserved. No commits/Git operations or runtime network calls.

Next optical work remains labelled real-image validation, camera geometry and
uncertainty calibration, reflected pupil/mark verification and screw response
before a tested integrated model. The crosshair is a viewing aid only.

## Previous checkpoint: tracking, stable controls and fullscreen

## Current: stable controls, continued preview with tracking off, fullscreen

Latest corrections: disabling live edge tracking must keep the camera preview
running; unreliable recognition must not make the checkbox/controls jump; app
starts fullscreen. The plan and additional layout report were recorded before
code in DETECTION_IMPROVEMENTS.md. Optional mark/pupil/pixel-radius work below
remains current. Runtime offline, Newtonian only, no commits or Git operations.

- Track live edges disables only analysis, invalidates in-flight work and clears
  pending analysis frames. Camera/session stays open; new raw images continue
  displaying behind held circles. Re-enable analyzes the same selected camera
  without reopening or clearing references. Live camera action still explicitly
  switches source/reopens when requested.
- One-shot Detect with tracking off resumes preview after the result. Picking,
  numeric radius editing and active image/circle dragging temporarily freeze the
  view for exact edits; finish/cancel resumes the feed independently of tracking.
  Active tracking still pairs accepted observation snapshots with displayed frames.
- Paused UI says the circles hold last measurements. New raw preview frames set
  observations_current false; accepted analyzed frames set it true. Capture PNG
  is the current raw image; JSON exports observations_match_image and omits stale
  camera alignment advice when the observations refer to an earlier frame.
- Tracking checkbox is in the stable upper action area, before capture messages.
  Capture and selection labels reserve five/three lines; changing detections no
  longer move role buttons, radius entry or pick controls. Compact padding/help
  preserves full no-scroll layouts at 1280x720 and 1024x768.
- Actual fullscreen starts enabled. Visible Windowed/Fullscreen control and F11
  toggle it; Escape exits (in a radius entry, Escape first cancels typing).
  Window geometry, source, zoom and references are preserved. Tests assert the
  default fullscreen state then put hidden windows in normal mode for layout QA.

Validation: `C:\Python313\python.exe -B -m unittest discover -q` — **120 run,
119 passed, 1 skipped** (absent `lox/image (1).jpg`). Regression checks change raw
camera frames while tracking is off, prove no new analysis or camera/session
switch, hold overlays, check paused export validity, re-enable/reacquire, exercise
fullscreen and repeatedly alternate complete/empty/blurred detection messages
while asserting identical control positions and regular-screen layout fit.
All prior pupil, numeric radius, camera ownership, stale-result, options and
tracking tests remain. Native-photo audit/guide renders remain current; source
photos and user options were not changed.

Remaining optical limitations/next work are unchanged: validate identities and
advice on labelled real views, calibrate camera geometry/uncertainty/screw response,
then integrate a tested model. No simulator, physical screw instructions or
calibrated alignment verdict exists yet.

## Previous checkpoint: pupil and exact radii

## Current: optional marks, reflected camera pupil and exact pixel radii

Latest requests: center marks may be absent, analyze the camera pupil, and allow
one-pixel size changes plus direct numeric entry. The plan was recorded before
code in DETECTION_IMPROVEMENTS.md. The brief camera-selection report was withdrawn
by the user; no camera behavior changes were made for that report.

- Five direct color-coded roles: Focuser, Secondary, Primary, Mark and Pupil.
  Camera pupil is red; mark stays purple. All displayed circles are round and
  share the focuser/largest-boundary master center. Raw observations remain
  independent for guidance and export. No confirmation/dropdown flow returned.
- Setup gains center-mark None. None/Unknown makes the mark optional; specified
  Ring/Spot/Triangle requires it. None suppresses automatic mark proposals.
  Progress counts required roles, normally three rims plus pupil (4), or 5 with
  a specified mark shape. Missing required references prompt acquisition/picking
  before adjustment recommendations. An explicit manual mark can still be used.
- The pupil heuristic finds a small round opening nested inside a larger dark
  central reflection. Size/centering/contrast/containment support is required;
  the whole shadow and a lone dot are rejected. A pupil ID is never reused as the
  mark. Round lens details remain available for Triangle profiles. Identification
  remains heuristic. post-333184's former mark is now correctly proposed as pupil.
- Pupil manual three-point circles, outline replacement, raw JSON export and
  matching/hold/reacquisition use the existing tracking pipeline. Missing/soft
  pupils prompt focus/illumination or picking. Manual references retain radius
  and follow the master when a good replacement is absent.
- Guidance includes raw pupil offsets from focuser and primary reference. After
  camera/secondary acquisition checks and placement/aiming, pupil displacement
  gives conditional primary-tilt screen direction toward mark or approximate
  raw primary rim center. Without a mark, uncertainty is widened and advice says
  approximate. A plain pupil is not a calibrated Cheshire ring. Always request
  optical/star verification; no screw turns, mechanical squaring or success verdict.
- Radius (px) entry accepts whole raw-image radii. Enter/focus loss applies;
  Escape cancels. +/- and Ctrl+wheel use one pixel per step, no percentages.
  Radius changes keep the center and other sizes, clear fit evidence and enter
  manual_resize retention. Tracking pauses while typing; stale analysis is
  rejected. Escape/gestures preserve deliberate tracking pause. Detect resets edits.
- Five buttons fit in two rows, with selected-role entry/button colors. Existing
  12-display-pixel hover, empty-space left pan, blink hold/release and Reset persist.

Validation: `C:\Python313\python.exe -B -m unittest discover -q` — **118 run,
117 passed, 1 skipped** (absent `lox/image (1).jpg`), 56.8 seconds. New checks cover
no-mark persistence, nested pupil/mark/shadow separation and raw scaling, native
photo identity, pupil hold/recovery, optional/known-mark guidance, raw offsets
despite shared guides, approximate advice, exact entry/pixel steps, invalid input,
typing/pause races, manual pupil/export, and layouts. Existing camera tests pass.
The 14-photo audit and overlay contact sheet were refreshed; heuristic coverage
is not labelled optical ground truth. Source photos/options unchanged. No commits
or Git operations; no runtime network calls or downloaded models.

Next: label real pupil/mark/mirror identities and validate advice on a telescope;
calibrate camera seating/orientation, uncertainty and reflected-reference geometry.
Closely merged rims, reflections and pupil/mark overlap remain ambiguous. Current
pupil support is geometric/appearance-based, not a probability or optical verdict.
Profile dimensions remain saved but are not used to infer millimeters. Screw
response calibration and a tested integrated forward model remain future work.

## Previous checkpoint: direct circle controls

## Current: direct circle sizing, hover feedback, colored controls, tight focuser

Latest report: need smaller circles, move cursor near rims with forgiving grabs,
empty-image drag to pan, color correspondence on controls, and automatic assignment
of the clean outer rim in post-333184. Plan recorded before code at the end of
DETECTION_IMPROVEMENTS.md. Previous tracking/advice behavior remains current.

- Click any named circle, then −/+ beside Change outline to change only its radius.
  Wheel over these size controls also works. Ctrl+wheel near a circle resizes it;
  successive events at the same position keep that role as its rim shifts. Ordinary
  wheel keeps cursor-based image zoom. The common center and other radii stay fixed.
- Size edits record manual_resize circular geometry at the original measured
  center, clear fit/shape evidence and enter manual tracking retention. A good
  later fit may replace it; otherwise radius is held with master-center motion.
  Explicit Detect resets overrides. Capture export includes the edited reference.
- Hover within 12 display pixels of a visible rim or center shows the move cursor.
  Hit testing remains available while live analysis runs; a gesture invalidates
  old results. Picking uses crosshair; blink/hidden overlays cannot be grabbed.
  Empty-space left drag pans; no dropdown or pixel-precise hit is needed.
- Role buttons have guide-color swatches and readable text in matching hues.
  Selected size controls match the role. The edit toolbar stays in the existing
  Change outline row, retaining 1280x720 and 1024x768 layout fit.
- The reported outer rim was detected at radius ~145 but the 1.3 ratio role gate
  rejected it around primary radius ~126. Tight high-quality nearly round outer
  rims now qualify above 1.08 with distinct separation/support; circular pixel
  verification remains. The photo now gets focuser/primary/mark automatically;
  secondary remains missing. Thin primary rim sides are still not a focuser.

Validation: 105 tests run, 104 passed, one absent-local-photo skip. Added checks
cover the reported native photo, tight synthetic rings versus thin rim sides,
12-pixel hover during analysis and high zoom, hidden-overlay grabs, empty pan, sizing,
repeated Ctrl+wheel versus zoom, export/manual hold/reset, colors and compact layout.
DETECTION_VALIDATION.json and DETECTION_OVERLAYS.png refresh all 14 current native
photos. Their heuristic role coverage is not labelled optical ground truth.
No commits/Git operations, runtime network calls, options or source-photo changes.

Remaining next work stays optical: labelled roles and uncertainty, reflected
primary reference, camera orientation/geometry and measured screw responses before
calibrated mechanical focuser/primary recommendations or an integrated model.

## Previous checkpoint — automatic tracking and advice

## Current: automatic circles, live tracking and provisional next-action advice

Latest authorized flow: Detect draws usable circles immediately, with no confirm
step. Users add missing circles manually; live tracking follows mirror changes,
retaining manual circles when no reliable replacement exists. Missing references
request better illumination/focus/field. With all four present, advise from the
actual measured geometry. Runtime offline, Newtonian only, **no Git operations**.

- Public analyze_frame returns full round concentric guides plus separate original
  observations. Focuser is master; absent focuser, largest boundary supplies center.
  Dragging one moves all. No eccentricity option or independently movable guides.
- Direct role buttons/circle clicks replace dropdowns. One visible outline per
  role; Change outline cycles alternatives. No Confirm action or exported list.
- Detect starts enabled live tracking (350 ms minimum interval, one worker/latest
  frame), or analyzes a static image. Result/frame snapshots remain paired for
  display/export. Picking/gestures freeze updates and invalidate inflight results;
  disabling tracking freezes the current analyzed image.
- edge_tracking.py matches manual roles by quality, kind, size and proximity.
  Unmatched manual references retain radius and move with the master. Provenance
  manual_hold prevents advice based on stale geometry. Good later fits reacquire.
  Explicit Detect resets manual overrides and group offset. Source changes reset
  state. Recovered manual roles remain managed so later loss can retain them.
- Manual secondary/mark picks preserve master center and store their actual raw
  positions separately. Picking the focuser sets the master; no focuser plus a
  larger new boundary can establish a replacement master.
- collimation_guidance.py uses raw observations for capture/camera seating,
  secondary shape/placement and secondary tilt instructions in image coordinates.
  It rejects stale, soft, incomplete or unmeasured evidence. Guidance is conditional
  and pixel-based, not a physical tolerance or proof of alignment.
- Primary tilt still needs a reflected pupil/Cheshire reference, which is not one
  of the four identified roles. The app requests that check and star verification;
  it does not infer screw turns, mechanical focuser squaring or a success verdict.
  No forward/inverse simulator has been ported yet. Profile dimensions are saved
  but current image heuristics do not convert them into physical error estimates.
- Raw PNG/JSON export includes observations, guides/master, manual references,
  tracking state/offset and advice. JSON is not automatically restored on import.

Plan was documented before code in DETECTION_IMPROVEMENTS.md. Current README and
DESIGN describe the superseding flow. Older checkpoints below are historical.

Validation: `C:\Python313\python.exe -B -m unittest discover -q`: **100 run,
99 passed, 1 skipped** (local `lox/image (1).jpg` absent), 41.6 seconds. Includes
40 Tk/camera/interaction tests, 16 pure tracking/advice tests, round guide/master
checks and independent observation/photo regressions. New live checks verify
matching analyzed/exported frames, manual hold/reacquisition, pause/pick races and
single-worker scheduling. Tk cleanup remains main-thread only. The current audit
records 14 decodable photos; source photos/options remain unchanged.
Visually inspected overlays are saved in [DETECTION_OVERLAYS.png](DETECTION_OVERLAYS.png).

Next work: label real images by optical role, quantify uncertainty and validate
advice on a telescope. Merged secondary rims and reflected camera/mark details can
still be misidentified. Manual three-point circles cannot measure shape distortion.
Restart Detect after changing camera resolution; retained manual references are
not calibrated for an in-session resolution change. Add camera orientation,
reflected-reference recognition and small adjustment calibration before porting
forward-model geometry for reliable mechanical/screw guidance.

## Historical checkpoint — 2026-10-05

## Current checkpoint: independent recognition and native-photo audit

Latest user report: none of the images appeared to have recognized elements.
The documented plan is at the end of DETECTION_IMPROVEMENTS.md. The complete-chain
role gate was a concrete cause: a missing/soft/closely spaced rim erased all roles.

- The primary is now anchored by raw face appearance, radial consistency and a
  central dark obstruction, with nested layers as fallback. An outward-darkening
  transition refines its rim. Brightness acceptance is relative to the capture.
- Roles are proposed independently; missing references do not suppress others.
  Circular focuser verification retains soft measurable estimates with focus
  advice, and an anchored circular search recovers some incomplete outer rims.
- Bounded secondary contour windows require refined nesting, rim separation,
  angular coverage and support away from primary/focuser before a suggestion is
  shown. This recovers the displaced secondary in the native annotated photo.
  It does not guarantee identity or hidden-rim accuracy.
- Advice reports how many references were found and gives short focus/field or
  missing-secondary instructions, without scrolling. One outline per element,
  confirmation, blink, panning, dragging/reset and Detect reacquisition persist.
- DETECTION_VALIDATION.json records all 15 native photos with Ring/eccentricity
  0.55/max dimension 960, raw geometry, missing roles and single-run timings.
  All yield at least a primary suggestion (91–372 ms); this is recognition
  coverage, not calibrated complete identification. Source images/options stayed
  unchanged. The six main native overlays were rendered and visually inspected.

Validation: **75 tests pass**, `C:\Python313\python.exe -B -m unittest discover -q`
(19.8 seconds). New checks cover missing-secondary independence, dark reflected
pupil rejection as a secondary, dim captures, displaced annotated secondary
geometry, soft focuser preservation, uncertain blurred-secondary rejection,
small partial focuser recovery, and raw-coordinate scaling without forcing an
unsupported secondary. Existing camera/UI/layout/blink/export tests pass.
No commits or Git operations; no runtime network calls added.

Remaining limitations: merged secondary rims are still unresolved in some
photos. Upscaling/resampling the annotated partial secondary can leave it missing;
primary/focuser remain mapped correctly and a nearby rim side must not be forced
into that role. Center marks can resemble reflected peepholes/collimator details.
For 2.png, the current evidence supports primary/mark suggestions, not a separate
focuser/secondary identity. The blurred post-474648 photo supports focuser/primary,
with secondary missing. Next work should use labelled roles, measurement uncertainty
and the integrated forward model. There is still no optical verdict or screw
recommendation. Do not keep loosening free ellipse support to manufacture completeness.

## Previous checkpoint: one named outline per element and press/release blink

User correction: raw detector candidates are confusing; show one per optical
reference and explain how the information is used. Blink must hide on right press
and restore on release. The plan was documented first in DETECTION_IMPROVEMENTS.md.

- Normal overlays show only assigned focuser, secondary, primary reflection and
  center mark, labelled by name (at most four). Raw hypotheses, including alternate
  rim sides/reflection details, remain internal/exported. They are not optical
  identities. Missing roles are explicit; no arbitrary identity is invented.
- Raw selection is hidden behind Change outline for the current element. Each
  choice replaces that element’s one visible outline; the all-candidate checkbox
  was removed. Kind filtering separates mark choices from boundary choices.
- Missing/check/checked states, a next-step prompt and Confirm outline and next
  guide the user through identification. Confirmation advances to the first
  unchecked reference. Corrections still reset confirmation. Completed review
  offers a baseline capture and live reacquisition after a telescope adjustment.
- Checked centers are shown relative to the focuser in raw image pixels with
  +right/+down signs. This describes image geometry for comparing captures; no
  calibrated optical error, alignment verdict or screw direction is inferred.
- Right press sets transient blink_active; release clears it. It does not change
  the persistent Show overlays setting. Root release/focus-loss handlers restore
  visibility if the cursor leaves the image. Picks/references/view remain intact.
- Analysis worker closures capture only raw data and their result queue, not the
  Tk app. GUI tests retire closed window cycles on the main thread after joining
  workers, preventing Tk variable destruction from worker-triggered garbage
  collection across the many test windows.

Validation: **66 checks pass**, `C:\Python313\python.exe -B -m unittest discover -q`
(20.2 seconds). The new checks verify extra hypotheses do not change rendered
normal overlays, one replacement per named role, hidden/explicit alternatives,
guided confirmation, missing-state prompts, signed image offsets, fully visible
completed-review text at 1280×720 and 1024×768, momentary blink pixel restoration,
release outside the image, and restoration of a previously disabled Show overlays
preference. Previous camera, dragging, redetection, circular focuser, profile,
raw export and local-photo tests pass. No commits or Git operations.

Remaining next work is labelled real-image validation and an integrated calibrated
model that can explain optical adjustments. Current information supports checking
boundaries and comparing image positions; screw advice is not implemented.
The checkpoints below retain previous behavior as history.


## Previous interaction checkpoint: blink, reset, circle movement, circular focuser

- Reset view is above the tabs and also bound to Ctrl+0; it preserves references.
- Right-click toggles all overlays for a blink test, preserving zoom, pan, reference
  data, confirmation, and unfinished picks. Show overlays controls the same state.
  Right-button pan/double-click reset were removed. Middle drag still always pans.
- Left drag grabs a visible rim/center, or pans empty space. Picking mode disables
  reference grabbing. The 5-pixel threshold keeps clicks distinct from drags.
  Shared-center manual guides move together; detected references move independently.
- Moved references become `manual_drag`, lose automatic evidence/role proposals and
  confirmation, and retain original geometry/cumulative raw translation in exported
  `manual_adjustments`. Three-click points translate with their reference. Detect
  clears edits, ends gestures, restores overlays and automatically fits raw pixels.
- Detected lines are 1 px (2 for selected rims), with a 1-pixel wider black halo.
  Center markers/pick markers are thinner too; label placement remains unchanged.
- Additional user instruction: the focuser must always be round. Automatic focuser
  proposals use a least-squares circle followed by circular evidence/refinement.
  Unverifiable/soft circles are not assigned. Manually assigning an ellipse to the
  focuser produces a labelled `focuser_circle_estimate` with equal axes, no inherited
  fit score, and original-geometry metadata. Its missing arcs are extrapolated with
  finer, dimmer dashes even after confirmation. Other missing rims stay blank.
  Mirror-edge eccentricity remains configurable for the other rim candidates.

Validation: **64 checks pass** (`C:\Python313\python.exe -B -m unittest discover -q`,
16.2 seconds). New checks exercise blink pixel restoration with unfinished picks,
independent raw-coordinate dragging after zoom/pan, cumulative exported translation,
Detect replacing manual geometry, shared-center guide dragging, global reset across
all tabs, constrained/partial focuser circles, inferred dashes after confirmation,
and manually assigned circular estimates. Regular-screen layout and all previous
camera/profile/review regressions pass. No commits or Git operations.

Remaining limitations: extrapolation is a geometric estimate, not observed rim
support or an optical identity guarantee. Manual assignment still requires review.
Simulation-based diagnosis and screw instructions remain future work. The earlier
checkpoint below records the previous rendering/navigation behavior.


## Previous follow-up: roundness, unsupported fits, advice, and panning

Recorded before implementation in `DETECTION_IMPROVEMENTS.md`, following six more
user screenshots. No commits or Git operations. Runtime remains entirely offline.

- `max_eccentricity` is saved in the integrated setup dialog, default 0.55, valid
  0–0.85. Existing schema-1 options get the default without altering their file.
  e = sqrt(1 - (minor/major)^2); one analysis pixel of axis mismatch is tolerated.
  Snapshot the option for worker analysis and reject invalid/nonfinite settings.
- Final/refined rims enforce roundness plus at least 65% evidence for interior
  shapes, 48% for visibly clipped shapes, across three quadrants. A bright-face
  seed after closing narrow spider gaps improves divided-mirror views. The joined
  image never supplies evidence. Ghost fits in the supplied examples are reduced.
- Colored strokes are 2 px, selected 3 px, halos 2 px wider. Smaller labels seek
  separate positions. Automatic overlays show supported arcs only: missing arcs
  stay blank after confirmation. Manual circles remain explicit fitted references.
- Capture advice uses a fully wrapped label with no scrolling. Focus and missing
  camera field are the priority actions; full engine messages remain in exports.
  Sidebar width is stable so status changes cannot shift the viewport.
- Left drag pans after zooming; left-click places guides/picks edges on release.
  A 5-pixel threshold separates drag from click; dragging never adds a pick.
  Right/middle drag remains available; wheel zoom anchors to the cursor. Reset view
  and right double-click return to the full image. Crops clamp to image bounds.
  `DisplayTransform`, `prepare_frame`, overlays and manual picking share the crop.
  Manual shared-center guides follow movement/scale. Raw images and measured
  coordinates never change when navigating. Opening another image resets the view.

Validation: `C:\Python313\python.exe -B -m unittest discover -q` — **58 checks pass**
(11.4 seconds), including four optional local-photo checks. Added saved-limit and
backward-compatibility tests, stretched/short-arc negatives, missing-arc drawing,
pan/clamp/cursor zoom/reset/manual-pick checks, left-click versus drag gesture
checks, and no-scroll blur advice layout at
1280×720 and 1024×768. Camera regressions remain covered. Rendered the six example
overlays for visual inspection; `lox` images were read and not modified. Timings
and example outcomes are in `DETECTION_IMPROVEMENTS.md`.

`images.jpg` now proposes the main focuser/secondary/primary rims instead of two
misplaced lower ellipses. The small dark-tube and orange examples lose the stretched
artifacts. The annotated view and central circular reflection details still need
manual identification. Very faint interior rims may now be conservatively omitted;
the eccentricity option must not imply optical identity or calibrated accuracy.

Next: labelled raw-image validation and a guided acquisition/confirmation flow,
then integrate calibrated model comparison into this same app to explain which
component to adjust. No simulation-based diagnosis or screw directions exist yet.
The earlier checkpoints below are retained as historical context.


## Earlier checkpoint: real-image detection and visibility

User feedback: the old thin gray overlays were hard to see, and requiring nearly
complete contours missed blurry, clipped, or interrupted rims. Source examples
are now available locally in `lox`. They were read and not modified.

The plan was recorded first in `docs/DETECTION_IMPROVEMENTS.md`. Implemented:

- Radial-gradient and contour-arc ellipse hypotheses supplement complete contours.
  Independent evidence checks use distributed support, gradient normals, smooth
  contrast changes, and transition prominence; weaker mixed-rim fits are suppressed.
- Partial/clipped fits retain support bins, transition widths, and residual offsets.
  Their inferred sections remain dashed even after role confirmation.
- Bright 3-pixel outlines with black halos, readable labels, stronger center marks,
  and a 5-pixel selected outline replace thin gray candidates.
- Candidate counts remain visible when role association fails. Feature-specific
  review hints explain actual secondary vs dark reflection and mark vs camera pupil.
- Focus advice for broad transitions; missing/incomplete focuser identification
  suggests zooming out, repositioning, or a wider-view camera if the rim is absent.
- A fixed-height scrolling advice area keeps long messages within regular screens.

Validation at that checkpoint: `C:\Python313\python.exe -B -m unittest -q` — **48 checks pass**,
including two optional tests using existing local photos. Geometry tests now cover
interrupted rims, clipped geometry estimates, faint contrast, moderate/excessive
blur, negative noise/straight lines, and bright selected/unassigned overlays.
Existing camera, options, frozen review, and screen-layout checks still pass.

Local example observations (three runs each, medians before the final residual
metadata-only addition): `image.jpg` 319 ms, annotated secondary example 192 ms,
orange-primary example 214 ms. All processing remains on the analysis worker.
The first now proposes three main rims (approximate radii 508/298/210 raw pixels).
The annotated secondary view still requires manual secondary identification.
The soft orange-primary view retains partial candidates and asks for better focus
and a wider camera view rather than confidently assigning three optical roles.
These are visual-regression checks, not calibrated measurement accuracy.

Current next task remains reliable feature confirmation/acquisition, followed by
model comparison integrated into this app. The user explicitly wants later
recommendations about which optical component to move. Calibrate camera geometry
and screw response before mapping those recommendations to directions/turns.
No commits or Git operations were performed.

The original first-slice checkpoint below is retained as historical context.

## Scope and persistent decisions

- Newtonian focuser views only; all runtime work must be completely offline.
- Telescope parameters belong in integrated setup/options and are saved locally.
- Build one coherent collimation assistant; selectively port model geometry only
  when it helps explain measured errors or predict useful adjustments.
- No commits, staging, initialization, or other Git operations. User handles Git.
- Keep camera controls compact, scrollable, and capability-aware. Hide camera
  reported-value acknowledgement messages.
- Do not mistake the reflected dark secondary silhouette for its actual edge or
  force it to be concentric. Three outlines alone do not establish primary alignment.

## Documentation before implementation

`docs/DESIGN.md`, this checkpoint, and `README.md` were created before detector
code. The baseline had manual guides/camera controls and 22 passing checks.
The design records the product direction, detection contract, architecture,
saved setup, future model integration, and required validation.

## Completed first slice

- `app_options.py`: optional validated telescope dimensions, derived focal ratio,
  versioned local JSON, atomic saving, no assumed telescope model/dimensions.
- `setup_dialog.py`: integrated setup editor; validation errors leave it open;
  cancel preserves settings; saved parameters reload at app startup.
- `feature_detection.py`: offline contour/ellipse candidates and round/triangle
  marks, duplicate merging, geometric fit/coverage measures, nested-role suggestions,
  original image coordinates, three-point circle fitting, shared display transform.
- `collimation_review.py`: frozen raw-frame analysis on a separate worker; tagged
  results reject stale camera/image/profile analyses. Explicit candidate assignment,
  confirmation, clearing, three-click edge correction, one-click center mark.
- Existing camera worker gains a close command for imported images. Camera stays
  on its owner thread; no worker accesses Tkinter. A disconnected camera does not
  discard a frozen review image. Analysis failures retain the image for correction.
- Offline image import, including Unicode paths; raw PNG and JSON capture export.
  Metadata includes setup, geometric candidates, roles, confirmations, and manual points.
- Three compact tabs: Detect & review, Manual guides, Camera. Display adapts to
  available window space. Manual shared-center guides stay separate from measured
  independent centers and temporarily hide during review.
- `requirements.txt` explicitly includes NumPy. Local options/temp saves are
  ignored by `.gitignore`; tests inject temporary paths and do not touch user options.

The forward simulator was not ported in this slice: it cannot identify optical
features in an image. There is no automatic optical diagnosis, calibrated
millimeter error, collimation-success verdict, or screw-adjustment guidance yet.

## Validation completed

Environment: Windows, `C:\Python313\python.exe`, Python 3.13.

Command: `C:\Python313\python.exe -B -m unittest -q`

Result: **41 checks pass** (about 5 seconds). Coverage includes:

- Off-center circular and elliptical boundaries; full-resolution coordinates
  after downsampling; triangle/round marks; duplicate rims; moderate noise/blur.
- Blank, random noise, missing edges, clipped rims, invalid image input.
- Three-click geometry validation and exact crop/scale coordinate round trips.
- Actual Tkinter callbacks with synthetic cameras, frozen review, explicit
  confirmation, manual clicks at digital zoom, stale analysis rejection, errors.
- Raw image/metadata export, Unicode paths, saved options loading, corrupted
  settings preservation, setup validation/cancel, failed atomic replacement.
- Controls and aspect-preserving image fit at 1280×720 and 1024×768.
- Original camera capabilities, ranges, debounce, switching, release, errors,
  disconnect, main-thread rendering, and manual-guide behavior.

An overlay PNG was rendered and visually inspected from the synthetic fixture.
No physical telescope images or real adjustment sequences were supplied.

Local timing, eight runs per synthetic input, median/max analysis milliseconds:

| Source size | Median | Max | Candidates |
| --- | ---: | ---: | ---: |
| 800×600 | 8.6 | 19.4 | 4 |
| 1920×1080 | 9.1 | 10.5 | 4 |
| 3840×2160 | 9.5 | 10.4 | 4 |

A 960×960 random-noise image took 367.8 ms, produced mark-like candidates, and
suggested no optical roles. Timings are local synthetic observations, not a field
performance guarantee. Processing downsamples to a 960-pixel longest side.

## Known limitations

Detector thresholds are documented in DESIGN.md. Nesting and fit quality cannot
prove identity; a non-telescope image can contain plausible nested objects.
Spider vanes, touching outlines, glare, severe misalignment, clipped rims, and
camera perspective may defeat automatic detection. Missing edges require better
capture or manual correction. Three-point correction fits circles only. Center
mark identity is reviewed by the user; ring and spot use the same round path.

Export is an image/JSON pair, not an atomic pair transaction. Metadata restoration
is not implemented; reopen a saved raw PNG and detect again. Options currently
live beside the source, not in a packaged per-user application directory. Only
one saved telescope profile is supported. An offline distributable installer is
not built; dependencies must already be installed or supplied as offline wheels.

## Next development sequence

1. Collect real raw focuser images and manually label actual optical edges, mark,
   and usable/ambiguous views. Add regression fixtures with permission. Evaluate
   center/radius errors and false role suggestions before tuning thresholds.
2. Build a setup/acquisition wizard integrated into these same controls: mount
   and center camera, illuminate/focus, check usable view, verify reference
   identities, and explain the next measurement required. Test with beginners.
3. Identify a trustworthy primary-alignment reference (appropriate Cheshire or
   equivalent) and camera geometry. Preserve uncertainty; a single image may
   have several mechanical explanations.
4. Extract selected forward geometry from astro-toolbox into a native Python
   module, parameterized by this saved profile. Remove DOM/default-BKP130
   assumptions, check licensing, and test numerical parity against known cases.
   Use it to explain measured changes and show expected offsets in this app.
5. Calibrate real screws and camera orientation using before/after responses to
   known small adjustments. Then recommend one adjustment, reacquire, and verify
   improvement. Do not infer turn counts from the toolbox's displacement units.

These are continuation plans, not implemented capabilities or a new authorization
to make commits. Start from this checkpoint; do not redo the first slice.

## Data needed from the user for reliable field validation

Raw frames without overlays, preferably an independently checked aligned
reference plus misaligned examples; the saved telescope profile; camera/lens and
mounting information; camera orientation/handedness; adjustment/locking screw
photos and labels; before/after captures for documented small adjustments.

## Toolbox findings retained for later

Source: https://github.com/Borschtsch/astro-toolbox/tree/main/collimation

The JS forward model has `threeScrewFit`, `geometry`, `reflectPoint`, `pmImage`,
`project`, and `build`, with secondary placement/rotation/tilt, primary tilt, and
reflection layers. `alignedNow` compares known simulated poses; it is not an
inverse photograph solver. Some dimensions are estimated and primary imaging
is approximate. Some geometry reads a DOM option directly and needs separation.
Its screw controls encode displacement rather than calibrated actual turns.
No toolbox code was copied into this slice.

Source double-click implementation completed: start.py delegates to
source/bootstrap.py, selecting .venv when present and pythonw for Windows GUI
startup. start.cmd calls the same entry without depending on .py associations.
CLI arguments, version reporting and frozen startup remain functional. Startup
failures log a traceback and Windows GUI failures show a message. No registry
association changes, dependency downloads/installations or Git operations.

Validation: all 57 integration scenarios passed (178.231 s). Three new real-launch
workflows use isolated Unicode/spaced source copies and offline-created venvs;
the fixture exposes the test runner's installed packages through a .pth file,
so it also supports a Linux runner whose dependencies live only in a venv.
The Windows Explorer scenario explicitly skips on Linux. No unit classes ran,
previous assertions remain and historical coverage gaps are still documented.

A fresh build under dist/startup-validation passed source, frozen and relocated
archive smoke checks. Existing release folders were preserved. Evidence is in
docs/STARTUP_VALIDATION.json; the rebuilt archive is
 dist/startup-validation/AstroCollimator-0.1.0-windows-x64.zip.
Normal GUI startup uses the same windowed bootstrap branch exercised by the
hidden --windowed --smoke-test workflow. Documentation now explains double-click
startup and the start.cmd fallback. Native Linux validation remains pending VM.

Direct startup correction completed: start.cmd removed; source/bootstrap.py no
longer selects .venv, pythonw or a child process. It calls the shared launcher in
the interpreter invoked by the caller/Explorer and retains readable errors/logs.
The three launcher integration scenarios were updated to this explicit user
preference and passed (3.300 s). The Explorer case deliberately includes an empty
local .venv and proves it is ignored while the associated Python completes real
Tk/setup/detection/export. Explicit venv invocation and missing-dependency
failures remain covered. No production Tk/application functions are mocked.

The actual reported normal-start failure is not reproduced here. The user's
observed behavior/error and whether setup.py means the existing start.py are
pending clarification. Do not claim that an unidentified root cause was fixed.
Earlier startup package/test evidence remains historical; no release was rebuilt
for this direct-interpreter correction. No commits or association changes.

## Central guide crosshair visibility — 2026-10-07

Plan: draw the FOV crosshair before optical guides so the central marker stays
above it. Increase the shared-center white marker from 1 to 2 pixels, with a
matching black outline. Preserve independent candidate markers, FOV controls,
blink behavior and raw exports. Verify overlap through actual Tk rendering in
an integration scenario; no unit tests or commits.

Completed: the independent FOV crosshair is rendered first, then optical guides
and the central marker. The shared-center marker now uses a 2-pixel white stroke
and 3-pixel black outline; independent candidate markers retain their previous
width. Five targeted application integration scenarios passed (9.850 s): central
overlap/thickness, FOV visibility, FOV dragging, hold-right blink and raw export.
The overlap check inspects actual Tk-rendered pixels and waits for the FOV redraw.
No prior assertions were removed. No unit tests or commits; no release rebuild
was needed for this display-only change. Linux native validation remains pending.

## Explorer console visibility and interpreter errors — 2026-10-07

Plan: hide only a dedicated Windows launch console (the application and optional
Python file launcher), preserving consoles shared with a terminal. Keep the same
associated Python process, with no CMD file or interpreter restart. Include the
full interpreter location/version in startup logs and the location in error
messages. Validate through the real Explorer association and startup/error app
workflows; no unit tests or commits.

Completed: Windows source GUI startup hides only the dedicated console before
loading GUI dependencies, using native console process ownership and SW_HIDE.
A shared terminal is preserved; no interpreter switch, process restart, CMD file
or association change was introduced. Startup messages identify the interpreter;
UTF-8 error logs include its full location, Python version and traceback. Smoke
reports retain their existing interpreter field and now record native console
visibility on Windows.

Validation: four targeted actual source/Explorer/shared-console/dependency-failure
workflows passed (5.030 s). The prescribed command
`C:\Python313\python.exe -B scripts/test_integration.py` then passed all
59 integration scenarios in 176.255 s. This includes the thicker central
crosshair change. No historical assertions were removed or unit tests run.
The Unicode-path failure scenario explicitly requests UTF-8 terminal output;
production file logs are always UTF-8. Evidence: DIRECT_STARTUP_VALIDATION.json.

Limitations: Windows may allocate/show a console briefly before Python executes.
Windows Terminal pseudoconsole window hiding remains unvalidated and is not
claimed. Native Linux desktop/camera/release validation and the historical
coverage-equivalence gaps remain pending. Existing packaged releases were not
rebuilt for these source-launch changes. No commits or other Git operations.

## Opened-image mouse navigation — 2026-10-08

Plan: reproduce opened-image wheel/left-drag events through actual Tk widgets,
restore panning from the black image margin, preserve optical/FOV drag targets,
Control-wheel radius edits, reset and raw geometry. Tk 9.0.4 on Windows reports
symbolic Button-4/5 events as button numbers 8/9, which the current wheel helper
ignores; normalize these only on Windows/Aqua Tk 9. Ordinary MouseWheel zoom and
inside-image drag passed the focused reproduction, so this does not yet establish
the exact cause of the user's reported wheel failure. Ask for launch/event details
while checking a real file-open workflow. No Git operations or unit tests.

Validation environment changed: C:\Python313\python.exe is no longer present.
The project .venv now uses Python 3.14.8/Tk 9.0.4. Tk initialization initially fails
because Tcl's installed libraries are ZIPs and this test process cannot locate
init.tcl. For validation only, extract those existing local libraries under
build/gui-validation/tcl and pass TCL_LIBRARY/TK_LIBRARY to child processes.
Do not alter the user's interpreter installation or app environment selection.

Completed: begin_pan now accepts the entire image widget, including letterbox
margins; circle/FOV hit testing remains bounded to visible image geometry. Pan
remains limited to the source crop, so zoom in first when the whole image fits.
wheel_direction normalizes Tk 9 Windows/Aqua symbolic Button-4/5 numbers 8/9;
X11 physical buttons 8/9 are not treated as vertical wheel input. Normal wheel
zoom, Control-wheel circle sizing and reset behavior remain intact.

The new file-open integration scenario opens/detects/exports an actual image,
zooms only through widget events, drags from the black margin, verifies crop
movement with unchanged detection/raw pixels, and resets through the button.
Five focused navigation/editing workflows passed in 10.642 s.

Prescribed validation: .venv/Scripts/python.exe -B scripts/test_integration.py,
with the local extracted Tcl/Tk library environment described above. Of 60
integration scenarios, 59 passed (177.263 s); the Explorer association case
failed at os.startfile with PermissionError [WinError 5] Access is denied for
its temporary source copy, before application startup. No app assertion in
that workflow ran, and it was not skipped or weakened. All navigation, camera,
tracking, detection, rendering, persistence/export and other source-launch cases
passed. Log: build/gui-validation/navigation-integration.log. Native Explorer
association validation therefore remains a current environment gap; the earlier
2026-10-07 passing result applies only to that earlier environment. This was an
OS launch denial, not an automatic approval-review rejection.

The precise user-reported wheel failure remains unconfirmed: ordinary MouseWheel
and in-image panning already passed the initial reproduction, whereas margin
panning and Tk 9 symbolic wheel inputs were reproducibly broken and corrected.
User confirmed an opened image but did not specify source versus packaged launch.
Existing portable binaries were not rebuilt. Restart the updated source app to
use these changes. No unit tests, assertion removals, commits or Git operations.
Historical coverage-equivalence gaps and native Linux VM checks remain pending.

## High-resolution wheel zoom — 2026-10-08

Plan: handle TouchpadScroll in the shared wheel binder when Tk exposes
::tk::PreciseScrollDeltas. Decode the vertical signed delta instead of treating
the packed X/Y value as a simple direction. Keep ordinary MouseWheel/X11 wheel
paths, Control-wheel circle editing and camera controls. Zoom proportionally
for fine Windows deltas so a 30-unit packet is a quarter of a 120-unit wheel step.
Verify native WM_MOUSEWHEEL delivery to an actual visible production window,
including sidebar focus, both signs and unchanged raw/guide geometry; no unit
checks, Git operations or runtime network dependency.

Reproduced before edits: Python 3.14.8/Tk 9.0.4 turns a native Windows wheel packet
with delta 30 into TouchpadScroll delivered to the video label. Zoom remains 1.0
regardless of whether focus is on the label, camera entry or root. The app only
binds MouseWheel/Button-4/5. Earlier generated MouseWheel checks missed this path.
Reference: https://core.tcl-lang.org/tips/doc/main/tip/684.md and
https://core.tcl-lang.org/tk/tktview/7a17cfd1b55980aa2bfbaf521600d95b12551432.

Completed: bind_wheel conditionally registers TouchpadScroll using Tk's available
PreciseScrollDeltas decoder. It forwards the signed vertical component and keeps
horizontal-only movement from changing zoom or controls. Windows precise zoom
uses delta / 120 for immediate fine increments; ordinary mouse wheels retain
0.1 steps. Circle Control-scroll and other controls reuse the normalized events.

Evidence: before the patch an actual native 30-unit Windows packet reached the
image as TouchpadScroll without changing zoom. After the patch the same packet
changes zoom by 0.025 with image, camera-entry or root focus. The committed-to-file
integration workflow checks both signs at 30/120, actual rendered crop changes,
sidebar focus, horizontal rejection and preserved raw/optical geometry. A second
actual app workflow checks packed axes, Control-scroll sizing and raw export.
These are integration scenarios, not component/unit tests; Windows routing APIs
and Tk event conversion are not mocked. They explicitly skip on runtimes without
precise scroll support, and the native Windows workflow skips on Linux.

Validation: four focused workflows passed (8.799 s). The prescribed full runner
(.venv/Scripts/python.exe -B scripts/test_integration.py with the existing
validation-only Tcl/Tk environment) ran 62 scenarios in 184.673 s: 61 passed,
one Explorer startup scenario failed at os.startfile with the same Windows
PermissionError [WinError 5] before app execution. No skipped cases in this run;
all native-wheel, image, camera and other app assertions passed. Full log:
build/gui-validation/precise-wheel-integration.log. No assertion was removed or
weakened. No Git operations, unit tests or interpreter-install changes.

The previous fix missed the separate high-resolution event type; this patch
addresses a reproduced native input failure. User confirmed start.py with no wheel response, so the updated source entry is
the relevant launch path. Changes require restarting the app; existing portable
binaries were not rebuilt. Native Linux GUI/hardware validation and
historical coverage-equivalence gaps remain pending.

## Touchpad field diagnosis — 2026-10-08

User reports only circles change without physically holding Ctrl. More precisely,
horizontal two-finger scrolling changes circles; vertical two-finger scrolling
does nothing. Physical mouse is untested. This conflicts with the tested source
handler (vertical precise input zooms, horizontal input does not). Do not declare
another fix without the actual received event data.

Plan: temporarily enable bounded local input diagnostics for normal source GUI
startup. Record interpreter/source/Tk identities, received event type/axes/state,
widget and callback, and zoom/circle geometry before/after. Debounce local writes
and keep at most 40 events; capture no images and transmit nothing. Test via real
file-open/production widget/render/export workflows. User must restart this exact
start.py and scroll both directions so the actual session can be diagnosed.
Native Computer Use inspection was attempted with the bundled skill/API, but its
local native pipe is unavailable (os error 2). No alternate desktop automation.
Remove temporary default tracing after resolving the field failure; preserve
explicit opt-in diagnostics if helpful. No Git operations or unit tests.

Field evidence obtained from the user's restarted app: actual interpreter is
Python314/python.exe, Python 3.14.8/Tk 9.0.4, loading this workspace's source.
TouchpadScroll reaches the video Label's WebcamApp.zoom_with_scroll callback with
state 0 (no Ctrl). Vertical deltas change zoom/crop; horizontal-only deltas leave
zoom unchanged. Captured raw optical radii remain identical before/after each
event. A subsequent 40-event snapshot records 30 zoom changes from approximately
223% to 100% and zero measured-radius changes. Summary:
build/gui-validation/touchpad-session-validation.json.

User explicitly confirmed after restarting this exact start.py: "Yes, it works
now". The high-resolution event support is active in the restarted source app;
no additional axis remapping or circle behavior change was needed. Removed the
temporary automatic source-startup trace. The shared binder retains optional
ASTRO_COLLIMATOR_INPUT_LOG diagnostics, disabled by default, bounded to 40 local
events with 100 ms write debounce. The currently running diagnostic session may
continue tracing until its next restart because its environment was already set.

A new actual file-open/render/export workflow proves that the source image itself
enlarges (distinct colored pixel area grows approximately 4x at 2x zoom), not just
overlays. Raw pixels and detected radii remain unchanged; opt-in log fields and
input callback are checked. It and two existing precise/ordinary navigation
workflows passed (3 checks, 5.510 s). Full prescribed runner result follows below.
No unit tests, Git operations or historical assertion removals.

Prescribed full integration validation completed: 63 scenarios in 187.730 s,
62 passed and the same Explorer temporary-source launch failed with WinError 5
before app startup. No skips, unit tests or broad discovery. All rendering,
precise-input, camera, tracking and other app checks passed. Evidence:
build/gui-validation/touchpad-field-integration.log. The trace's first retained
sample includes an ignored horizontal event [-3,0], positive vertical [0,4]
changing zoom 1.775 -> 1.7783, and negative vertical [0,-156] changing zoom
1.7825 -> 1.6525, all with Ctrl state 0 and unchanged measured radii. The actual
user confirmation closes this touchpad field issue. Earlier Explorer permission,
historical coverage-equivalence and native Linux validation gaps remain explicit.

## Startup overlays and manual references — plan, 2026-10-09

Show only the enabled FOV crosshair before detection in Detect & review. Display
manual starter guides only on the Manual guides tab. Reuse detected references
there without duplicate rings; estimate missing radii in Focuser > Secondary >
Primary order from the nearest detected references. Keep user-sized missing
guides through navigation, but clear estimates on a new image or detection run.
Keep estimates separate from measurements and alignment advice. Connect manual
controls to detected circles as well. Give tabs bold labels, spacing and distinct
selected colors without changing the global widget theme. Validate startup pixels,
partial detections, resize/move/navigation, tab state and existing integration
workflows. No Git operations; native Linux desktop validation remains pending.

Implemented: Detect & review and Camera now hide manual starter rings. Manual
circles are shown only on Manual guides; detected rings are reused once, with
working sliders/visibility controls. Missing guides use preset ratios against a
single detected radius or interpolation between two measured radii. User-sized
missing rings survive tab switches, zoom and shared-center movement. New source
images and Detect clear estimates/overrides. Presets remain visual helpers,
separate from measurement exports/advice; Pick edge remains the path to adding
measured/manual references for tracking. FOV remains enabled independently.

Tabs use bold platform-default text, distinct selected colors and a portable
clam tab element without changing the global native widget theme. The first full
run exposed small-screen clipping from extra tab padding; reducing tab and
review-panel padding restored all four affected layout/navigation scenarios
(4 passed, 6.794 s). Old manual click/render assertions now explicitly select
Manual guides before exercising presets, preserving their behavior coverage.
New startup/partial-reference workflows cover rendered pixels, each single-ring
anchor, editing detected circles, zoom/navigation retention and fresh detection.
Final prescribed runner result is recorded below when complete.

Revalidation exposed intermittent native Windows wheel routing failures (the
same native workflow passed in the first full run and an isolated rerun).
One run also showed an unintended integer rounding of a detected radius.
Guard manual slider callbacks by the active manual tab and ignore writes equal
to the displayed rounded radius. Hidden Tk scale updates must not turn an
untouched fractional measurement into a manual edit. Extended the partial-guide
integration scenario to assert this, then checked manual resizing, native wheels
and actual source-image zoom together: 3 passed in 5.553 s. Final full run pending.

Final prescribed integration validation completed: 65 scenarios in 87.898 s,
64 passed; the sole error is the previously recorded Explorer temporary-source
launch (WinError 5 at os.startfile, before app startup). Native Windows wheel,
all GUI/layout, image zoom/pan, manual guides, camera/tracking and source startup
workflows passed. No skipped assertions, unit tests or broad discovery. Evidence:
build/gui-validation/startup-guides-final-integration.log. The intermediate native
wheel failure remains documented above, with its isolated passing rerun in
build/gui-validation/startup-guides-native-wheel-recheck.log.

Validation used the project Python 3.14 environment and Tk 9 on Windows with the
existing extracted Tcl/Tk validation libraries. Native Linux GUI/camera/release
validation and previously mapped historical equivalence gaps remain unresolved.
Restart start.py to load the changes. Portable releases were not rebuilt for
this task. No Git operations were performed.

## Manual-session persistence — plan, 2026-10-09

User clarified that manual circles must survive returning to Detect & review.
Treat entering Manual guides as enabling a manual guide session for the current
image/camera source: reveal all three optical guide roles on entry, retain their
sizes and center across tabs, and continue displaying missing-role manual guides
alongside detected roles without duplicates. Auto-only startup/live workflows
still display no presets until manual mode is used. Detect can reacquire measured
edges, but must retain the manual fallback configuration when an edge is absent.
A new image/camera source resets the manual session. Keep visual estimates
separate from actual measured/manual-picked references used for analysis. Add
integration coverage for tab persistence, hide/re-entry restoration, detection
restart with missing roles, live master movement and fresh-source reset. No Git.

Implemented manual-session persistence. Entering Manual guides enables the guide
session and restores all three per-ring visibility flags plus Show guides. Guide
visibility persists across tabs; automatic roles are rendered once, with missing
manual rings still present. Detected radii can replace estimates; manually sized
missing rings retain their values. Detect keeps the fallback setup, while loading
another source resets it (or starts fresh presets if already on the manual tab).
Global overlay hiding/blink and independent FOV behavior remain available.
Retained manual overlays also remain resizable with Ctrl+wheel in review; this
explicit user input marks the radius override while hidden slider layout writes
remain blocked from editing measurements.

Prescribed runner: 66 scenarios in 80.053 s; 65 passed, sole error is
previously recorded Explorer launch WinError 5 before app startup. Evidence:
build/gui-validation/manual-session-integration.log. After adding explicit
Ctrl+wheel retention, the complete blank-detect/manual/live-loss/new-source
workflow passed again (1 scenario, 2.888 s). All original workflow and failure
assertions retained, with tab visibility/reset expectations updated to match the
user clarification. No unit tests, broad discovery, Git operations or portable
release rebuild. Native Linux desktop and historical equivalence gaps remain.
