# Phone camera

Use your phone for focuser-view photographs or a live camera feed. The computer
receives everything directly on the local network. No account, internet service
or phone app is needed. The phone shows camera controls and a plain preview;
collimation overlays and analysis stay in the desktop application.

## Connect

1. Connect the computer and phone to the same Wi-Fi or hotspot.
2. In the **Camera** tab, select **Stream from the phone**.
3. Scan the large QR code in the main image view with the phone and open its link. If the computer has several
   network adapters, select the address for the network shared with the phone.
4. Tap **Open camera** for the browser preview, then **Take photo** or **Send video**.
   **Choose photo** sends an existing image.

**Take photo** captures directly from the browser preview, without opening the
phone's camera app. The browser uses native still capture when available, or
sends a lossless PNG of the complete preview frame. Native still capture may
provide higher resolution than the preview. Browser photos and video use the
same HTTPS camera permission. **Choose photo** works on HTTP and sends an existing
file without resizing or recompression; orientation and HEIC are decoded locally.
Transfer progress and a receipt appear on the phone.
Photos may be up to 25 MB and 60 megapixels. A new photo resets the desktop view
and starts edge detection and image alignment automatically.

Receiving a photo or video replaces the QR with the image. Use **Show QR** in the
Camera tab to show the connection again, and **Show image** to return without
losing your circles, zoom or rotation.

The QR starts with HTTP for straightforward photo transfer. HTTP transfers are
unencrypted on the local network; use a network you control. The URL contains
a random pairing token. It changes whenever the phone source is restarted.

## Camera zoom

After opening the browser camera, **Camera zoom** uses the camera-reported
minimum, maximum and step. The same zoom applies to browser photos and live video.
An unsupported camera/browser leaves the slider disabled. If a change is rejected
or ignored, the control returns to the actual zoom and explains the problem.
The app does not enlarge/crop the preview to simulate camera zoom.

Optical zoom can be used when the phone/browser exposes it through the camera
track. The API does not identify whether a particular zoom value uses lens
movement, lens switching or digital processing; optical-only zoom cannot be
guaranteed. Some phones expose less control to browsers than to their camera app.
See the [camera zoom specification](https://www.w3.org/TR/image-capture/).

## Browser camera and certificates

**Open camera** or **Send video** opens this computer's local HTTPS address. If the browser accepts
that connection, tap the button again and grant camera permission. Certificate
installation is not required by the app, but some browsers require a trusted
certificate before enabling their camera. A browser warning exception does not
guarantee camera access. **Choose photo** remains available on the original HTTP link.
See [browser camera requirements](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).

The app generates its root and server certificates locally, on your computer.
No shared certificate or private key is distributed with the app. It never
changes the computer's or phone's trust settings automatically.

If your phone requires certificate trust and you choose to set it up:

1. On the computer, click **Compare certificates** in the Camera tab.
2. On the phone, open **Connection and certificate details**. Compare the full
   SHA-256 fingerprints with the computer. Both the server and root are shown.
3. Check the **server certificate** fingerprint in the browser's certificate
   details before accepting that connection. Check the **root certificate**
   fingerprint in the phone's certificate/profile details before trusting it.
   The downloaded page's numbers alone are not verification of its identity.
4. Download the public root certificate, or the optional iPhone/iPad profile,
   from that section. Install it only if the identity matches and you intend
   to trust this computer. Android installation menus vary by manufacturer.
5. On iPhone/iPad, a manually installed root also needs full trust enabled in
   **Settings → General → About → Certificate Trust Settings**. The supplied
   profile contains only this root certificate, with its fingerprint in the
   description. It is unsigned; no management or other settings are included.
   See [Apple's manual trust instructions](https://support.apple.com/en-us/102390).
6. Reopen the HTTPS link, allow camera access and tap **Send video**.

Remove the certificate/profile from your phone when you no longer want to trust
this computer. Managed phones may prohibit user-installed certificates or camera
access; photo transfer is the fallback.

Certificates live in `phone-link/` beside `options.json`. The local root persists
between sessions; the server certificate is renewed when the receiver starts,
so its fingerprint may change. Private keys stay on the computer and are never
served. Keep that folder private and exclude it from shared copies and releases.
If intentionally resetting an expired or damaged identity, close the app, remove
that folder and remove the old root/profile from the phone. Reconnect and compare
the newly generated fingerprints. A certificate error leaves HTTP photos usable.

## Desktop controls

Phone video uses the same detection, tracking, guide editing, zoom, pan, blink,
rotation and capture export as a local camera. **Track live edges** controls
analysis, without stopping incoming video. Camera gain/focus controls are hidden
for the phone; adjust focus/exposure on the phone instead.

Frames are sent one at a time, normally up to about 10 per second, and only the
newest received frame waits for processing. Actual speed depends on the phone,
network and computer. Edge analysis runs independently and averages steady frames
using the existing live detection pipeline: at most three steady frames over
350 ms for phone video (120 ms for local cameras). Motion or brightness changes
clear the average. This is a JPEG frame feed rather than
WebRTC or an audio stream.

Tap **Stop video** to end the feed while keeping the browser preview ready for
photos. **Take photo** also stops video uploads before capturing and sending the
still image. **Close camera** releases the camera and hides the preview. If frames stop arriving for four
seconds, the desktop retains the last image and shows the QR again. Restarting
the same video view retains manual circles and view edits; a different image
size or a new photo starts a fresh analysis. Switching to a local camera, opening
a file or closing the app stops the phone receiver.

## If the link does not open

The receiver uses native adapter discovery without DNS or internet probes. An
IPv4 address shared with the phone is needed; a loopback-only connection cannot
be reached from the phone. Check the selected network address, that both devices share a network, and that
the network permits devices to contact each other. Guest Wi-Fi often isolates
devices. A computer firewall may need to allow the application on your private
network; the app does not alter firewall settings. The server uses local available
ports shown in the URL. Do not forward them through an internet router.

If local HTTPS cannot start, the Camera tab shows the actual reason; HTTP photos
still work through **Choose photo**. This means the computer could not prepare its video connection, rather
than a phone rejecting the certificate. Details are written to `phone-error.log`
beside `options.json`, including the interpreter path. Missing runtime dependencies
are checked earlier and stop application startup.

Native Windows HTTP/HTTPS/Tk and browser workflows are covered by integration
checks. Real iPhone/Android capture, certificate trust prompts, Wi-Fi/firewall
behavior and the native Linux desktop workflow still require device validation.
