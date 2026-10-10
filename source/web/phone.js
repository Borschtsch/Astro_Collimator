"use strict";
const status = document.getElementById("status"), preview = document.getElementById("preview");
const open = document.getElementById("open"), photo = document.getElementById("photo");
const start = document.getElementById("start"), stop = document.getElementById("stop");
const choose = document.getElementById("choose"), progress = document.getElementById("progress");
const zoom = document.getElementById("zoom"), zoomValue = document.getElementById("zoom-value");
const zoomNote = document.getElementById("zoom-note"), zoomControls = document.getElementById("zoom-controls");
let config = {}, media = null, streamId = null, cameraRun = 0, videoRun = 0;
let opening = false, uploading = false, takingPhoto = false, frameRequest = null;
let zoomRange = null, pendingZoom = null, zoomTask = null;
const say = message => { status.textContent = message; };
function buttons() {
  const busy = uploading || takingPhoto;
  open.textContent = opening ? "Cancel camera" : media ? "Close camera" : "Open camera";
  open.disabled = busy;
  photo.disabled = !media || opening || busy || !!zoomTask;
  start.disabled = opening || busy || !!streamId;
  stop.disabled = !streamId;
  choose.disabled = busy;
  zoom.disabled = !media || !zoomRange || busy;
}
async function api(path, options = {}) {
  const response = await fetch(path, {...options, cache:"no-store"});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Connection failed. Open the current QR link.");
  return result;
}
async function loadConfig() {
  config = await api("config");
  document.getElementById("server-fingerprint").textContent = config.server_sha256 || "Local HTTPS is unavailable.";
  document.getElementById("ca-fingerprint").textContent = config.ca_sha256 || config.tls_error || "Preparing…";
  document.getElementById("certificate").hidden = !config.ca_sha256;
  document.getElementById("profile").hidden = !config.ca_sha256;
}
async function stopVideo(notify = true) {
  ++videoRun;
  const id = streamId;
  streamId = null;
  const pending = frameRequest;
  buttons();
  // Complete any current image upload before submitting a photo or new session.
  if (pending) await pending.catch(()=>{});
  if (notify && id) await api("stream/stop", {method:"POST", body:JSON.stringify({stream_id:id})}).catch(()=>{});
}
function closeCamera(notify = true) {
  ++cameraRun;
  opening = false;
  stopVideo(notify);
  if (media) media.getTracks().forEach(track => track.stop());
  media = null; preview.srcObject = null; preview.hidden = true;
  zoomRange = null; pendingZoom = null; zoomTask = null; zoomControls.hidden = true;
  buttons();
}
function cameraError(error) {
  return error.name === "NotAllowedError"
    ? "Camera permission was denied. Allow camera access in this browser. You can still choose an existing photo."
    : error.message;
}
function readZoom(track) {
  zoomControls.hidden = false;
  zoomRange = null; zoomValue.textContent = "";
  try {
    const range = track.getCapabilities?.().zoom, value = track.getSettings?.().zoom;
    if (range && Number.isFinite(range.min) && Number.isFinite(range.max)
        && range.min > 0 && range.max > range.min && Number.isFinite(value)) {
      zoomRange = {min:range.min, max:range.max,
                   step:Number.isFinite(range.step) && range.step > 0 ? range.step : .01};
      zoom.min = zoomRange.min; zoom.max = zoomRange.max; zoom.step = zoomRange.step;
      zoom.value = value; zoomValue.textContent = Number(value).toFixed(2) + "×";
      zoomNote.textContent = "Uses camera zoom for photos and video.";
    } else {
      zoomNote.textContent = "Zoom is not available from this camera/browser.";
    }
  } catch {
    zoomNote.textContent = "This browser could not read the camera's zoom range.";
  }
  buttons();
}
async function openCamera() {
  if (media) return true;
  const current = ++cameraRun;
  opening = true; buttons();
  try {
    await loadConfig();
    if (current !== cameraRun) return false;
    if (location.protocol !== "https:") {
      if (!config.https_url) throw new Error("Local HTTPS is unavailable. Choose an existing photo, or check the connection on the computer.");
      say("Opening local HTTPS. Then tap Open camera or Send video again.");
      location.assign(config.https_url);
      return false;
    }
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("This browser has not enabled camera access. Choose an existing photo, or compare the local certificate with the computer if trust setup is needed.");
    const video = {facingMode:{ideal:"environment"}, width:{ideal:1280}, height:{ideal:720}};
    if (navigator.mediaDevices.getSupportedConstraints?.().zoom) video.zoom = true;
    let captured;
    try {
      captured = await navigator.mediaDevices.getUserMedia({audio:false, video});
    } catch (error) {
      if (!video.zoom || !["OverconstrainedError", "NotSupportedError"].includes(error.name)) throw error;
      delete video.zoom;
      captured = await navigator.mediaDevices.getUserMedia({audio:false, video});
    }
    if (current !== cameraRun) { captured.getTracks().forEach(track => track.stop()); return false; }
    media = captured;
    preview.srcObject = media; preview.hidden = false;
    await preview.play();
    if (current !== cameraRun) return false;
    readZoom(media.getVideoTracks()[0]);
    say("Camera ready. Adjust zoom, then take a photo or send video.");
    return true;
  } catch (error) {
    if (current === cameraRun) { closeCamera(); say(cameraError(error)); }
    return false;
  } finally {
    if (current === cameraRun) { opening = false; buttons(); }
  }
}
open.onclick = async () => {
  if (media || opening) { closeCamera(); say("Camera closed."); }
  else await openCamera();
};
zoom.oninput = () => {
  if (!media || !zoomRange || uploading || takingPhoto) return;
  pendingZoom = Number(zoom.value);
  if (zoomTask) return;
  const track = media.getVideoTracks()[0], current = cameraRun, range = zoomRange;
  const task = (async () => {
    // Serial constraints; fast dragging retains only the latest requested value.
    while (pendingZoom !== null && current === cameraRun) {
      let value = pendingZoom; pendingZoom = null;
      value = range.min + Math.round((value - range.min) / range.step) * range.step;
      value = Math.max(range.min, Math.min(range.max, value));
      try {
        await track.applyConstraints({advanced:[{zoom:value}]});
        if (current !== cameraRun) break;
        const applied = track.getSettings().zoom;
        if (!Number.isFinite(applied) || Math.abs(applied - value) > range.step / 2 + 1e-6)
          throw new Error("The camera did not apply the requested zoom.");
        if (pendingZoom === null) zoom.value = applied;
        zoomValue.textContent = Number(applied).toFixed(2) + "×";
        zoomNote.textContent = "Uses camera zoom for photos and video.";
      } catch (error) {
        if (current !== cameraRun) break;
        pendingZoom = null;
        const applied = track.getSettings().zoom;
        if (Number.isFinite(applied)) {
          zoom.value = applied; zoomValue.textContent = Number(applied).toFixed(2) + "×";
        }
        zoomNote.textContent = "Zoom could not be changed: " + error.message;
      }
    }
  })().finally(() => { if (zoomTask === task) { zoomTask = null; buttons(); } });
  zoomTask = task; buttons();
};
async function frameBlob(type, quality) {
  if (!preview.videoWidth || !preview.videoHeight) throw new Error("The camera image is not ready. Try again in a moment.");
  const canvas = document.createElement("canvas");
  canvas.width = preview.videoWidth; canvas.height = preview.videoHeight;
  canvas.getContext("2d").drawImage(preview, 0, 0);
  const blob = await new Promise(resolve => canvas.toBlob(resolve, type, quality));
  if (!blob) throw new Error("The browser could not capture this image.");
  return blob;
}
async function sendPhoto(file, keepCamera = false) {
  if (!file || uploading) return;
  uploading = true; buttons();
  await stopVideo();
  if (!keepCamera) closeCamera();
  progress.hidden = false;
  progress.value = 0; say("Sending photo…");
  try {
    const result = await new Promise((resolve,reject)=>{
      const request = new XMLHttpRequest(); request.open("POST", "photo");
      request.timeout = 60000; request.setRequestHeader("Content-Type", file.type || "application/octet-stream");
      request.upload.onprogress = e => { if(e.lengthComputable) progress.value = 100 * e.loaded / e.total; };
      request.onload = () => {
        try { const value=JSON.parse(request.responseText); request.status===200?resolve(value):reject(new Error(value.error)); }
        catch { reject(new Error("The receiver did not return a receipt.")); }
      };
      request.onerror = request.ontimeout = () => reject(new Error("Transfer interrupted. Check Wi-Fi and the computer, then send again."));
      request.send(file);
    });
    say("Photo received on computer (" + result.width + " × " + result.height + ", receipt " + result.receipt + ").");
  } catch(error) { say(error.message); }
  finally { uploading=false; progress.hidden=true; buttons(); }
}
choose.onchange = event => {
  sendPhoto(event.target.files[0]); event.target.value="";
};
photo.onclick = async () => {
  if (!media || uploading || takingPhoto || zoomTask) return;
  takingPhoto = true; buttons();
  const current = cameraRun, track = media.getVideoTracks()[0];
  try {
    say("Taking photo in browser…");
    await stopVideo();
    if (current !== cameraRun) return;
    let blob;
    if (typeof ImageCapture === "function") {
      try { blob = await new ImageCapture(track).takePhoto(); }
      catch (error) { if (error.name === "NotAllowedError") throw error; }
    }
    if (current !== cameraRun || track.readyState !== "live") return;
    // No camera app and no artificial zoom: preserve the preview's full pixels.
    if (!blob) blob = await frameBlob("image/png");
    if (current === cameraRun) await sendPhoto(blob, true);
  } catch (error) { if (current === cameraRun) say(cameraError(error)); }
  finally { takingPhoto = false; buttons(); }
};
stop.onclick = async () => { await stopVideo(); say("Video stopped. The camera is ready for photos."); };
start.onclick = async () => {
  if (uploading || takingPhoto || streamId) return;
  if (!await openCamera() || !media) return;
  const current = ++videoRun, camera = cameraRun;
  streamId = crypto.randomUUID(); const id = streamId;
  buttons();
  try {
    await api("stream/start", {method:"POST", body:JSON.stringify({stream_id:id})});
    if (current !== videoRun || camera !== cameraRun) {
      api("stream/stop", {method:"POST",body:JSON.stringify({stream_id:id})}).catch(()=>{});
      return;
    }
    say("Sending video to the computer…");
    let sequence = 0;
    while (current === videoRun && camera === cameraRun && media) {
      const blob = await frameBlob("image/jpeg", .9);
      if (current !== videoRun || camera !== cameraRun) break;
      const request = api("frame", {method:"POST", headers:{"X-Stream-ID":id,"X-Frame-Sequence":String(sequence++)}, body:blob});
      frameRequest = request;
      try { await request; } finally { if (frameRequest === request) frameRequest = null; }
      await new Promise(resolve=>setTimeout(resolve,100));
    }
  } catch (error) {
    if (current === videoRun) { await stopVideo(); say(error.message); }
  }
};
window.addEventListener("pagehide", () => {
  const id = streamId; closeCamera(false);
  if (id) navigator.sendBeacon("stream/stop",JSON.stringify({stream_id:id}));
});
buttons();
loadConfig().catch(error=>say(error.message));
