# Astro Collimator

An offline desktop assistant for Newtonian collimation: acquire a focuser view,
detect optical edges, track adjustments, and show the next useful action.

## Run and verify

Install `requirements.txt` in a local Python environment, then run
`python astro_collimator.py`. It starts maximized with the Windows title bar.
**F11** enables optional fullscreen; **Escape** or **Windowed** restores the prior
window state. Run integration checks with `python -B run_integration_tests.py`.
Do not add/run unit tests or broad discovery. Integration tests must preserve the
previous behavior and failure-case coverage; see [coverage mapping](docs/INTEGRATION_COVERAGE.md).
For an offline installation, supply Python and dependency wheels beforehand.
The application makes no runtime network requests and requires no downloaded model.

## Use

1. Open **Telescope setup / Options**, enter known telescope dimensions and the
   primary center-mark shape, then save. Choose **None** for an unmarked mirror,
   or **Unknown** if unsure; both make the mark optional. Unknown dimensions can stay blank.
   Settings are saved in `options.json` beside the application.
2. Choose a camera and supported controls in **Camera**, or **Open image** in
   **Detect & review**. Seat the camera centrally and squarely in the focuser;
   show its inside rim, actual secondary face, and primary reflection.
3. Click **Detect edges / restart tracking**. Detected elements appear immediately,
   without confirmation: orange focuser, cyan secondary, green primary reflection,
   purple optional center mark, red reflected camera pupil (lens opening).
   At most one guide is shown per element. Missing elements
   stay missing; the panel recommends illumination, focus or a wider camera view.
4. Add a missing element with its direct **Focuser / Secondary / Primary / Center
   mark / Pupil** button and **Pick edge**: three well-spaced rim points, or one center-mark
   point. Click a visible circle to select it. **Change outline** offers previous/
   next alternatives if an automatic assignment is wrong; no dropdown is needed.
   Role buttons have matching guide-color swatches and text. Click a circle and
   use **− / +** beside Change outline for **one raw-image radius pixel** per step.
   Enter a whole number in **Radius (px)** and press **Enter** to set it directly;
   **Escape** cancels typing. Tracking pauses while editing the field.
   **Ctrl+wheel near a circle** also steps its radius by one pixel; repeated
   scrolling keeps editing that circle. Plain wheel still zooms the image.
5. With a live camera, **Track live edges** is enabled by default after Detect.
   The tool updates reliable existing edges locally (100 ms minimum cadence),
   with full detection on failure and periodically for missing/new references.
   Up to three recent frames spanning 120 ms are averaged while steady; motion or
   local image changes clear accumulation. The actual analyzed image is displayed
   and exported, with mode/sample count in JSON. Manual
   references are replaced only by a sufficiently good nearby fit; otherwise
   their radius is retained and they move with the shared center. Picking and
   dragging pause updates. **Disabling tracking keeps the camera feed running**
   and holds the circles; re-enabling resumes analysis on the same camera.
   The checkbox stays above detection messages, and fixed message areas keep
   interactive controls still when recognition changes.
6. Read the next-action instruction after all required circles are present
   (three rims and the pupil, plus the mark if its shape is known). It uses
   original measured outlines, rather than the forced guide geometry. Advice can
   request better acquisition, square camera seating, secondary placement/
   rotation, secondary aiming, or conditional primary tilt using the observed
   pupil position relative to the mark. Without a mark, rim-center estimates are
   approximate. Follow one small adjustment, then let tracking measure the new view.
7. **Save capture** saves an original-resolution PNG without overlays plus JSON
   containing setup, raw observations, guides, assignments, manual references,
   tracking state and advice. With tracking off, the PNG is the current live image;
   metadata flags held observations as not matching it and omits stale advice. Reopening the PNG reanalyzes it; automatic restoration
   of its JSON state is not implemented.

All displayed outlines are complete circles with one shared center. The detected
focuser is the master; without it, the largest boundary supplies the center.
Adding a secondary or mark keeps that center. Adding a focuser sets a new master.
**Dragging any circle moves the entire group**; it does not rewrite measured
optical positions. **Detect** discards manual overrides and starts a fresh guess.
Guide concentricity is a viewing aid, not proof of alignment.

A move cursor appears within **12 display pixels** of a visible rim or center;
you do not need to click precisely on the line. Empty space uses ordinary image
navigation. Resizing changes only the selected radius, keeps the common center,
and creates a manual reference that tracking can retain or replace with a good fit.

Wheel zoom follows the cursor. **Left drag on empty space pans**; middle drag
always pans. **Hold the right button to hide overlays; release to restore them**.
**Reset view** or **Ctrl+0** restores the full image without discarding references.
The startup red crosshair has a separate **FOV crosshair** checkbox above the
tabs. **Left-drag its intersection** (12-pixel grab margin) to move only that
reference; circle rims still move the guide group. **Center FOV** returns it to
the full-image center. Its raw-image position stays fixed through zoom/pan,
Reset view, Detect and tracking; changing source recenters it. Blink and Show
overlays also hide it. Manual guides retains its separate circle size/center controls.

## What advice can establish

Guidance is provisional and based on image heuristics. Manual three-point circles
cannot measure actual oval distortion. Held manual references, soft or incomplete
mirror observations defer adjustment advice until better evidence is available.
Automatic identities can still be wrong, particularly at merged rims or reflected
camera details; correct those with a direct pick or alternative outline.

The pupil detector looks for a smaller opening inside a larger dark central
reflection; it does not use the entire secondary shadow or reuse the same detail
as both pupil and mark. Check this identity against the image. A camera pupil is
not a calibrated Cheshire reference. Pupil/mark advice assumes a centered, square
camera; unmarked-primary estimates use a wider pixel threshold and require optical
verification. Verify with a star test; the app does not certify alignment or
infer physical screw directions. Mechanical focuser squaring, physical
error tolerances and screw-specific adjustments need further calibration.
No simulator or inverse optical model has been ported yet.

## Development checkpoint

[Design](docs/DESIGN.md), [continuation](docs/CONTINUATION.md) and the plans in
[detection improvements](docs/DETECTION_IMPROVEMENTS.md) document implementation,
validation and subsequent work. No commits or Git operations were performed.

The historical baseline was **123 tests run, 122 passed, 1 skipped**. Current
validation uses the explicit integration runner; historical component tests are
kept as the coverage reference. [Coverage mapping](docs/INTEGRATION_COVERAGE.md)
records the required equivalents and remaining migration gaps. A passing run
alone is not a claim of identical coverage.
Real telescope validation remains necessary.
