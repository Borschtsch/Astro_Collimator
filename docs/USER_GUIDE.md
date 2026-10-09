# Collimating a Newtonian telescope

Astro Collimator compares optical references in a camera view through the
focuser. It helps you see changes as you adjust the telescope and suggests the
next useful step. Confirm the final alignment optically with a star test or an
appropriate collimation tool.

## Prepare the view

Seat the camera centrally and squarely in the focuser. Use even illumination
and focus on the visible mirror edges. Include the inside focuser rim, the
secondary mirror face and the primary mirror reflection.

In **Telescope setup / Options**, enter known dimensions and the primary
center-mark shape. Select **None** for an unmarked primary, or **Unknown** if you
are unsure. A center mark is optional for those settings; unmarked-primary
guidance is approximate.

## Detect and adjust

At startup, the image shows only the FOV crosshair. Guide circles appear after
detection or when you select **Manual guides**.

Select **Detect edges / restart tracking**. Recognized references appear
immediately, without a confirmation step.

| Reference | Color | What to identify |
| --- | --- | --- |
| Focuser edge | Orange | Inside rim of the focuser or sight tube |
| Secondary edge | Cyan | Actual edge of the secondary mirror face |
| Primary reflection | Green | Primary mirror edge reflected in the secondary |
| Center mark | Purple | Mark on the primary mirror, when present |
| Camera pupil | Red | Reflected camera lens opening |

The dark reflected secondary silhouette is not the secondary edge or the camera
pupil. Its apparent offset does not by itself indicate poor collimation.

If a reference is missing, improve illumination or focus. Widen the camera view
if the focuser rim is outside the image. To add a missing reference, select its
colored button and **Pick edge**, then click three well-spaced rim points. The
center mark needs one click. **Change outline** offers alternatives when the
automatic assignment is wrong.

Follow the next-action instruction and make one small adjustment at a time.
With a live camera, **Track live edges** redraws measured references as the view
changes. A manually added reference stays in place until a suitable detected
edge can replace it. Disabling tracking keeps the camera stream running and
holds the last measured circles. **Detect** starts a fresh detection. Configured
manual guide sizes remain available for edges the detector cannot find.

## Manual guides

Use **Manual guides** for a quick visual comparison when an edge is missing.
Detected circles keep their measured sizes. Missing guides start around those
references: orange focuser outside cyan secondary, with green primary reflection
inside. If only the secondary is detected, it anchors both starter sizes. With no
detection, the tab provides three nested presets.

Resize a guide with its slider, **− / +**, or scrolling over its control. Detected
circles can be resized here too. Drag a rim to move the shared center. A resized
missing guide keeps its size when you switch tabs, zoom or restart detection.
Entering Manual guides reveals all three circles. They remain visible when you
return to Detect & review, alongside any recognized edges. Before you use Manual
guides, automatic detection shows only recognized references. Opening a new image
or switching the camera resets the guide setup for that source.

Missing presets are visual estimates and do not count as measured edges for
alignment advice. To include a missing reference in tracking and analysis, use **Pick edge** in Detect & review.

## Inspect the image

All guide circles are round and share one center, using the focuser as the
reference when detected. These overlays help you compare edges; they are not
proof that the optical references are aligned. Guidance uses the independently
measured outlines beneath them.

| Action | Control |
| --- | --- |
| Select a circle | Click near its rim or use its colored button |
| Move the circle group | Left-drag any circle |
| Change radius by one image pixel | **− / +**, or **Ctrl+wheel** near the circle |
| Enter an exact radius | Type **Radius (px)**, then press **Enter** |
| Cancel radius entry | **Escape** while editing |
| Zoom | Mouse wheel |
| Pan | Zoom in, then left-drag empty space or the black image margin; middle-drag also works |
| Blink between image and overlays | Hold the right button; release to restore |
| Reset zoom and pan | **Reset view** or **Ctrl+0** |
| Show or hide overlays | **Show overlays** |
| Show or hide the full-field crosshair | **FOV crosshair** |
| Move the full-field crosshair independently | Left-drag its intersection |
| Recenter the full-field crosshair | **Center FOV** |
| Enter or leave fullscreen | **F11** |
| Leave fullscreen | **Escape** or **Windowed** |

A move cursor appears near an editable rim; exact pixel placement is not
necessary. Moving the guide group does not change the measured optical centers.
The full-field crosshair is an independent viewing reference.

## Save a session image

**Save capture** writes an original-resolution PNG without overlays and a JSON
file containing the telescope setup, measurements and current guidance. Keep
both files together. Reopening the PNG runs detection again; the JSON does not
automatically restore the previous session.

When tracking is paused, the saved image comes from the current camera stream.
The JSON marks held measurements as stale and omits guidance for that newer image.

## Interpreting the guidance

The tool may recommend improving the capture, seating the camera squarely,
adjusting secondary placement or rotation, aiming the secondary, or making a
small primary-tilt adjustment using the observed pupil position.

Ambiguous, blurred or incomplete edges can prevent reliable guidance. Manual
three-point circles cannot measure true oval distortion. Automatic identities
also need a visual check, especially where mirror rims overlap.

Pupil-based guidance assumes a centered, square camera. The camera pupil is not
a calibrated Cheshire reference, and primary-rim estimates without a center
mark are approximate. The application does not identify individual adjustment
screws or certify collimation. Verify the result with a star test before relying
on the telescope's alignment for imaging.
