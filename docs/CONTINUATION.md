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

## Literal Windows cache folder — plan, 2026-10-09

User already removed %SystemDrive% from the project root. It contained native
ProgramData/Microsoft/Windows/Caches databases, not app content. The tool-launched
process environment has SystemRoot/WINDIR but lacks SystemDrive, ProgramData and
ALLUSERSPROFILE. Restore missing/unexpanded Windows paths from the native Windows
and common-app-data directory APIs before app startup, integration setup and shell
launch validation. Change only the current process environment; preserve valid
caller paths and avoid hardcoded drives. Release checks must inherit repaired
paths too. Add a production startup integration workflow under a deliberately
incomplete environment and verify no literal folders appear in its working
folder or project root. Retain all Explorer launch assertions; record whether its
existing WinError 5 resolves. No user deletion remains, Git or system settings.

Implemented ensure_windows_environment in the shared lightweight bootstrap. It
uses GetWindowsDirectoryW and SHGetFolderPathW(CSIDL_COMMON_APPDATA) to restore
missing, relative or unexpanded process paths while preserving valid caller
values. Called before normal/CLI/smoke startup, integration imports, shell-launch
fixtures and portable-build checks. Linux returns without changing its environment.
No persistent system settings or registry writes, directory deletion or ignore-only
workaround were introduced. The user had already removed the artifact.

The new startup integration workflow passes for deliberately missing/unexpanded
variables and valid caller data paths, using actual Tk/render/export components.
After the full prescribed runner, %SystemDrive% remains absent from the project.
67 scenarios in 84.525 s: 66 passed; the sole error is the unchanged Explorer
os.startfile WinError 5, which does not recreate the cache directory after this
repair. Log: build/gui-validation/windows-cache-path-integration.log. All original
assertions retained; no unit tests, broad discovery or Git operations. Portable
binaries were not rebuilt; native Linux desktop and previous coverage gaps remain.

## Spider vanes and crosshair rotation — plan, 2026-10-09

Add offline straight-spider radial line detection on original image data, with
count four by default and a saved telescope vane count. Both Detect & review and
Manual guides must expose synchronized vane-count, Auto-align and separate
optical/FOV angle controls. Use uniformly spaced radial strokes for the chosen
count; four at zero degrees preserves the existing crosshair geometry. Angles
are clockwise image degrees. Auto-align estimates count and angle from distributed
dark radial evidence, refusing weak/ambiguous/curved or incomplete patterns; do
not rotate on a low-confidence result. Keep vane observations separate from
collimation measurements and do not claim screw alignment or optical accuracy.

Detect vanes in the existing background analysis path and use a separate bounded
image-only job for explicit Auto-align, preserving guide assignments and raw
frames. Source/generation tokens reject stale align results. Manual rotation
survives tracking, pan/zoom and view resets; source changes clear vane evidence.
Keep optical center strokes above FOV strokes. Include rotation/count/evidence
in capture metadata. Validate actual app import/detection/render/export for
three/four vanes, blur/negative cases, both tabs, independent editing, stale
results, camera continuity and existing compact layout. Integration tests only,
no Git or native Linux validation claims.

User refinement: expose separate optical/FOV visibility toggles on both tabs.
Crosshair shapes are limited to three or four blades, with an explicit shared
switch button. Auto mode uses three only for a clear, approximately equally
spaced three-vane pattern converging at the center; all other/uncertain designs
use four. Detected physical ray count is still reported separately. This
supersedes the planned free vane-count spinner; curved/off-center designs are
not represented as three blades. Auto-align does not force hidden overlays on.

### Spider controls — implementation, 2026-10-09

Implemented offline radial contrast plus straight-line intersection evidence in
source/spider_vanes.py. Three blades require three equally spaced radial arms
with sustained dark support and confidence >= 0.75. All other cases retain four;
clear two-arm diameters can orient the four-blade fallback. Curved/off-center,
weak, cropped or missing reflection evidence does not change angles.

Both tabs share visibility, independent optical/FOV angle entries, a 3/4 switch
and Auto-align. Blade shape and angles are session controls rather than new
physical telescope dimensions in the options schema. A manual shape override
survives tracking; new sources reset evidence/shape to four, retaining angles.
Background optical analysis adds vane evidence without rotating crosshairs;
vane errors cannot discard successful optical analysis. Explicit alignment runs
one bounded image-only worker, rejects stale source/manual-edit results and
preserves raw pixels, reference assignments and both centers. No camera restart
is involved. Optical markers retain their thicker stroke above FOV lines.

Review spacing was compressed to retain complete controls at 1280x720/1024x768.
Exports add vane evidence and annotation settings. No Git operations performed.
Native Linux desktop/camera/release validation still requires the real GUI VM.

Validation: prescribed python -B scripts/test_integration.py ran 70 integration
scenarios in 80.769 s; 69 passed. Sole unchanged error: Explorer os.startfile
returns WinError 5 before app startup in this environment. The three new spider
workflows passed again in 5.544 s after strengthening two-arm fallback and
rendered three/four-blade pixel assertions. Evidence:
build/gui-validation/spider-crosshair-integration.log. No unit tests or broad
discovery; historical cases and previous assertions retained. No release rebuild
or native Linux desktop validation performed.

## Image rotation and real spider photographs — plan, 2026-10-10

Replace the Optical angle semantics with whole-image display rotation, including
all circles/crosshairs and their input mappings; leave raw capture/measurements
unchanged. FOV rotation changes only that crosshair relative to the image.
Move shared image/FOV controls next to the existing FOV toolbar above both tabs.
Replace spinbox arrows with horizontal drag angle controls and typed values at
0.01-degree precision. Retain crosshair visibility, blade switch and alignment.

Improve real-photo vane evidence for dark and bright narrow supports, obstruction
at the center, and small perspective deviations; keep strict centered-three
selection and four-blade fallback. Validate the supplied real photographs plus
previous synthetic negative cases through actual GUI production workflows.
Add rotation/render/input/export/compact-layout coverage without deleting earlier
integration scenarios. Run the prescribed integration runner, retain the known
Explorer failure and native Linux VM gap, and record continuation evidence.

### Rotation and real-photo implementation — 2026-10-10

One persistent toolbar above the notebook replaces tab-local duplicate controls.
Image rotation (formerly Optical angle) now rotates the displayed pixels and
all overlays; FOV angle remains relative to the source image and rotates only
that crosshair. Guide crosshair visibility is separate. AngleControl is a Tk
Entry with drag adjustment, Shift fine steps (0.01 degrees), exact typed values,
finite-number validation and two-decimal normalization. Auto-align changes only
FOV angle, preserves image rotation/centers/circle assignments, and still rejects
stale source/manual-angle results. Pan/zoom reset retains rotation settings.

DisplayTransform now maps points/vectors through rotation and its inverse. A
fit scale retains all image corners; rendering, picking, rim hit tests, FOV/guide
dragging, viewport panning, cursor-anchored zoom and guide sizes use the same
mapping. Rotation never changes raw input pixels, optical measurements or saved
raw captures; exports add image_rotation_deg and retain the reference metadata.

Vane detection now uses narrow local bright/dark extrema and coherent competing
three/four-arm hypotheses. It tolerates unequal contrast and a partly obstructed
fourth arm while retaining stricter three-arm evidence. Magenta annotation ink
is removed only in the analysis copy; this prevents baked-in reference-photo
crosshairs from being counted as supports. The three supplied photographs are
mapped to native test images 2.png, qbvhjd7cwo7a1.jpg and
post-333184-0-47945200-1591447543.jpeg; all now report four straight vanes.

Earlier independent-Optical-angle and Auto-align-both-angles assertions were
updated for the requested whole-image semantics. The finite-value/normalization,
raw-export, independent visibility, stale-result, uncertain-image, layout and
camera-stream assertions remain. Native Linux GUI/camera/release validation is
still pending a real desktop VM; no release rebuild or Git operations performed.

Follow-up fixes: the shared toolbar uses two rows, with vane status beside the
FOV visibility/center controls, retaining full guidance text at regular sizes.
Manual fallback radii retain an unrounded viewport value during repeated rotate/
zoom transforms so fractional scale changes cannot accumulate integer-size
error. A full manual-tab rotation cycle is covered by a new integration workflow.
The previously mapped guidance/layout assertions remain unchanged and pass.

Final validation: python -B scripts/test_integration.py ran 73 integration
scenarios in 106.025 s; 72 passed. Sole unchanged error is Explorer os.startfile
WinError 5 before application startup. No application/layout/rotation/vane
failures remain. The rotated-image workflow passed again in 1.188 s after
adding continuous Shift fine adjustment mid-drag and its explicit assertion.
Evidence: build/gui-validation/image-rotation-integration.log. All previous
integration cases remain; no unit tests or broad discovery. Native Linux GUI/
camera/release validation remains pending the real desktop VM.

## One crosshair and complete Reset view — plan, 2026-10-10

Unify the FOV/guide crosshairs as requested: one visible reference, checkbox and
angle control; remove the separate guide-center stroke/control. Use the circles'
shared center when detection or manual guides are active, and frame-center/moved
crosshair position before guides. Crosshair dragging and circle dragging move
the same shared center; keep measured raw geometry independent of visual guides.

Reset view must clear both rotation angles as well as pan/zoom; do not add a
second reset button. Update metadata and user documentation for one crosshair.
Keep integration workflows covering visibility, startup, blink, center dragging,
manual persistence, angles, stale alignment and raw export; update only assertions
for the explicitly changed single-crosshair/Reset-view semantics. Add production
GUI checks for unified controls/center and rotation reset. Preserve historical
cases and coverage mapping; use the prescribed integration runner.

## Fixed-scale rotation around the crosshair — plan, 2026-10-10

Remove the angle-dependent fit scale: rotating must preserve image and circle sizes at every zoom. Use the sole FOV crosshair as the raw-image pivot, including off-center positions. Render the rotated viewport directly from the original frame so zoomed rotation can reveal pixels outside the unrotated crop. Update inverse mouse mapping, cursor-anchored zoom and screen-space panning for that pivot. Retain raw measurements and exports. Extend application integration workflows for off-center pivots, unchanged scale, rotated pan/zoom, Reset view and opening another image; document the intentional replacement of the old corner-fitting behavior.

## Shared crosshair and stable image rotation — implemented, 2026-10-10

- One Crosshair checkbox and Crosshair angle control above all tabs. The brighter center and full-field arms share visibility, angle, blade shape and the circles' center. Center crosshair recenters the group; dragging a rim or intersection moves that group without rewriting optical observations.
- Reset view / Ctrl+0 now clear image/crosshair angles, angle fields, pan and zoom; pending Auto-align results cannot restore the old angles. Existing circle centers and radii are retained. Loading another image invokes the same full view reset and starts fresh source guides.
- Image rotation uses the crosshair as its raw-image pivot. Removed angle-dependent shrinking; the display scale and circle radii stay fixed at every zoom. Rotated edges may be clipped by the viewport. The rotated viewport samples the full raw source, so zoom rotation can reveal pixels outside the unrotated crop.
- DisplayTransform shares exact forward/inverse rotation with rendering and hit tests. Zoom keeps its cursor anchor; panning and shared-pivot dragging translate in screen axes. Raw measurements and PNG exports remain unchanged. JSON exposes crosshair metadata and retains fov_crosshair as a compatibility alias.
- Updated USER_GUIDE.md and INTEGRATION_COVERAGE.md with the intentional retirement of independent crosshairs and corner-fit scaling. Preserved BOM/line endings, historical scenarios and failure coverage. No Git operations or runtime network dependencies.

Validation: prescribed integration runner, 74 scenarios in 104.303 s, 73 pass;
only the existing restricted Explorer shell-start WinError 5 remains. Focused
shared-center/rotation/reset/source-load workflows: four passed in 4.708 s. Log:
`build/gui-validation/unified-crosshair-rotation-integration.log`. Native Linux
desktop GUI/camera/release validation and prior equivalence gaps remain pending.
Source changes are ready through start.py; portable binaries were not rebuilt.

## Overlay dragging must not move image pixels — plan, 2026-10-10

The image transform currently reads the crosshair center on every frame. Moving an overlay therefore changes an already applied rotation and translates image pixels. Freeze the applied image transform between image-angle changes. When an image-angle change starts, compose that change around the crosshair's current displayed intersection without moving that pivot. Keep the resulting translation through zoom, pan and resize; clear it on Reset view/source changes. Overlay dragging must use the inverse image rotation, while empty-space panning continues in screen axes. Check crosshair/circle drags, manual recenter/arrow moves, new detected masters, rotated cursor zoom, resizing, angle changes after moving a crosshair, raw export and source resets through integration workflows with actual rendered pixels. Preserve earlier failure coverage and record remaining platform gaps.

Alignment-feedback steering: use Aligning…/Aligned instead of announcing three/four vane counts. Keep manual crosshair shape switching and useful focus/illumination failure advice.

Latest correction: the FOV crosshair is independent of the concentric guide group. Keep only one full-field crosshair, with its own center/angle/visibility. Guide-circle drags, manual-tab initialization and detected master changes must not alter that center or the applied image transform. Extend integration coverage for repeated file-image tab switches/render frames to reproduce manual jitter.

Rendering steering: antialias FOV rays, their center accent, manual circles and point-pick markers; measured rims already use LINE_AA. Replace exact jagged-stroke pixel assumptions with color/geometry/feathering integration assertions, retaining layering/visibility coverage.

## Independent FOV and stable rotated overlays — implementation, 2026-10-10

- The only full-field crosshair remains independent of all concentric guide circles. Dragging/recentering it leaves guide geometry unchanged; circle/radius/manual-center edits leave FOV position unchanged. No duplicate guide crosshair was introduced.
- Fixed the cause of image movement/jitter: rendering no longer reads a moving overlay center as the already applied image rotation pivot. Image-angle edits capture the current FOV intersection and compose rotation/translation so that intersection stays fixed on screen. Circle/FOV drags use inverse rotated-image mapping; viewport pan remains in screen axes. Composed offset survives zoom/resize and is cleared on Reset view/source change, including when angle is zero. Raw source pixels and measured observations remain unchanged.
- Actual loaded-file integration covers independent reference movement at zoom 1/2, rotations 0/37.25/90, exact clean-image pixel preservation, new automatic masters, manual-arrow/recenter operations, subsequent rotation around the moved FOV, cursor zoom and screen-space pan. A 24-frame repeated-tab scenario verifies identical rotated/zoomed manual pixel output, stable centers and radii. Existing live tracking now also checks unchanged image mapping under rotating display and moving detected master.
- Applied LINE_AA to FOV rays, their brighter center, manual circles and pick markers. Measured rims already used antialiasing. Integration color/geometry checks now accommodate feathering, while verifying real feather pixels, startup-only FOV, layering, visibility, blink and raw exports.
- Alignment status uses Aligning…/Aligned; no detected vane counts are announced. Uncertain captures retain focus/illumination advice. Manual crosshair-shape switching remains available.
- Export JSON includes image_rotation_center_px and image_rotation_shift_px to describe composed viewport rotation. Updated user guide and coverage mapping. No Git operations; fully offline runtime retained. Portable binaries have not been rebuilt.

The overlapping-center drag scenario was updated to hide the FOV handle before
picking the guide center; its complete geometry/reset/export workflow passed
(1.276 s). Native Linux GUI/camera/release and previous equivalence gaps remain.
Final prescribed integration result follows below.

Final validation: `python -B scripts/test_integration.py` ran 76 scenarios in
112.783 s: 75 passed; only the existing restricted Explorer `os.startfile`
WinError 5 occurred before application launch. Evidence:
`build/gui-validation/independent-fov-antialiasing-integration.log`. Existing
coverage and historical tests retained, with explicit semantics mapped in
INTEGRATION_COVERAGE.md. No unit tests or Git operations. Native Linux desktop
GUI/camera/release and earlier documented equivalence gaps remain unvalidated.

## Crosshair group and exact visible rotation pivot — plan, 2026-10-10

Group the FOV checkbox, blade switch, angle, Center/Auto-align/status above Reset view. The checkbox gates only its crosshair controls, retaining independent image rotation and view controls. Remove the fullscreen/windowed button; retain decorated maximized-window startup. Preserve optional keyboard fullscreen behavior unless unnecessary for this request. Explicitly render the white accent as part of the FOV reference on every frame, independent of guide existence/position. Check pivot consistency between actual image pixels and fractional overlay drawing, including zero-angle resampling, zoom, noninteger/off-center FOV positions, and subsequent rotations. Extend integration checks for group ordering/gating, pending alignment while disabled, white marker independence, pixel-level pivot invariance, stable small-screen layout and retained view/source/error coverage.

Group naming correction: use FOV Crosshair as the checkbox/legend. Crosshair-only rotation is already correct and must retain its behavior. White accent rendering must be governed exclusively by FOV visibility and position, never by detection/manual-guide presence.

## FOV Crosshair group and visible pivot — implementation, 2026-10-10

The shared toolbar has a FOV Crosshair checkbox in the group legend, its blade
switch and the existing angle entry alongside, then Center / Auto-align / status. The group appears before Reset view; compact view controls keep
image rotation outside the checkbox-gated group. Disabling FOV disables its
editable controls and invalidates pending alignment. Disabled drag/Return/focus
handlers cannot apply a new angle. The fullscreen/windowed button is removed;
decorated maximized startup remains, with optional F11/Escape bindings retained.

The white accent belongs solely to FOV visibility and its independent position,
including startup. Circle existence, manual-tab activation and circle-group
movement no longer decide its rendering. Image rendering uses the same affine
sampling at zero and nonzero angles; previously switching from resize to warp
could introduce a half-pixel phase change. Rays/accent preserve fractional FOV
coordinates using antialiased subpixel drawing, matching the image pivot. No-op
image-angle applications retain the current composition instead of rebasing it.
Crosshair-only rotation behavior remains unchanged.

Added actual Tk image/pixel integration for the fractional pivot and independent
white marker, plus group ordering/gating/pending-result rejection. Adapted the
removed button and startup-white expectations without dropping their source,
window-state, visibility or failure coverage. Compact review controls/messages
fit 1280×720 and 1024×768. Full runner outcome follows. No Git operations, unit
tests or network runtime. Native Linux desktop/camera/release remains pending;
portable binaries have not been rebuilt.

Final validation: `python -B scripts/test_integration.py` ran 78
integration scenarios in 139.751 s: 77 passed, with only the existing
restricted Explorer `os.startfile` WinError 5 before application launch. Evidence:
`build/gui-validation/fov-group-pixel-pivot-integration.log`. No new behavioral
or failure-case coverage gaps; previously documented platform/equivalence gaps
remain. No Git operations or unit tests.

## White guide-center marker — correction plan, 2026-10-10

The small white crosshair marks the shared circle center, independently of the
red FOV crosshair. Remove the white FOV accent and draw the guide-center marker
only while guide circles are visible. Guide movement/tracking moves the white
marker, FOV movement/visibility/angle leaves it unchanged; startup remains FOV
only. Retain independent image rotation, FOV pivot, mouse hit targets, blink and
raw image integrity. Adapt integration coverage to this corrected semantics and
verify actual rendered markers in manual/detected/live states.

Reset-view steering: Reset view must also recenter the independent FOV crosshair
to the full image center, while retaining the guide-circle center and radii.
Extend reset/source/rotation workflow assertions for this intended change.

Alignment-status steering: successful Auto-align should not display Aligned in
the FOV group or replace capture guidance with a success announcement. Retain
working/uncertain/error feedback and fixed-size layout.

Layout steering: move the angle out of the group legend and into the former
status position to the right of Auto-align. Keep checkbox/blades and other
controls unchanged; no visible success-status label. Progress/error coverage
uses real alignment enablement and capture advice. The first full run was
interrupted to incorporate this UI correction; run the complete suite afterward.

## White guide marker and final FOV layout — implementation, 2026-10-10

The small white marker now belongs to the shared circle center. It is drawn
over visible automatic/manual guide circles, with antialiasing and the displayed
image rotation; FOV position, angle and visibility do not control it. Startup
shows only red FOV rays. Blink still hides all overlays. The separate FOV remains
the image rotation pivot and its drag target remains independent of circle rims.

Reset view additionally centers FOV in the raw image without moving guide
centers/radii, and resets pan/zoom/both rotation angles. Successful Auto-align
updates the angle silently, preserving existing capture advice. The button
shows Aligning… while busy; uncertain/error messages remain available. The group
legend holds FOV Crosshair and its blade switch; Center / Auto-align / Angle are
inside the group on one row. Removed the visible status label. Checkbox gating
and independent image/view controls remain. Focused actual Tk workflows pass,
including 1280×720 and 1024×768 text/control bounds. Full result follows.

The previous white-at-FOV and reset-keeps-FOV interpretations are superseded
by the user's clarification. Coverage mappings record changed semantics,
retaining raw pixel, geometric, visibility, source, stale-work and failure checks.
No Git operations, unit tests or runtime network access. Native Linux desktop
GUI/camera/release remains unvalidated; binaries have not been rebuilt.

Final validation: `python -B scripts/test_integration.py` ran 78
integration scenarios in 148.285 s: 77 passed; only the existing
restricted Explorer `os.startfile` WinError 5 occurred before application launch.
Evidence: `build/gui-validation/circle-center-reset-angle-layout-integration.log`.
No new coverage gaps; documented native Linux and historical equivalence gaps
remain. No unit tests or Git operations.

## Matched guide-marker shape and angle — plan, 2026-10-10

Use the existing FOV angle and blade count when drawing the small white
circle-center marker. Preserve independent centers/visibility and current
image-transform behavior. Verify real rendered three/four-blade shapes, manual
angle changes, image rotation, Auto-align, hidden FOV and guide movement through
production GUI workflows; retain existing integration coverage.

## Matched guide marker — implementation, 2026-10-10

The white circle-center marker now reads the same FOV angle and blade count
as the large red FOV crosshair. Both use the current image transform for
orientation, including image rotation, while retaining independent positions
and visibility. Manual shape/angle controls, vane detection and Auto-align
therefore update both consistently without a duplicate state.

Added a rendered GUI workflow distinguishing three/four ray shapes, checking
manual angles and rotated images, hidden-FOV white-patch identity, raw pixel
integrity and real Auto-align. Existing thicker-center/visibility/live-capture
workflows pass. User guide and coverage map updated. Fully offline runtime,
BOM/line endings preserved, no Git operations or unit tests. Final full-run
result follows; native Linux desktop/camera/release remains unvalidated and
portable binaries have not been rebuilt.

Marker matching validation completed: 79 integration scenarios, 78 passed in
148.776 s; only known restricted Explorer launch WinError 5. Evidence:
`build/gui-validation/matching-guide-marker-integration.log`.

## Image Auto-align and Detect alignment — plan, 2026-10-10

Auto-align rotates the displayed image around the independent FOV center,
keeping the visible crosshair orientation and its angle control unchanged.
A shared render compensation applies equally to red FOV and white guide marker;
manual image rotation still rotates both as before. Rotate by the nearest
three/four-blade-equivalent angle, preserving zoom, centers, raw measurements
and pixels. Explicit Detect edges also aligns on reliable evidence; background
tracking must not continually rotate. Repeated alignment is stable; uncertain
evidence preserves rotation and supplies capture advice. Reject alignment from
in-flight detection after reset/angle/source changes. Reset/source load clears
compensation; capture JSON records it. Adapt integration semantics and verify
actual image landmarks, fixed rays/pivot, stale work, tracking, export and
uncertain inputs without weakening prior coverage.

## Image Auto-align — implementation, 2026-10-10

Auto-align measures raw vanes and applies the nearest equivalent displayed
image-angle correction around the current FOV pivot. Shared crosshair render
compensation keeps the visible red and white rays fixed while leaving the
manual FOV angle entry unchanged. Manual image rotation still rotates both
references; marker/FOV centers remain independent. Explicit successful Detect
also aligns; background tracking updates evidence without rotating the view.
Reliable detection uses its own frame/measurements before applying alignment.
Uncertain Detect retains capture guidance; uncertain explicit Auto-align gives
useful advice without changing angles.

Detection captures the alignment generation and rejects its automatic rotation
after reset/angle/visibility/source changes. Reset/source load clears the shared
compensation. Exports include rotation_compensation_deg and render_angle_deg
under the canonical/legacy crosshair aliases; saved PNG remains raw.

Focused workflows pass for actual landmarks at zoom 2 with nonzero angles and
off-center FOV, fixed visible rays/pivot/user angle, repeated pixel identity,
export/reset/in-flight rejection, uncertain designs, rotated overlay dragging,
matching white/red shapes and all three real photographs. Full runner follows.
Prior FOV-only alignment assertions were updated to test image alignment while
retaining their failure, pixel, mouse, raw measurement and platform coverage.
No Git operations or unit tests; runtime offline. Native Linux desktop GUI/
camera/release remains pending and portable binaries have not been rebuilt.

Final validation: `python -B scripts/test_integration.py` ran 80
integration scenarios in 160.966 s: 79 passed; only existing restricted
Explorer `os.startfile` WinError 5 before application launch remains. Evidence:
`build/gui-validation/image-auto-align-detect-integration.log`. No new coverage
gaps; previously documented Linux desktop/release and historical equivalence
gaps remain. No unit tests or Git operations.

## Rotation buttons and radius dragging — plan, 2026-10-10

Add compact −/+ buttons beside image rotation and FOV angle, each adjusting
0.01° per click through the existing angle setter. FOV buttons follow checkbox
gating; view rotation remains independent. Add a drag-capable radius entry:
horizontal drag changes whole raw-image pixels, Shift offers one pixel per
ten screen pixels, preserving typed entry, validation, clamping, wheel/buttons
and tracking pause during editing. Escape/source changes terminate drags;
invalid or disabled entries remain safe. Verify real GUI events, angle wrapping,
shared-marker rendering, raw-radius invariance under zoom/rotation, release/
tracking behavior, bounds and ordinary-screen layout in integration only.

Layout steering: label the FOV angle Rotation; move the view toolbar above
the FOV Crosshair group, then keep the source/status/tabs below both groups.
This supersedes the earlier Auto-align-before-Reset vertical ordering.

Branding steering: rename visible application and release branding to Advanced
Astro Collimator, including window/launcher text, README and user documentation.
Keep start.py and source/ entry paths and offline/platform constraints.

## Rotation/radius controls and Advanced Astro Collimator — implementation, 2026-10-10

Both rotation entries now have compact −/+ buttons applying 0.01° steps through
the existing production setters. FOV buttons follow checkbox gating; image
buttons remain independent. The FOV field is labeled Rotation. View toolbar
comes above the crosshair group, then source/status/tabs, preserving the
compact layout at 1280×720 and 1024×768.

RadiusControl adds horizontal whole-image-pixel dragging to Radius (px), with
Shift at one image pixel per ten screen pixels. It retains fractional fine
motion across events and discards bound overshoot so direction reversal works
immediately. Existing radius validation/reference resize paths remain shared.
Editing pauses tracking application while camera capture continues; release
commits and resumes, Escape/role/source changes cancel the drag anchor and
prevent a late release from changing new-source advice. Typed entry, buttons,
wheel, colors and radius limits remain intact.

Visible GUI, launcher/version/error text, README/current user docs, project
distribution metadata and native build naming now use Advanced Astro Collimator
(AdvancedAstroCollimator executable/archive names). start.py/source/ stay shared.
Historical release records and files were preserved; no new portable binaries
have been built, so release-artifact branding awaits native build validation.

New actual GUI workflows cover precision/wrapping/invalid angles, disabled
controls, layout/title/launcher subprocess, live radius dragging at rotated
zoom, Shift transition, raw geometry, clamping, invalid inputs, Escape and
mid-drag source change. Existing compact-label/typed-radius workflows pass.
User guide and coverage mapping updated. Full runner result follows; native
Linux desktop GUI/camera/releases and known Explorer/historical gaps remain.
No Git operations, unit tests or runtime network access; UTF-8 flavor preserved.

Full-run follow-up: wider controls exposed nonuniform rounded viewport scales.
Preserve the actual displayed crosshair direction during Auto-align by using
forward/inverse image vectors when computing correction and compensation;
retain the strict direction/pivot assertions. Update old white stroke waits
from exact 255 side pixels to bright neutral antialiased coverage without
changing layering/visibility checks. Native build CLI validation was blocked
because platform.machine() is empty in the isolated environment despite a
64-bit interpreter; new release artifacts remain unbuilt.

Final validation: `python -B scripts/test_integration.py` ran 82 integration
scenarios in 163.621 s: 81 passed; one existing Explorer association scenario
failed before application launch with `os.startfile` WinError 5 (Access denied).
No application workflow failures remain. Evidence:
`build/gui-validation/rotation-radius-branding-integration.log`. Coverage mapping
retains existing workflows and failure cases, plus the two new GUI scenarios.
Release artifacts remain unbuilt; native Linux desktop/camera/releases, Explorer
launch in this restricted environment and earlier historical equivalence gaps
remain explicitly unvalidated. No unit tests or Git operations.

## Detection label and camera names — plan, 2026-10-10

Rename the action to Detect edges and align image without changing detection or
tracking behavior. Read friendly camera names on the camera worker using the
same DirectShow moniker ordering as capture on Windows, and Linux video4linux
sysfs device names. Keep explicit label-to-index mapping, disambiguate identical
names, retain selection by index on refresh, and fall back to Camera N when
names are unavailable. No runtime network or extra dependencies. Integration
workflows must cover discovery, switching, refresh, unnamed/duplicate devices,
name-query failures and native API boundary/resource ownership. Preserve current
coverage; native Linux desktop/hardware validation remains pending.

## Detection label and camera names — implementation, 2026-10-10

The action now reads Detect edges and align image. Its detection, alignment and
tracking restart behavior is unchanged. Camera discovery reads DirectShow
FriendlyName through IMoniker::BindToStorage/IPropertyBag::Read on the worker,
using the same moniker order as CAP_DSHOW. Variant strings and COM references
are released before the querying apartment closes; names do not open cameras.
Linux reads /sys/class/video4linux/videoN/name without extra dependencies.

Labels show Name (Camera N), or Camera N on missing/failed queries. Explicit
label-to-index mapping replaces string parsing, disambiguates identical names,
and preserves the index on refresh even when the reported name changes. The
selector is wider; source descriptions use the same name. Runtime stays offline.

Five focused integration scenarios passed: real Windows FriendlyName queries
with production worker/Tk selection/refresh and capture boundary substitute;
Linux sysfs names with actual discovery/control/streaming and hardware boundary
substitute; duplicate names, changed names, inaccessible names, same-index
refresh/resume, detection action/export and compact layout; existing no-camera
recovery and permission failure. Actual Windows query reported USB2.0 HD UVC
WebCam. Native Linux desktop/hardware and Windows COM name-query failure
cleanup paths remain unvalidated; ordinary driver-name fallback is covered.
Full integration runner follows. No Git operations or unit tests.

Native API reference: https://learn.microsoft.com/en-us/windows/win32/directshow/selecting-a-capture-device

## Direct editing instead of outline chooser — plan, 2026-10-10

Remove Change outline and alternative-candidate navigation from Detect & review.
Use the detector's automatic best-role suggestions as the displayed circles,
with one outline per named role and no confirmation. Keep uncertain/missing
reference advice and manual picks, direct radius entry/drag/buttons, and common
center mouse movement. Preserve raw independent observations for analysis; do
not fabricate optical evidence or force unrelated candidates into missing roles.
Retire the chooser-only production UI/state and adapt its active integration
scenarios to direct edits/manual replacements, retaining roundness, master
center, raw data, restart, duplicate-reference and hidden-hypothesis coverage.
Keep historical tests. Update user guide and explicit coverage mapping.

Camera-name validation before the outline-chooser steering: the full explicit
runner completed 84 scenarios in 174.754 s; 83 passed and the existing Explorer
os.startfile WinError 5 remained. Evidence: build/gui-validation/camera-names-integration.log.

## Direct editing instead of outline chooser — implementation, 2026-10-10

Removed Change outline, its hidden cycling panel, candidate-label state and
chooser handlers. Automatic detector suggestions are already best-ranked per
identified role and now lead directly to radius/drag editing with no confirmation
or alternative navigation. Missing-reference help points to Pick edge. Normal
rendering still hides unused hypotheses; user edits preserve the round/shared
center rules and manual tracking retention. Raw observations remain independent
and uncertain unrelated rims are not forced into named roles.

Chooser integration scenarios now use direct typed radius edits and manual
three-point replacement. They retain the same oval image, explicit rejection
of the unverified oval focuser, manual master anchoring, per-role roundness and
center invariance, uniqueness, extra-hypothesis pixel invisibility, clear/restart
and guidance/layout checks. No historical tests removed. Focused direct-edit,
radius drag, static-detection and named-camera workflows pass. Final full runner
follows; platform/Explorer/COM-failure/historical gaps remain documented.

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

## Consistent rotation control order — plan, 2026-10-10

Match radius controls in both rotation rows: minus button, Image rotation or
Rotation label, numeric drag/type field with adjacent degree unit, plus button.
Move the degree unit before plus and create the label inside the shared rotation
builder. Preserve 0.01-degree button steps, drag/type behavior, enablement and
layout order. Extend actual GUI layout workflow to assert left-to-right order,
unit placement and bounds on both tabs at ordinary screen sizes. Integration
only; preserve encoding, offline runtime and no Git operations.

## Consistent rotation control order — implementation, 2026-10-10

Both Image rotation and FOV Rotation now read left to right as minus, label,
numeric drag/type entry, degree unit, plus. The shared builder owns the label
and unit placement, preserving numeric values/validation and 0.01-degree steps.
Radius layout and rotation behavior are unchanged. Three focused integration
workflows passed: actual widget ordering/nonoverlap/alignment on both tabs at
1280x720 and 1024x768, existing angle wrapping/invalid input/disabled gating,
pending alignment and rotated image mouse dragging. Full runner follows.

Final validation: `python -B scripts/test_integration.py` ran 84 scenarios in
178.085 s: 83 passed, with only existing Explorer os.startfile WinError 5
(Access denied before app launch). Evidence:
`build/gui-validation/rotation-control-order-integration.log`. Existing scenario
coverage retained and layout assertions extended; no new validation gaps. Native
Linux desktop/camera/releases, forced Windows COM failure cleanup and earlier
historical/Explorer gaps remain. No unit tests, Git operations or release build.

## Phone capture/link — plan, 2026-10-10

Read all six pages of newtonian-collimator-conversation.pdf (visual review of
streaming page included). Implement only phone photo/video capture now; defer
phone overlays/shared analysis controls. Add Stream from the phone as a Camera
selector option, even with no physical camera. Start a local receiver only when
selected, show LAN URL + locally generated QR while waiting, and restore it on
stream loss; stop receiver on physical-camera/file switch and app shutdown.

Serve a self-contained mobile page with Take photo, Choose photo, Stream video
and Stop video. Photo uploads preserve supplied bytes; decode EXIF orientation
and HEIC locally. Live getUserMedia requires trusted HTTPS: provide a local CA
certificate, device-specific installation/trust guidance and a TLS server with
LAN-IP SANs; photo capture/upload works over HTTP without certificate setup.
No system trust/firewall changes, public services, analytics, STUN/TURN or CDN.
Use backpressured JPEG frame uploads for a lightweight LAN video feed instead
of a WebRTC dependency; bounded newest-frame mailbox, decouple analysis rate
from receipt, reject stale streams/frames and source generations.

Use session-token URLs, same-origin requests, bounded payload/dimensions/decode
concurrency, timeouts and explicit error receipts. GUI work remains on Tk thread;
HTTP decode/startup run in workers. Integrate phone video with production live
tracking/averaging, pause/edit/zoom/pan/blink and raw PNG/JSON export; photos are
static sources with fresh view and automatic detection. Preserve USB controls
with unsupported phone sliders disabled/hidden. Bundle HTML/JS and QR/TLS/HEIC
dependencies for source/native releases. Keep source/ entry organization.

Integration: actual local HTTP/HTTPS sockets and production Tk/detection/tracking
with browser camera substituted only at hardware boundary; QR URL decoding,
photo JPEG/PNG/EXIF/HEIC and exact-byte receipt, live newest frame/backpressure,
source switch/pending/stop/reconnect, malformed/oversize/auth/origin/stale inputs,
ports/thread shutdown, page/browser controls and ordinary-screen layout. Retain
prior 84 workflows and map coverage. Actual Android/iPhone trust/camera capture,
LAN firewall/isolation, native Linux desktop and release remain explicit gaps
until devices/desktop VM are available. No Git or unit tests.

Phone-link certificate steering: never require installation for photos. Offer
local HTTPS video without an installed certificate when the browser permits a
user-approved local connection; do not promise universal browser support. Only
if camera access is blocked, offer optional locally generated CA trust setup.
Show both server certificate and CA SHA-256 fingerprints on PC and phone so
browser certificate details or installation details can be matched exactly.
Certificates/private keys are generated locally, never bundled/shared, and no
OS trust or firewall setting is changed automatically.

Phone integration follow-up plan: retain the existing steady/motion checks and
three-frame limit, but use a 350 ms averaging window for the lower-rate phone
feed; retain 120 ms for local cameras and restore it on every source switch.
Validate actual paced HTTP frames, timeout/reconnect and unchanged USB workflows.

Adapter discovery follow-up plan: enumerate native IPv4 interface addresses on
Windows/Linux rather than resolving the computer hostname. This avoids DNS and
Linux hostname-to-loopback mappings. Perform enumeration in the receiver startup
worker. Validate real Windows adapter URLs/QR plus explicit loopback TLS tests;
native Linux interface ioctl behavior remains a real-VM handoff item.

## Phone capture/link — implementation, 2026-10-10

Added source/phone_server.py, phone_capture.py, phone_tls.py, phone_profile.py and
local_network.py, with self-contained source/web/phone.html and phone.js. Camera
selection always offers Stream from the phone. The app shows a locally generated
QR, adapter selector and copyable URL while waiting/lost, and hides USB settings
for phone input. Source changes and closing stop the receiver without blocking Tk.
No certificate/trust/firewall installation is performed by the application.

HTTP photos need no certificate installation. Supplied bytes are retained for
the latest photo; Pillow decodes EXIF orientation and HEIC locally, and receipt
starts fresh view/detection/alignment. Pending analysis defers the next photo’s
detection until the worker completes; latest-frame mailboxes stay bounded.
HTTPS video uses browser getUserMedia and backpressured JPEG uploads, a separate
stream generation/sequence and stale-frame checks before/after decoding. Stop
messages do not wait for the single image-decoder slot. Browser cancellation
stops camera tracks and prevents old async requests from reviving a stopped feed.
Video is integrated with existing live controls and motion-checked three-frame
averaging (350 ms phone, 120 ms USB); four-second loss restores QR and retains
the last frame. Same-view reconnect retains manually supplied circles and zoom/
rotation; changed dimensions/new photos reset the view. PNG/JSON export stays
raw and excludes stale phone advice and pairing tokens.

TLS roots are generated per installation and persist only in private local
phone-link/ files beside options.json; server certificates are renewed locally
for discovered IPv4 addresses. Identity creation is serialized, partial/corrupt
identities are not silently replaced, and failures preserve HTTP photo access.
PC dialog, phone page, downloadable root and optional certificate-only unsigned
iOS profile show matching SHA-256 identities. Users compare actual certificate
details before optional trust; browser-specific trust remains explicitly pending.
Native adapter enumeration avoids DNS and hostname-to-loopback mappings and
preserves Windows route ordering. Initial native Windows enumeration correctly
preferred 192.168.178.37; adapters can still be selected by the user.

requirements.txt/pyproject.toml declare QR, cryptography and HEIC dependencies;
requirements-test.txt is browser tooling only. Source wheel/native builder include
web assets; native release docs/notices/dependency records were extended and
personal certificate/key inclusion is rejected. The built source wheel contains
both web assets, with tests and personal certificate files excluded. Portable
executables were not rebuilt; Linux desktop/device validation remains pending.
User docs are in PHONE_CAPTURE.md, linked by README and existing user/setup guides.

Validation evidence: intermediate complete run passed 91/91 in 181.038 s, including
Explorer startup which had been blocked in earlier restricted runs. Extended
94-scenario run exposed a serial-cadence averaging assertion and four native-wheel
subcases during overlapping command activity; averaging now uses an independent
real HTTP sender and observes completed averages throughout receipt. Isolated
native wheel and phone averaging/reconnect workflows then passed (2, 13.529 s).
A final full runner on the finished implementation follows; record its exact
result below. No Git operations, unit tests or broad discovery. Previous
historical/native COM and real mobile/Linux/release gaps remain in the map.

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

## Startup dependencies and phone connection view — plan (2026-10-10)

Check every required runtime dependency with real codec, QR, TLS and Tk operations before opening the application. Stop startup on missing or broken dependencies, aggregate failures, and identify the launching interpreter in the error and log. Keep version/help metadata usable without opening the GUI; do not install software or certificates automatically. Move the QR from the Camera sidebar into a large centered connection panel on the image side. Receiving a photo/video restores image rendering; losing video offers the QR again while retaining the previous frame. Display the actual local HTTPS setup error rather than a generic unavailable message. Extend complete startup/phone integration workflows, preserve previous coverage, and record remaining real-phone/Linux/release gaps.

Implemented: source/dependencies.py validates numpy, OpenCV PNG/JPEG, Pillow
PNG/JPEG/EXIF, qrcode rendering, production cryptography/OpenSSL certificate
creation, native HEIF encode/decode, Tk/ImageTk and bundled phone-page files.
GUI and release-smoke launches stop with an aggregate dependency error before
application creation; version/help remain metadata-only. Temporary certificate
checks never alter the saved phone identity or OS trust. Existing error dialogs
and UTF-8 startup logs identify the interpreter; Linux attempts a Tk error dialog
when display support is available.

The actual running app used the system Python314 interpreter, where qrcode,
cryptography and pillow-heif were absent. Installed the three declared versions
and their transitive packages there. No interpreter association, automatic
installation behavior or certificate trust settings changed. Missing crypto was
the cause of the screenshot’s local HTTPS failure.

The large QR is centered on the main image side and sized with integer pixels
for scanning. Photo/video receipt restores the image. Show QR/Show image can
switch views without changing stored image pixels or guides; stream loss restores
the card while retaining the last frame/view. QR mode ignores hidden-image
wheel and drag events. Camera sidebar displays the actual HTTPS setup cause;
phone-error.log records the exception and interpreter without pairing URLs.

Focused integration results: four launcher/photo/QR/certificate-failure workflows
passed in 10.209 s; three actual damaged-installation/tracking/averaging/reconnect
workflows passed in 25.531 s. The new package-installation workflow uses copies
of real production modules and removes only a copied HEIF native extension.
Previous scenarios and historical files are retained; coverage mapping extended.
Complete runner evidence follows below when finished. No Git operations or unit
tests. Existing real-phone, LAN/firewall, native Linux/release, native COM failure
and historical equivalence validation gaps remain.

Final validation: `.venv/Scripts/python.exe -B scripts/test_integration.py`
passed all 95 production integration scenarios in 222.335 s, without skips.
Evidence: `build/gui-validation/startup-phone-view-integration.log`. This includes
actual Explorer startup through the associated system interpreter, the repaired
real-package/native-codec workflow, main-view QR decoding/layout/state transitions,
local HTTP/TLS and the production mobile browser page. Native Linux desktop, real
iPhone/Android capture/trust UI, physical LAN/firewall behavior and rebuilt portable
releases remain unvalidated; historical equivalence/native COM failure gaps are
still recorded. No Git operations, unit tests, broad discovery or trust changes.

## Browser photo capture and camera zoom — plan (2026-10-10)

Replace the native-camera file capture shortcut with a browser camera preview and
shutter. Use the existing optional local HTTPS connection for camera access;
Choose photo remains available on HTTP for existing files. Keep photo/video in
one preview, prefer ImageCapture.takePhoto for native still capture and use a
lossless preview-frame capture when unavailable. Stop video uploads before sending
a still, retain the camera for subsequent photos, and close/cancel tracks cleanly.
Expose camera-reported zoom min/max/step and apply constraints to the actual track
for both stills and video. Report unsupported zoom and constraint failures; do not
use CSS/canvas cropping as camera zoom or promise optical zoom where the browser
cannot identify it. Add integration coverage through the actual browser page,
receiver, desktop analysis and export, using substitutes only at camera hardware
boundaries where capability/failure cases require it. Preserve existing coverage
and document real mobile zoom/lens/platform validation gaps. No Git operations.

Implemented browser camera preview with Open/Close/Cancel camera, browser shutter,
Choose photo and Send/Stop video. Native ImageCapture.takePhoto is preferred; a
full lossless PNG preview frame is used when still capture is unavailable. The
phone camera remains open after a still or stopping video. Still capture cancels
and drains pending video uploads before sending its photo, preserving backpressure
and avoiding stale frames; source/desktop analysis behavior is unchanged.

Camera zoom queries track capabilities/settings, uses reported min/max/step,
requests zoom permission when the browser supports the constraint, and applies
serial/latest changes to the camera track. Rejected or ignored settings restore
the actual zoom. No preview transforms or artificial camera zoom. Camera
cancellation closes late-acquired tracks, and old zoom promises cannot update a
new camera. Browser camera photos now need the same HTTPS permission as video;
existing file uploads remain available without it. Updated desktop/mobile wording
and phone/user/getting-started documentation reflect this distinction.

The existing production browser workflow now includes native still capture and
shared preview reuse. The new complete capability/failure workflow passed in
8.094 s, including real native still, camera hardware zoom constraints and
failures, actual video-to-PNG still transfer, unsupported zoom, camera denial and
pending acquisition cancellation. Intermediate harness issues were fixed:
Playwright route callbacks must be serviced until actual uploads complete;
function polling preserves the production CSP; receipts include video frames
and cannot be hard-coded as still-photo counts. No production CSP relaxation or
server receipt change. The generated mobile camera/zoom screenshot was inspected
at 390px width. Complete integration result follows. Physical optical zoom and
real mobile browser/LAN/Linux validation remain pending. No Git operations.

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
