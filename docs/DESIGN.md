# Offline Newtonian collimation assistant

Original plan recorded before implementation, 2026-10-04. Current contract updated
2026-10-06. Earlier plans and checkpoints are retained in DETECTION_IMPROVEMENTS.md
and CONTINUATION.md as history; the current contract supersedes confirmation,
independently movable displayed centers and a user-configurable eccentricity limit.

## Product contract

- Newtonian focuser views only; all runtime work stays offline.
- Telescope dimensions and camera/mounting notes belong in saved setup/options.
  Unknown dimensions remain unknown. Do not assume a particular telescope model.
- One integrated collimation tool; no separate simulator website or unrelated UI.
- No commits, staging, initialization or Git operations.
- Compact supported camera controls; no camera-value acknowledgement messages.
- Start maximized with a visible Windows title bar. F11 enables optional fullscreen;
  Escape/Windowed restores the remembered normal/maximized state.

Setup -> acquire -> Detect -> immediately draw -> add missing circles manually ->
track changes -> recommend the next capture or optical action. No confirmation step.

## Observations and guides

Five available roles: inside focuser rim, actual secondary face edge, primary
reflection edge, optional primary center mark and reflected camera pupil (lens
opening). Never substitute the dark secondary shadow for its actual face or for
the pupil. Setup None/Unknown makes the mark optional; Ring/Spot/Triangle requires
a mark for complete analysis. None suppresses automatic mark proposals.

The pupil heuristic requires a supported round opening inside a larger dark
central reflection, with size, centering, containment and intensity contrast
checks. It never proposes a lone center dot as a pupil. A proposed pupil cannot
share an ID with the mark; an alternate mark must lie outside the pupil detail.
Round lens contours are retained even for a Triangle mark profile. These tests
reduce ambiguous assignments but cannot prove identity from a photograph.
Native post-333184 now identifies its inner opening as Camera pupil rather than
a primary mark. Unresolved pupils request focus/illumination or manual picking.

Analysis always consumes an immutable raw BGR frame, before overlays or cropping.
The observation engine keeps independent centers, semiaxes, orientation, support,
residual, softness and provenance. Appearance, radial transition direction and
nested geometry suggest roles independently; missing roles do not erase others.
These assignments are heuristic, not proof of optical identity.

The public detector projects observations into **round concentric guides**.
Each guide radius is the geometric mean of the observed semiaxes; axes are equal,
angle is zero. Its center is the observed assigned focuser center, otherwise the
largest boundary center. Full circles extrapolate missing arcs. The absolute FOV crosshair is a separate
viewing reference, never a fitted guide or input to alignment advice. Only one assigned
circle per role is drawn; alternative hypotheses remain internal/exported.
Guide fit scores/support are cleared rather than misrepresenting constrained
geometry as a measured fit. Original observations remain separate for advice.
There is no user eccentricity setting; legacy saved values are ignored on load.
Internal oval fitting remains necessary to assess actual distortion.

Click a visible rim/center or a direct role button to select an element. Change
outline uses previous/next alternatives, replacing only that role. Three clicks
add a manual circular rim; one click adds the mark position. A manual focuser
establishes the master center; another role keeps the existing master unless no
focuser exists and the new boundary is larger. Dragging any circle translates all
guides and saves a group offset without changing underlying observations.
Explicit Detect clears overrides/offsets and fits the raw image again.

## Live tracking

Detect starts tracking when the camera and Track live edges are enabled. A latest-
frame slot feeds one bounded analysis worker. Successful local rim/detail updates
run at a minimum 100 ms interval; full-only scenes retain a 350 ms minimum. Local
tracking uses independently measured raw observations and fresh pixel evidence;
failed quality/identity/proximity checks fall back to full detection. Full discovery
also runs every 1.5 seconds for missing/held required references, otherwise every
3 seconds. Slow analysis reduces cadence; it does not build a queue.

A small motion/change check admits at most three captured frames over 120 ms.
Camera motion, local detail/illumination changes, source/size/time gaps and editing
reset accumulation. Averaging runs in the analysis worker. Accepted averaged
frames are displayed/exported together with their results; capture JSON records
analysis mode and sample count. Soft/manual references require full reacquisition. Each accepted result carries the exact
frame analyzed, which becomes both the displayed and exported image. Camera and
analysis workers never access Tk; session/generation tokens reject stale results.

Manual references are matched against new raw observations. A replacement needs
a compatible optical kind (boundary, mark or pupil), fit quality >=0.65, available coverage >=0.6,
transition width <14 analysis pixels, radius ratio 0.8–1.2 and center distance
<=max(6 px, 25% of old radius). One-point marks omit the radius-ratio condition.
Matches cannot steal a candidate assigned to another optical role. These are
prototype image thresholds, not calibrated optical tolerances.

Without a reliable match, retain the manual radius, translate its observation
with master-center motion and label its provenance manual_hold. Guides remain
concentric. A later reliable match reacquires the reference. Lost automatic roles
are not silently retained. Original manual click arrays are not reused on newer
frames; current manual references and held state are exported instead.

Picking and mouse gestures pause tracking and invalidate in-flight results.
Disabling tracking stops analysis and invalidates in-flight results while raw
camera acquisition/display continues. Guides keep their previous positions.
Enabling resumes analysis on the same camera/session without reopening it. Picking,
radius entry and active drag gestures temporarily freeze the image independently
of the tracking checkbox. A one-shot Detect while tracking is off unfreezes the
camera view after applying the result. Source/profile changes invalidate
results and clear tracking state. Resolution changes within one camera session
are not calibrated; restart Detect after changing acquisition resolution.

## Advice

Missing roles request illumination, focus, manual addition, and a wider field if
the focuser is absent. Short capture status and next-action labels wrap without
scrollbars. All required references enable analysis of **raw observations**, not the
forced concentric guides. Missing raw data, held manual references, soft mirror
edges, incomplete mirror support or a clipped focuser request better acquisition.

With sufficient observations, similar oval distortions first suggest seating and
centering the camera squarely. An oval actual secondary suggests checking camera
seating and secondary rotation. Secondary-center displacement from the focuser
suggests apparent placement/rotation toward the focuser center. Primary-mark
displacement from that center suggests secondary tilt, with direction described
in displayed image coordinates. These are conditional heuristics; a photograph
does not uniquely identify mechanical causes or physical screw directions.

The image uncertainty threshold is max(3 raw pixels, 1.5% of focuser radius,
0.75 times measured transition width). Width is retained in analysis pixels;
this threshold is deliberately provisional, not a millimeter calibration.
Manual circular picks retain measured positions but cannot establish eccentricity.
Guide dragging never produces artificial zero-error recommendations.
Resizing replaces the selected raw reference with manual circular geometry at its
original observed center, clears fit evidence, and records manual_resize provenance.
Other raw observations and the shared guide center remain unchanged. Its new
radius enters the existing tracking retention/reacquisition rules.

Secondary aiming uses the mark when present, otherwise the raw primary rim
center with uncertainty max(2 times the normal pixel threshold, 3% of primary
radius). After placement and aiming, compare the independently observed pupil
with that same primary reference. A soft, clipped or incomplete pupil defers
primary advice. An offset suggests small primary-tilt changes moving the apparent
pupil toward the mark/estimated rim center, conditional on square centered camera
seating. Directions describe screen motion, not physical screws. No mark means
explicitly approximate advice. Within-threshold references still request star
verification, never a success certificate. The pupil is not a calibrated Cheshire
ring; telescope validation and camera geometry remain necessary. Mechanical focuser squaring
needs an external geometric reference; do not infer it from nested circles.

## Navigation and layout

Wheel zoom is cursor anchored. Left dragging empty space pans; dragging a circle
moves the common center. Middle drag always pans. A five-pixel gesture threshold
distinguishes clicks. Hold right to hide overlays; release or focus loss restores
them, preserving the Show overlays preference. Reset view/Ctrl+0 restores the full
image without losing roles. Display transforms map picks to uncropped raw pixels.
Thin orange/cyan/green/purple/red guides and shared-center markers limit clutter.
The existing startup red full-field crosshair is drawn once, independently of
the guides. Its FOV crosshair checkbox and Center FOV button remain above all
tabs. Visibility defaults on; the old Manual guides visibility only controls its
manual circles. Position is a normalized fraction of the full raw frame, mapped
through DisplayTransform when rendering. Pan/zoom/window resize, Reset view,
Detect, guide movement and tracking preserve that position. Image/camera source
changes reset it to (0.5, 0.5). Center FOV restores that position without moving
guides or framing. It is not a physical field-angle/optical calibration.

Left-drag within 12 display pixels of the crosshair intersection moves only the
FOV reference; the intersection takes priority over a coincident guide center.
Ctrl+wheel still hits circles for sizing. Farther portions of the crosshair lines
do not intercept ordinary image panning. Picking, hidden overlays and blink
disable dragging. The image briefly freezes during the gesture, then resumes.
The thin red lines have a black halo and no additional circle/duplicate crosshair.
Role buttons use matching color swatches and darker readable text of the same hue;
selected −/+ and radius entry inherit that hue. Five role buttons fit in two
rows. The compact toolbar includes an editable Radius (px) field; Enter or focus
loss applies a valid whole raw-image radius, Escape cancels, invalid input leaves
geometry unchanged. Limits are 1 pixel for a mark or 2 for other roles, up to twice
the longest image dimension. +/- and Ctrl+wheel near a rim step by one pixel; a same-position wheel gesture keeps editing the same
role as the rim moves. Plain wheel keeps image zoom. The grab margin is 12 display
pixels, independent of zoom/raw resolution. Round-rim hit testing uses continuous
geometry rather than sampled points so the tolerance stays forgiving at high zoom. Hover shows the move cursor near a
rim/center, including during live analysis; empty-space drag pans. Picking shows
a crosshair cursor. Hidden overlays cannot be grabbed. Entry editing pauses
tracking and invalidates in-flight results; finishing preserves a deliberately
disabled-analysis state while the camera preview resumes. Gestures cannot
unfreeze the view while the entry is edited. The tracking checkbox is packed
before capture messages. Capture messages reserve four lines; selection messages
reserve three lines. Their changing content cannot move the role/size/pick
controls. Padding and concise help preserve 1280x720 and 1024x768 layouts.

## Saved data and architecture

options.json beside start.py (source) or the portable executable stores telescope name, aperture/focal length,
secondary minor axis, focuser diameter, known offset, mark shape, camera description
and mounting notes. Optional numeric values must be finite and physically valid.
Options are saved atomically via a flushed temporary file and os.replace.
Telescope parameters are not sufficient to derive apparent pixel radii without
camera geometry; current advice does not use them to infer millimeters.

- start.py / source/launcher.py: shared source and packaged entry.
- source/app.py: app shell, camera ownership, display transforms and gestures.
- source/collimation_review.py: role editing, analysis scheduling and capture import/export.
- source/feature_detection.py: observation fitting, role proposals and concentric projection.
- source/edge_tracking.py: bounded manual-reference matching and retention.
- source/collimation_guidance.py: pure provisional next-action advice from observations.
- source/app_options.py / setup_dialog.py: validated saved telescope setup.
- source/camera_properties.py: Windows capability queries and supported control ranges.

Analysis resizes to at most 960 pixels on the longest side and returns raw image
coordinates. CLAHE, blur, Canny, contours/arcs and radial intensity fitting generate
bounded hypotheses. Focuser proposals use circular intensity verification;
secondary recovery requires separated supporting arcs rather than a nearby rim
side. The outer-focuser role size gate normally uses 1.3 times the primary radius;
a tight clean rim can qualify above 1.08 with >=4 analysis pixels separation,
eccentricity <=0.2, quality >=0.85, coverage >=0.8 and transition width <14.
The separate circular pixel-evidence check still verifies the proposal. This
recognizes the reported post-333184 photo's 145/126 radius ratio automatically;
it does not infer a missing secondary or prove optical identity. General raw fitting retains a fixed eccentricity bound of 0.55. This is an
internal hypothesis limit, not the geometry of the displayed guides. Detector
performance and limitations should be assessed on labelled real views.

Capture export is adjacent raw PNG + schema-1 JSON containing setup, detections
(observations and guides), selections, manual references/adjustments, tracking and
advice. No confirmation list. During active tracking, export is paired to the
analyzed snapshot. With tracking disabled, export uses the current raw preview;
observations_match_image is false once newer frames arrive, and stale camera
advice is omitted. The UI says the circles hold their last measurements. This
metadata flag prevents held geometry being mistaken for analysis of the saved
new image. FOV crosshair visibility, normalized center and raw-image center are
exported separately as viewing metadata; the PNG never contains it.
The two-file write is not an atomic transaction;
partial failure reports the saved image. PNG import reanalyzes; JSON restoration
is future work.

## Validation and next work

Current policy (user decision, 2026-10-06): **integration tests only**. Do not add
or run unit tests or broad unittest discovery. Validate actual app workflows
including acquisition, worker scheduling, image detection/tracking, Tk gestures,
rendering and capture export. Hardware-boundary capture substitutes are permitted;
use real production components and native photos for the rest. Historical unit
results below document earlier work and are not the current validation workflow.
The same behavioral/failure-case coverage is required. Use the explicit runner
`python -B scripts/test_integration.py`; [INTEGRATION_COVERAGE.md](INTEGRATION_COVERAGE.md)
maps previous categories and gaps. Equivalent coverage is not yet certified.

Historical baseline and coverage (superseded validation command):

Tests cover raw independent geometry, circular shared-center projection/master
selection, missing/soft/partial images, role editing, direct gestures, layouts,
live frame/result matching, retained/reacquired manual references, worker races,
conditional guidance, persistence, export and camera behavior.
2026-10-06: 123 run, 122 passed, one absent-photo skip, Windows/Python 3.13.
New checks cover optional-mark persistence, pupil/mark/shadow separation, pupil
retention/reacquisition, raw pupil offsets and approximate unmarked advice, exact
pixel steps/entry validation, editing races, compact layout and pupil export. Camera checks cover
continued changing raw preview with tracking disabled, held circles/no new
analysis, same-session resume, paused export validity, former fullscreen startup/toggle
and fixed interactive control positions across complete/empty/blurred results.
FOV checks cover existing startup visibility, toggle/blink, independent dragging,
full-frame coordinates under navigation, circle-group independence, tracking/Detect
retention, source reset, global controls and overlay-free raw capture export.
See DETECTION_VALIDATION.json for the current native-photo audit and
[DETECTION_OVERLAYS.png](DETECTION_OVERLAYS.png) for inspected guide renders. No synthetic
fixtures or unlabelled photos establish real telescope accuracy.

Next: labelled optical views and camera seating/orientation calibration; reliable
pupil/mark identity and reflected-reference calibration; measured screw responses;
then integrate selected pure forward-model functions where they improve advice.
The astro-toolbox model is a forward model, not a photograph inverse solver.
Port numerical cases with parity checks, telescope dimensions and camera geometry
before presenting screw amounts or directions. Do not bundle a separate simulator.

## Developer references (no runtime dependency)

- Donald E. Pensack's CATSEYE-hosted guide distinguishes secondary placement,
  secondary tilt toward the primary mark and primary checks using a reflected
  reference; the reflected secondary shadow need not be concentric:
  https://catseyecollimation.com/pensack.pdf
- CATSEYE-hosted McCluney optical explanation of pupil/primary mark alignment:
  https://catseyecollimation.com/mccluneytext.html
  A plain camera reflection is not automatically a calibrated Cheshire target.
- CATSEYE FAQ on collimation and focuser checks:
  https://www.catseyecollimation.com/ceyefaq.html
- OpenCV contour/ellipse APIs:
  https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html
- Potential forward-model source, not currently ported:
  https://github.com/Borschtsch/astro-toolbox/tree/main/collimation
