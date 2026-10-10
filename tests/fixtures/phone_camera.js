// Hardware-boundary capabilities/failures around a real browser video track.
// The page, browser image capture/canvas, HTTP/TLS receiver and desktop stay real.
(() => {
  const device = window.phoneCameraHardware = {
    zoomSupported:true, zoom:1, requests:[], applying:0, maximumApplying:0,
    rejectZoom:false, ignoreZoom:false, fallbackPhoto:false, denyCamera:false,
    delayCamera:0, stopped:0, captures:[], acquired:0
  };
  const capture = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  navigator.mediaDevices.getUserMedia = async constraints => {
    if (device.denyCamera) throw new DOMException("Camera permission denied by hardware fixture.", "NotAllowedError");
    if (device.delayCamera) await new Promise(resolve => setTimeout(resolve, device.delayCamera));
    const stream = await capture(constraints);
    ++device.acquired;
    const track = stream.getVideoTracks()[0];
    const settings = track.getSettings.bind(track), capabilities = track.getCapabilities.bind(track);
    const stop = track.stop.bind(track);
    track.stop = () => { ++device.stopped; stop(); };
    track.getCapabilities = () => {
      const result = capabilities();
      if (device.zoomSupported) result.zoom = {min:1, max:4, step:.25};
      else delete result.zoom;
      return result;
    };
    track.getSettings = () => {
      const result = settings();
      if (device.zoomSupported) result.zoom = device.zoom;
      else delete result.zoom;
      return result;
    };
    track.applyConstraints = async constraints => {
      const value = constraints.advanced[0].zoom;
      device.requests.push(value);
      ++device.applying;
      device.maximumApplying = Math.max(device.maximumApplying, device.applying);
      try {
        await new Promise(resolve => setTimeout(resolve, 60));
        if (device.rejectZoom) throw new DOMException("Camera zoom adjustment rejected.", "OverconstrainedError");
        if (value < 1 || value > 4) throw new DOMException("Zoom out of range.", "OverconstrainedError");
        if (!device.ignoreZoom) device.zoom = value;
      } finally { --device.applying; }
    };
    return stream;
  };
  const NativeImageCapture = window.ImageCapture;
  window.ImageCapture = class {
    constructor(track) { this.track = track; }
    async takePhoto() {
      device.captures.push(this.track.getSettings().zoom);
      if (device.fallbackPhoto || !NativeImageCapture)
        throw new DOMException("Still capture unavailable on this camera.", "NotSupportedError");
      return new NativeImageCapture(this.track).takePhoto();
    }
  };
})();
