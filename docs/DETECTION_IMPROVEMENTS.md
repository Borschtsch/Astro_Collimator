# Detection improvement plan — 2026-10-05

## Named outlines and momentary blink plan (recorded before implementation)

The user finds raw candidates confusing and wants one outline per optical element,
plus an explanation of how to use the result. Raw hypotheses include multiple rim
sides, reflections and circular texture. Keep these internal/exported for diagnosis,
but normal review shows only one assigned focuser, secondary, primary and mark.
Missing/unidentified roles stay missing. Put raw alternative selection behind an
explicit Change outline action, show alternatives one at a time, and remove the
all-candidate display. Use named overlay labels, per-element states and a next-step
instruction: blink-check, correct, confirm, advance. After confirmation display
image-center comparisons as geometry only and offer a baseline capture/reacquisition;
no uncalibrated screw instruction or optical success verdict. Right press temporarily
hides overlays; right release restores them, leaving persistent visibility and
references unchanged. Focus loss also ends blink so overlays cannot remain stuck.

## Next interaction change (recorded before implementation)

The user requested always-accessible view reset, right-button blink comparison,
thinner lines, and mouse movement of circles with fresh automatic detection on
Detect. Put Reset view and Show overlays above the tabs. Reserve right-click for
toggling all overlays, keep middle drag for panning, and use left drag to move a
visible rim/center or pan empty image space. Picking mode takes precedence over
circle dragging. Manual guides keep their shared center; detected references move
independently in raw coordinates, lose automatic fit evidence and confirmation,
and retain original geometry/translation in exported metadata. Detect clears
manual adjustments, ends gestures, restores overlays, and analyzes the raw image
again. Verify blink preserves state, dragging after zoom/pan maps correctly,
reset preserves references, and Detect replaces manual shifts with new fits.

Additional user constraint: the focuser reference must always be circular.
Constrain its fit to a circle and show missing portions as finer extrapolated
dashes. Automatic assignments require evidence on the constrained circle; manual
role assignment can retain an explicitly labelled circular estimate. Other
references retain ellipse support and leave missing arcs blank.

## Follow-up plan: roundness, unsupported ellipses, and panning

Recorded before the next changes, following the user's six screenshots:

- Add a locally saved maximum ellipse eccentricity in setup/options. Start with
  e = 0.55 (minor/major axis about 0.84); e = 0 permits circles only. Apply it
  consistently to rim hypotheses so stretched artifact ellipses cannot pass.
- Require more angular evidence for an interior ellipse than a visibly clipped
  rim. Suppress fits assembled from existing rims. Draw supported arcs only for
  automatic candidates; do not outline empty inferred areas.
- Reduce outline/halo widths while retaining color contrast and readable labels.
- Replace scrolling capture advice with short, fully wrapped priority actions.
- Add right/middle-button drag panning, cursor-anchored wheel zoom, and a reset
  view action. Share one clamped crop transform between rendering, overlay
  positioning, and manual clicks. Analysis/export stay in uncropped raw pixels.
- Validate on the newly available small example images as well as existing
  fixtures, and retain negative cases, camera behavior, and regular-screen layout.

Recorded before implementation, following the user's real-image screenshots.
The original detector finds the bright primary and central reflection details,
but misses faint focuser rims and secondary outlines. Thin gray overlays make
even successful candidate detection difficult to see.

## Intended changes

- Keep offline processing, independent centers, frozen-image review, and explicit
  optical-role confirmation. Do not turn nesting into a collimation verdict.
- Supplement contour fits with radial-gradient searches seeded by visible rims.
  Fit ellipses from separated supporting arcs and tolerate missing sections from
  clips, spider vanes, and the image border. Require distributed angular support
  and coherent contrast so texture alone cannot justify a circle.
- Retain angular support, clipping, and edge softness in measurements. Make
  inferred portions visibly different from supported sections. Reject shapes
  supported by too little geometry; ask for a better view or manual correction.
- Detect broad edge transitions and provide a focus/steady-camera instruction.
  Missing/unidentified focuser rims should prompt a wider camera view: zoom out,
  reposition, or use a camera/lens with a wider field.
- Draw bright thicker outlines with dark halos, readable labels, and an emphasis
  on the candidate currently being reviewed. Show detected candidate counts even
  if no three-edge role assignment is possible.
- Keep capture advice compact and readable on regular screens. Explain that
  partial fits remain estimates requiring confirmation.

## Validation

Use the existing source images in `lox` as local examples without modifying them.
Add synthetic missing-arc, clipped, low-contrast, moderate-blur, and excessive-blur
cases, and negative noise/straight-line cases. Check geometry errors, overlay
visibility, GUI layout, and existing camera/review regressions. Record timings
and actual results after implementation. These photos are examples, not a
calibrated aligned reference or an optical-accuracy benchmark.

## Later recommendations

After reliable feature identification, compare confirmed measurements against
the forward model integrated into this app. Account for expected secondary
reflection offset, camera perspective, and measurement uncertainty. Recommend
the next optical adjustment only when its cause is distinguishable; screw names,
directions, and turns require camera/mechanical calibration. The user requested
this as the later stage; this change improves detection and capture advice first.

## Current result: named outlines and momentary blink

The plan at the top is implemented. Only the assigned named optical outlines are
shown, at most one per element. Unassigned geometric hypotheses remain available
internally/exported; Change outline lets the user choose a replacement for only
the current element. Missing roles are explicit. Confirmation advances the
workflow, guided by per-element states and a next-step instruction. Checked image
centers are compared relative to the focuser in raw pixels (+right/+down), for
baseline comparison only. No uncalibrated adjustment diagnosis has been added.

Blink now hides on right press and restores on release using a transient flag;
Show overlays, picks, references and navigation are preserved. Root-level release
and focus-loss handling prevents stuck hiding. Tests also now retire closed Tk
windows on their owning thread; analysis closures capture only image data/queue.

Validation: **66 checks pass**, including render equality after inserting extra
raw hypotheses, one-element replacement, guided confirmation/missing prompts,
image offsets, completed-review screen layout, press/release blink and release
outside the image. Detailed checkpoints are in CONTINUATION.md. Earlier sections
below retain the previous toggle behavior and visual inspection results as history.

## Previous interaction result

The interaction plan above is implemented, including the additional circular
focuser requirement. Reset view is always accessible above the tabs (Ctrl+0 also
works); right-click now toggles every overlay for a blink test. Left drag moves a
visible rim/center or pans empty space, with picking taking precedence. Middle
drag always pans. Manual shared-center guides move together; detected references
move independently and become unconfirmed manual geometry. Original geometry and
cumulative raw-pixel translation are exported. Detect clears manual modifications,
restores overlays, and independently fits the original raw image again.

Colored strokes are now 1 px (2 selected), with a 1-pixel wider halo. Focuser fits
are circular: automatic ones are verified against image transitions and refined
with a circular constraint. Manual ellipse assignment produces a labelled circle
estimate with no inherited fit score. Its missing portions are shown with dimmer
fine extrapolation dashes; other references still leave missing sections blank.

Validation: **64 checks pass**, including the interaction, raw coordinate/export,
redetection, circular focuser and missing-arc checks described in CONTINUATION.md.
Four local-photo regressions remain in the suite. Offline processing and review
requirements are unchanged. The earlier checkpoint below records prior stroke
widths, pan buttons, and pre-circle-constraint timings.

## Previous implemented result (roundness/panning)

All follow-up items above are implemented. Maximum eccentricity defaults to 0.55
and is saved in Telescope setup / Options. It applies to the final rim evidence
and refinement, with one analysis pixel of semiaxis tolerance for raster circles.
Interior fits need 65% supporting samples/bins; image-clipped fits retain the 48%
threshold. Both require three quadrants, coherent contrast, gradient-normal
alignment, and transition prominence. This conservative evidence rule can omit
very faint genuine edges: better capture or manual correction is still necessary.

A bright-face bounding-box seed after closing narrow spider gaps helps recover
main rims when the bright mirror is divided by vanes. The closed image supplies
search origins only; evidence always comes from the unmodified image transitions.
Proposals remain bounded to three seeds, fourteen radial peaks per seed, and
24 contours with sixteen arc windows each. Duplicate/mixed-rim suppression and
optical-role confirmation remain in place.

Overlays use 2-pixel colored strokes (3 for selected rims), with a 2-pixel wider
black halo, smaller backed labels, and spaced label placements. Only supported
arcs are drawn for automatic fits. Their missing sections stay empty, even after
confirmation. Manual circle references still show their explicitly fitted circle.
Broad transitions (14 analysis pixels) request better camera focus; soft rims are
reviewable but excluded from automatic role suggestions.

The advice area is a fully wrapped label with short priority actions and no
scrollbar. More detailed engine messages remain in exported metadata. Sidebar
width is stable so changing messages cannot move the viewport. Wheel zoom anchors
to the cursor, left drag pans within the cropped image (right/middle also works),
and Reset view or
right double-click restores the full image. Overlays, manual picks, and manual
guides follow the shared clamped transform. Raw analysis/export are unchanged.
Left-click places/picks on release; movement of at least 5 pixels starts a drag
and suppresses point placement. This was changed at the user’s request after the
initial right/middle-button implementation.

Validation: **58 checks pass**, including four optional real-photo regressions.
Synthetic checks cover stretched-shape rejection, configurable eccentricity,
raster circles, a rejected short interior arc, missing-arc rendering before/after
confirmation, and panning/cursor zoom/manual-pick coordinates. Advice and controls
fit at 1280×720 and 1024×768. Existing camera, blur/noise, settings, freeze/stale
analysis, and capture regressions pass.

Three-run processing medians on this Windows/Python 3.13 environment (milliseconds):

| Local input | Median ms | Candidates | Observation |
| --- | ---: | ---: | --- |
| images.jpg | 84 | 4 | Main three rims now proposed; lower ghost ellipses removed. |
| image (1).jpg | 177 | 4 | Main three rims proposed; displaced stretched ellipse removed. |
| collimating-newtonian-secondary.jpg | 179 | 4 | Still requires manual role identification. |
| 2.png | 244 | 9 | Rejected stretched interior fits; central circular details still require review. |
| post-330586-0-86207400-1592443472.jpg | 164 | 6 | Partial soft outer rim, focus/field advice; lower stretched artifact removed. |
| post-474648-0-99865000-1758374870.jpg | 104 | 3 | Stretched lower artifact removed; soft inner rim needs focus/review. |

The six overlays were also rendered for visual inspection. Source photos were
not modified. These observations are not calibrated accuracy results or optical
alignment certification. Nested reflection details can still be ambiguous, and
an eccentricity prior can reject a valid view with strong camera perspective.
No simulator-based optical or screw diagnosis has been added in this follow-up.

## Recognition follow-up plan (recorded before implementation)

The complete-chain gate hides every reference when one rim is soft, missing, or
close to another. Test all local source photos, not just synthetic concentric
layers. Replace the fixed radius-ratio identity rule with image-supported role
proposals: locate the bright primary face, allow adjacent secondary/primary rims,
and recover the outer circular focuser independently when the nested view supports
it. Soft but measurable rims remain visible estimates with focus advice; missing
roles remain explicit. Avoid classifying the small dark central reflection as the
secondary mirror or forcing three labels onto a two-edge view. Keep one suggested
outline per element and user confirmation. Add real-photo geometry and negative
regressions, inspect the named overlays, and record remaining failures honestly.

## Recognition follow-up result

The complete-triple prerequisite has been removed. Raw-image brightness, radial
consistency, a dark central obstruction, and rim-transition direction now anchor
the primary; nested layers remain a fallback. Missing secondary/focuser references
no longer erase it. Primary refinement prefers the outward darkening edge of the
bright face. The circular focuser is verified independently, including soft rims
and a context-specific radial search with 48% angular support for a partly visible
circle. Soft estimates retain their label and focus advice.

A bounded contour-window search can recover an occluded secondary after the
primary and focuser are found. Its refined geometry must contain the primary
within a 5% raster/fitting tolerance, lie inside the focuser, be separated from a
thin primary rim side, have at least 68% supported angular bins, and retain
substantial support away from both existing rims. General short-arc/noise/line
rejection remains strict. Normal review still shows one suggestion per element.
Capture advice reports the number of references found and names the next capture
problem in fully wrapped text.

The local audit now produces at least a primary suggestion on all 15 decodable
source photos; this is coverage, NOT 15 verified complete identifications. The
annotated native photo now proposes the displaced secondary near (200, 255),
radius 164, rather than the primary's other rim side. The soft orange-primary
photo now retains focuser/secondary/primary suggestions. The small grayscale view
recovers a partial circular outer rim. The blurred offset-secondary photo retains
focuser and primary but leaves secondary missing. The already annotated 2.png
retains primary/mark suggestions while focuser and secondary remain unassigned.
The tightly framed post-333184 view retains primary/mark only. Center-mark identity
can still be confused with a reflected peephole: suggestions require checking.

Resolution regression caught an important limit: resampling the partly merged
secondary can remove enough distinct support that it must stay missing. The test
requires mapped primary/focuser geometry and rejects forced secondary assignment;
it does not claim scale-invariant recovery of that secondary. Remaining work needs
labelled optical-role examples, uncertainty estimates and a physical forward model,
not progressively looser unconstrained ellipse fitting. No simulator diagnosis or
screw recommendations have been added.

Native-photo measurements and single-run processing timings are recorded in
DETECTION_VALIDATION.json (91–372 ms in this run). Source photos and saved user
options were not modified. Final automated validation is recorded in CONTINUATION.md.

## Round, shared-center guides plan — 2026-10-06 (before implementation)

User changes the guide contract: every outline must be a circle, with one shared
center; dragging any outline moves the group. Remove eccentricity from setup and
ignore legacy saved eccentricity values. Detection supplies a best-guess center
(prefer focuser, otherwise primary/largest observation) and per-element radii.
Keep the original detector observations separately in exported metadata so forcing
a concentric overlay cannot masquerade as measured optical alignment. Alternatives
inherit the shared center; manual point/three-point picks reposition the group.
Dragging translates all guide candidates together, preserves radii, clears checks
for the group and retains cumulative adjustments. Detect discards those adjustments
and reacquires the center/radii automatically. Replace independent image-offset
readouts and arc-evidence claims with shared-guide instructions. Verify roundness,
common center, legacy options, picks/replacements, multi-event dragging including
bounds and zoom/pan, blink/reset, exports and redetection. Existing raw detector
regressions remain as internal-observation tests. No commits or network services.

Steering during implementation: the master is the focuser observation if assigned;
otherwise use the largest boundary circle, not the primary. Replace optical-role
and alternative dropdowns with direct role buttons, circle-click selection and
previous/next alternative buttons. Clicking a visible rim selects its named role
immediately; dragging it still moves the group.

## Automatic tracking and advice flow — 2026-10-06 (before implementation)

New user contract supersedes confirmation workflow: Detect draws usable circles
immediately; missing roles are added manually. Live analysis tracks the camera
at a bounded rate without overlapping analysis workers or rendering a new image
with old measurements. Match manually supplied roles locally to supported new
observations; retain the manual guide if no good replacement exists. Retained
guides follow the detected master center and keep their radius. Explicit Detect
remains fresh acquisition; tracking preserves manual fallback roles. Freeze only
while picking/dragging, and resume tracking on completing/cancelling the gesture.

Missing circles prompt even illumination, focus and (for missing focuser) a wider
field. Once all roles exist, evaluate original observed geometry, not the forced
concentric guides. Prioritize camera seating/perspective, actual-secondary shape
and placement, then secondary aiming relative to the primary center mark. Circle
eccentricity alone must not imply a primary screw adjustment. Primary-axis advice
requires a trustworthy reflected pupil/Cheshire reference; otherwise request that
view/test rather than invent alignment. Include pixel-scale uncertainty and flag
manual, soft or ambiguous measurements. Physical screw directions/turns still
require calibration. Implement useful conditional next actions offline, retaining
image evidence and provenance for future integrated model work.

Validate tracking on changing synthetic frames, loss/recovery of manually added
roles, shared-master movement, no overlapping/stale analysis, interaction pause,
matching frame/overlay export, missing-role advice and measurement-based next steps.

## Implementation checkpoint — 2026-10-06

Automatic roles now draw immediately, without confirmation. Direct role buttons,
circle selection and arrow alternatives replace dropdowns. All displayed outlines
are thin complete circles with one master center: focuser first, largest boundary
otherwise. Manual secondary/mark picks preserve the existing master; a manual
focuser establishes it. Dragging translates the group; Detect resets overrides.

Live tracking pairs each accepted analysis with its exact raw frame. It keeps a
single worker/latest-frame slot, pauses during editing, and retains manual radii
when a nearby supported replacement is absent. Original independent observations
are kept for conditional next-action advice; forced guide geometry cannot imply
zero error. Held references, blur and partial evidence request better acquisition.
Advice covers camera seating, actual secondary shape/placement and aiming toward
the primary mark. Primary tilt still requests the missing reflected reference;
mechanical screw guidance and the calibrated integrated model remain future work.

The refreshed DETECTION_VALIDATION.json contains 14 current native images with
raw observations, round guides/master, roles and advice. Rendered overlays were
visually inspected. These unlabelled photos assess coverage, not optical accuracy.
Current design/limitations and automated results are in CONTINUATION.md.

## Direct sizing, hover feedback and tight focuser assignment — 2026-10-06 (plan)

Add minus/plus controls beside Change outline for the clicked role, and Ctrl+wheel
near a visible rim to resize that role without changing the group center. Plain
wheel remains image zoom. Treat sizing as a manual circular reference, retained
by tracking until a reliable fit replaces it; Detect discards these overrides.
Use a 12-display-pixel rim/center grab margin, show the move cursor on hover, and
allow gesture invalidation while a live analysis is in flight. Empty-image drag
pans. Give role controls the corresponding guide color with readable text/swatches.

The reported native photo has a well-supported outer circle (radius ~145) and
primary reflection (~126). The role rule requires ratio >1.3 and discards this
outer rim even though its contour is excellent. Permit a smaller, separated outer
rim only when its observation is nearly round, well supported and high quality;
retain circular pixel-evidence verification. Do not manufacture a secondary from
a primary rim side. Validate this photo, tight synthetic layers, rejection of thin
rim duplicates/unsupported shapes, sizing/reset/manual retention, hover/empty pan,
colors and regular-screen layouts. No commits; runtime remains offline.

Implementation: selected-radius −/+ and Ctrl+wheel sizing, 12-pixel hover/grabbing,
colored role controls and verified tight-focuser assignment are implemented. New
regressions exercise the reported native photo and the interactions. Current
behavior, validation and remaining limits are in CONTINUATION.md and DESIGN.md.

## Optional primary mark, reflected camera pupil and exact pixel radii — 2026-10-06 (plan)

Add Camera pupil as a separate optical reference with its own color, automatic
proposal from supported central nested camera detail, manual rim picking and live
retention. Do not label the whole dark secondary shadow as the pupil or reuse one
candidate as both center mark and pupil. Keep observed pupil coordinates separate
from the forced shared-center guides and use them in primary-axis advice. A clean
nested central opening is a heuristic proposal, not proof of optical identity.

Primary center-mark setup gains None. Unknown/None marks are optional; a specified
Ring/Spot/Triangle can request its missing mark. Missing marks do not block camera
seating or secondary placement. Without a mark, use the primary rim's center only
as an approximate aiming/reference estimate; request optical/star verification.
Pupil/mark comparison can give conditional primary tilt direction in image space,
never screw turns or a calibrated verdict. Lens pupil is not automatically a
calibrated Cheshire ring. Ambiguous/hidden pupils prompt focus/illumination or pick.

Replace percentage resizing with +/- one raw-image radius pixel and an editable
Radius (px) field. Enter applies a validated whole-pixel radius; invalid input keeps
geometry intact. Pause tracking during focused editing so typed values cannot be
replaced. Keep manual resizing retention, group center, other radii, pan/zoom and
Detect reset. Keep five colored role buttons in two rows and fit ordinary screens.

Validate no-mark persistence/import, pupil-versus-shadow/mark separation, pupil
loss/recovery and raw-coordinate metrics, optional-mark advice, approximate
unmarked-primary steps, exact +/-/wheel/entry pixels, invalid input, editing races,
export, layout and original camera/detection regressions. No commits, offline.

Implementation checkpoint: five colored roles and a separate red pupil are now
integrated with automatic detection, manual circular picking, tracking/retention,
guidance and raw export. None/Unknown makes the primary mark optional; a specified
shape still requests its missing mark before complete adjustment analysis. All
required references must be present before optical advice, matching the authorized
flow. Primary aiming without a mark uses an explicitly approximate rim center;
pupil alignment advice is conditional and requests a star check. Exact pixel
steps and numeric radius entry replace percentage resizing; typing pauses live
updates. Escape cancels and preserves intentional tracking pause. Validation:
118 run, 117 passed, one absent-photo skip. See CONTINUATION.md for the complete
checkpoint and limitations. Camera selection was confirmed working by the user.

## Camera feed independent of tracking and fullscreen startup — 2026-10-06 (plan)

Disabling Track live edges must stop edge analysis, not camera acquisition/display.
Keep held guide positions while the raw preview continues; enabling tracking
reanalyzes the same selected camera without reopening it or losing references.
Picking, radius entry and active drag gestures may briefly freeze the image for
accurate edits. Detect with tracking disabled should run once then resume preview.
Paused camera guidance must identify held measurements; capture metadata must
state that held observations are not measurements of the new live frame. Source
changes still invalidate old references and worker results.

Start the app in actual fullscreen, add a visible Windowed/Fullscreen control,
F11 to toggle and Escape to leave fullscreen. Preserve ordinary window geometry
and compact layouts; test hidden windows in windowed mode after checking startup.
Validate paused preview changes, no analysis while disabled, same camera/session
on resume, retained circles, export status, editing freezes, and fullscreen
startup/toggle/escape. No commits; no network runtime changes.

Additional report: unreliable live detection changes message heights and moves
controls beneath them, including the tracking checkbox. Put the tracking checkbox
in the stable upper action area and reserve fixed capture/selection message space.
Check rapidly alternating empty/blurred/complete detection statuses, unchanged
interactive control positions and no-scroll regular-screen layouts.

Implementation: tracking off now holds analysis/circles while live preview stays
running; enabling resumes the same camera. Temporary editing freezes remain
independent. Export marks stale observations and omits stale camera advice.
Fullscreen startup has F11, Escape and a visible windowed toggle. The tracking
checkbox sits before fixed-height status areas; role/size/pick controls stay
still across changing recognition. Complete/empty/blurred UI regressions and
regular-screen checks pass. Full validation: 120 run, 119 passed, 1 missing-photo
skip. Updated README, DESIGN and CONTINUATION describe current behavior.

## Independent absolute FOV crosshair — 2026-10-06 (plan)

Add a global FOV crosshair checkbox and Center FOV button outside the tabs. This
full-image reference is independent of the shared optical guide center and raw
measurements. User clarification: reuse the existing startup red crosshair,
default on, rather than add a second one. Render it once, spanning the visible
image with a draggable intersection; manual-circle visibility is separate. Store its
position in normalized full-frame coordinates so pan/zoom, window resize, live
tracking and Detect never recenter it. Reset view restores framing only; Center
FOV restores the full-frame center. Changing image/camera source recenters it.

Left-drag within 12 display pixels of its visible intersection moves only the
FOV crosshair; its intersection has priority if a circle center coincides. Circle
rims still move all optical circles; empty space and distant crosshair lines pan
the image. Picking mode disables reference dragging. Blink and Show overlays hide
it too. Do not treat the FOV crosshair as a detected optical/calibrated reference.
Export its visible setting and full-frame position without drawing into raw PNG.
Validate independent movement, overlay toggle/blink, pan/zoom/reset/source handling,
Detect/tracking retention, export and compact stable layout. Offline; no commits.

Implementation: the existing startup red crosshair is reused, default on, with
FOV crosshair/Center FOV controls. It moves independently via its intersection,
retains full-frame position through navigation/detection/tracking and resets on
new sources. Global overlay visibility/blink apply; raw export stays clean and
JSON records reference position. No duplicate red crosshair or extra circle.
Compact fixed four-line status/three-line selection and two-line mouse help keep
the global controls within regular-screen layouts. Validation: 123 run, 122 passed,
one missing-photo skip. See CONTINUATION.md for behavior and remaining work.

## Fast live rim tracking and motion-aware averaging — 2026-10-06 (plan)

Authorized after the detection-speed discussion: retain full offline Detect for
initial discovery, then update existing independently observed rims from bounded
local pixel evidence. Full detection recovers lost edges and periodically searches
for missing/new references; incomplete roles must not force an expensive full
search on every successful local update. Keep raw geometry, shared circular guide
projection, manual retention, frame/result pairing and stale-worker protections.

Use at most three recent captured frames spanning 120 ms, only when a low-cost
spatial motion/change check says the image is steady. Reset accumulation on camera/
mirror motion, illumination/focus changes, source/shape change and editing pauses.
Compute averages in the analysis worker, not on Tk. Analyze/display/export the
actual averaged image together; record sample count/mode. There is no old-frame
backlog, and noisy averaging never replaces optical identity/quality gates.

Reduce successful local update cadence from 350 ms to 100 ms, bounded by worker
speed. Validate noisy steady scenes, local mirror motion, averaging reset/age/
size/session, lost-edge reacquisition, role identity and raw-coordinate scaling,
manual hold/reset, latest-frame scheduling, matched averaged exports and pauses.
Benchmark full versus local native-photo tracking; document observed limits.

Also resolve the reported missing title bar: start maximized with normal Windows
decorations; optional F11 fullscreen remembers and restores prior window state.
Escape exits optional fullscreen. No commits; runtime remains offline.

## Validation decision — 2026-10-06

User instruction: stop doing unit tests and focus on integration tests only.
Effective immediately, do not add/run unit tests or unittest discovery. Keep
existing historical tests, but validate changes through complete app workflows
with real image analysis, camera/analysis threads, tracking, Tk interaction,
rendered output and export. Synthetic capture substitutes are allowed at the
hardware boundary; use native photos and actual production components together.
Record commands, user-visible outcomes and remaining limits. This overrides earlier
plans that requested pure function/unit checks or full discovery.

Coverage requirement added by the user: integration checks must retain the same
behavioral/failure-case coverage as the previous tests. Maintain a coverage map
from historical categories to end-to-end scenarios and report uncovered behavior.
Do not equate a smaller or equal test count with equivalent coverage.

Implementation checkpoint: local rim/detail tracking and conservative full fallback
are integrated in live_detection.py. The Tk acquisition loop accumulates only a
bounded steady batch; worker output pairs the actual average with results and
export metadata. Startup is maximized/decorated with optional fullscreen. Current
validation is the explicit integration runner; see CONTINUATION.md for results
and INTEGRATION_COVERAGE.md for the required equivalence work. Existing historical
unit files remain untouched as references and are excluded from this runner.
