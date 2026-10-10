# Collimating a Newtonian telescope

Advanced Astro Collimator compares optical references in a camera view through the
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

Select **Detect edges and align image**. Recognized references appear
immediately, without a confirmation step. Reliable straight vanes also trigger
image alignment; unclear vanes leave rotation unchanged.

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
center mark needs one click. The detector draws its most likely circle for each
identified reference. Click a circle or its colored button, then adjust its
**Radius (px)** by typing, dragging, or using −/+. Drag any guide circle to move
the shared center. Use **Pick edge** to replace a guide from visible rim points.

Follow the next-action instruction and make one small adjustment at a time.
With a live camera, **Track live edges** redraws measured references as the view
changes. A manually added reference stays in place until a suitable detected
edge can replace it. Disabling tracking keeps the camera stream running and
holds the last measured circles. **Detect** starts a fresh detection. Configured
manual guide sizes remain available for edges the detector cannot find.

## Spider vanes and rotation

View controls appear first, followed by the **FOV Crosshair** group and the tabs.
The group remains available in Detect & review,
Manual guides and Camera. Its checkbox enables the reference and its controls;
the blade switch sits beside it. **Center**, **Auto-align** and the Rotation control
share the row inside the group. Image rotation and Reset view stay available when the
crosshair is disabled. The application starts in a maximized window with its
title bar and normal window controls.

**Image rotation** rotates the displayed image and its overlays around the
crosshair intersection. It keeps the current scale at every zoom level; rotated
edges can extend beyond the viewport. **Rotation** in the FOV Crosshair group rotates only the
crosshair relative to the image. **FOV Crosshair** shows or hides this single
reference. The small white crosshair marks the shared guide-circle center and
appears only when circles are visible; it follows their movement independently
of FOV position and visibility. Its angle and blade count always match the FOV
crosshair, including after Auto-align. The FOV crosshair has its own center,
independent of the guide circles. Moving it or the circles leaves image pixels
fixed. Each new image-angle adjustment rotates around the crosshair's current
displayed intersection.

Drag an angle horizontally to adjust it. Hold **Shift** while dragging for
**0.01° per pixel**; ordinary dragging gives 0.1° per pixel. You can also type an
angle to two decimal places and press Enter. The **− / +** buttons beside each
rotation field adjust it by **0.01° per click**. Angles increase clockwise. Reset
view restores pan and zoom, clears both rotation angles and centers the FOV
crosshair without moving the guide-circle center. Opening another
image also resets the view and both angles.

Detection selects three blades only when it clearly finds three straight,
evenly spaced vanes converging on a common center. Other designs and uncertain
images use four blades. Click **3 blades / 4 blades** to switch manually; this
choice stays in effect during tracking until you select Auto-align or change
the image source. The Auto-align button shows **Aligning…** while working, then returns to its
normal label without a success announcement; uncertain
images retain useful capture advice without announcing a vane count.

**Auto-align** measures the current raw image and rotates the displayed image
around the FOV center until the detected straight vanes match the crosshair.
The crosshair stays visibly fixed, and its angle entry stays unchanged. Zoom,
both reference centers and the optical measurements are preserved. **Detect
edges** performs this alignment too when reliable vanes are found. It recognizes light and dark supports and tolerates a partly
obstructed fourth vane. If competing background patterns, curved supports or
blur prevent a reliable result, it retains your angles and explains the next
step. Background tracking updates vane evidence and blade shape, keeping your
rotation settings; live tracking does not continuously realign the image. Vane alignment is a visual reference, not proof of mirror
alignment.

Saved images retain their original pixels. The accompanying JSON records image
rotation and its applied pivot/translation, crosshair angle, alignment
compensation and position, vane
evidence, blade shape and reference visibility.

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
| Drag the radius value | Drag **Radius (px)** horizontally: 1 image pixel per screen pixel; hold **Shift** for 1 per 10 |
| Cancel radius entry | **Escape** while editing |
| Zoom | Mouse wheel |
| Pan | Zoom in, then left-drag empty space or the black image margin; middle-drag also works |
| Blink between image and overlays | Hold the right button; release to restore |
| Reset zoom, pan and both rotation angles; center FOV | **Reset view** or **Ctrl+0** |
| Show or hide overlays | **Show overlays** |
| Enable or disable the crosshair and its controls | **FOV Crosshair** |
| Move the FOV crosshair | Left-drag its intersection |
| Recenter the FOV crosshair | **Center** |
| Enter or leave fullscreen | **F11** |
| Leave fullscreen | **Escape** |

A move cursor appears near an editable rim; exact pixel placement is not
necessary. Moving the guide group does not change the measured optical centers.
The circles share one guide center; the FOV crosshair is a separate viewing
reference. Overlay lines are antialiased for smoother edges.

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

The Camera tab lists device names reported by the operating system, followed
by their camera index. If a name is unavailable, the selector shows Camera N.
Refreshing preserves the selected index when that device is still available.

Rotation controls use the same order as radius adjustments: **−**, label,
editable value with **°**, **+**. The buttons change rotation by 0.01°.

## Phone camera

Choose **Stream from the phone** in the Camera tab to connect through a local QR
link. Choose existing photos without certificate installation, or use the browser
camera for photos and video over local HTTPS. See [Phone camera](PHONE_CAPTURE.md) for connection, certificate
comparison and desktop controls.
