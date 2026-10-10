"""Real Tk, HTTP/TLS, image decoder and browser phone-source workflows."""

from io import BytesIO
import hashlib
import http.client
import json
import os
from pathlib import Path
import ssl
import tempfile
import time
import unittest
from urllib.parse import urlsplit

import cv2
import numpy as np
from PIL import Image

from source.phone_server import PHONE_SOURCE, PhoneReceiver, MAX_PHOTO
from tests.fixtures.camera import FakeCapture
from tests.fixtures.images import optical_fixture
from tests.integration.test_app import GuiTests


def request(receiver, path="", body=None, headers=None, secure=False):
    address = urlsplit(receiver.url("127.0.0.1", secure=secure))
    connection = (http.client.HTTPSConnection(address.hostname, address.port,
                  context=ssl.create_default_context(cadata=receiver.identity["ca_pem"].decode()), timeout=8)
                  if secure else http.client.HTTPConnection(address.hostname, address.port, timeout=8))
    try:
        connection.request("POST" if body is not None else "GET", address.path + path, body=body, headers=headers or {})
        response = connection.getresponse()
        data = response.read()
        return response.status, data
    finally:
        connection.close()


def encoded(frame, extension=".png"):
    return cv2.imencode(extension, frame)[1].tobytes()


class PhoneTests(GuiTests):
    def wait_until(self, predicate):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            self.root.update()
            if predicate():
                return
            time.sleep(.005)
        self.fail("Timed out waiting for phone workflow")

    def phone_app(self, live_tracking=False):
        app = self.make_app(lambda index: FakeCapture(index, opened=index == 0), live_tracking=live_tracking)
        self.wait_until(lambda: app.camera_on and app.last_frame is not None)
        app.selected_camera.set(PHONE_SOURCE)
        app.on_camera_selected(None)
        self.wait_until(lambda: app.phone_receiver.ready.is_set() and bool(app.phone_url.get()))
        self.addCleanup(self.finish_receivers, app)
        return app, app.phone_receiver

    def finish_receivers(self, app):
        if app.phone_receiver:
            app.stop_phone()
        for receiver in app.retired_receivers:
            self.assertTrue(receiver.finished.wait(8))
            self.assertFalse(receiver.start_thread.is_alive())
            self.assertTrue(all(not thread.is_alive() for thread in receiver.threads))

    def upload(self, receiver, frame, sequence=0, stream_id="integration-stream"):
        return request(receiver, "frame", encoded(frame, ".jpg"),
                       {"X-Stream-ID": stream_id, "X-Frame-Sequence": str(sequence)})

    def start_stream(self, receiver, stream_id="integration-stream"):
        self.assertEqual(request(receiver, "stream/start", json.dumps({"stream_id": stream_id}).encode())[0], 200)

    def test_photo_qr_exif_heic_auto_detection_and_raw_export(self):
        app, receiver = self.phone_app()
        self.assertFalse(app.camera_on)
        self.assertFalse(app.live_source_active)
        self.assertTrue(all(not control.winfo_ismapped() for control in app.camera_controls.values()))
        self.assertTrue(app.phone_connection_visible)
        self.assertTrue(app.phone_view.winfo_ismapped())
        self.assertIs(app.phone_view.master, app.video_label)
        self.assertIsNone(app.video_label.image)
        for size in ("1024x768", "1280x720"):
            self.root.geometry(size); self.root.update()
            self.assertGreaterEqual(app.phone_view.winfo_rootx(), app.video_label.winfo_rootx())
            self.assertLessEqual(app.phone_view.winfo_rootx() + app.phone_view.winfo_width(),
                                 app.video_label.winfo_rootx() + app.video_label.winfo_width())
            self.assertGreaterEqual(app.phone_view.winfo_rooty(), app.video_label.winfo_rooty())
            self.assertLessEqual(app.phone_view.winfo_rooty() + app.phone_view.winfo_height(),
                                 app.video_label.winfo_rooty() + app.video_label.winfo_height())
        qr = np.array(ImageTk_image(app.phone_qr.image))
        # QR decoding validates the actual Tk-displayed link, not only its string.
        link, _, _ = cv2.QRCodeDetector().detectAndDecode(qr)
        self.assertEqual(link, app.phone_url.get())
        app.zoom_factor = 2
        app.crosshair_angles["optical"] = 15
        original = encoded(optical_fixture())
        code, receipt = request(receiver, "photo", original)
        self.assertEqual(code, 200)
        self.assertEqual(receiver.original_photo, original)
        self.wait_until(lambda: app.detection is not None and not app.analysis_busy)
        self.assertFalse(app.phone_connection_visible)
        self.assertFalse(app.phone_view.winfo_ismapped())
        self.assertEqual(app.source_description, "Phone photo")
        self.assertEqual(app.zoom_factor, 1)
        self.assertFalse(app.tracking_active)
        app.phone_view_button.invoke()
        self.assertTrue(app.phone_connection_visible)
        app.zoom_with_scroll(type("Wheel", (), {"delta":120, "x":50, "y":50})())
        app.begin_pan(type("Click", (), {"x":50, "y":50})())
        self.assertEqual(app.zoom_factor, 1)
        self.assertIsNone(app.pan_anchor)
        self.root.update()
        self.assertIsNone(app.video_label.image)
        app.phone_view_button.invoke()
        self.assertFalse(app.phone_connection_visible)
        self.wait_until(lambda: app.video_label.image is not None)
        np.testing.assert_array_equal(app.last_frame, optical_fixture())
        output = self.options_store.path.parent / "phone.png"
        app.export_capture(output)
        np.testing.assert_array_equal(cv2.imread(str(output)), optical_fixture())
        self.assertNotIn(receiver.token, output.with_suffix(".json").read_text())
        # Portrait EXIF orientation is applied once, without changing supplied bytes.
        image = Image.fromarray(cv2.cvtColor(optical_fixture(size=(160, 120)), cv2.COLOR_BGR2RGB))
        exif = Image.Exif(); exif[274] = 6
        content = BytesIO(); image.save(content, format="JPEG", exif=exif)
        data = content.getvalue()
        self.assertEqual(request(receiver, "photo", data)[0], 200)
        self.wait_until(lambda: app.last_frame.shape[:2] == (160, 120) and not app.analysis_busy)
        self.assertEqual(receiver.original_photo, data)
        from pillow_heif import from_pillow
        content = BytesIO(); from_pillow(image).save(content)
        self.assertEqual(request(receiver, "photo", content.getvalue())[0], 200)
        self.wait_until(lambda: app.last_frame.shape[:2] == (120, 160) and not app.analysis_busy)
        for size in ("1024x768", "1280x720"):
            self.root.geometry(size); self.root.update()
            self.assertLessEqual(app.phone_panel.winfo_rooty() + app.phone_panel.winfo_height(),
                                 self.root.winfo_rooty() + self.root.winfo_height())

    def test_local_tls_identity_matches_pc_phone_peer_and_persists(self):
        app, receiver = self.phone_app()
        self.assertTrue(receiver.https_port, receiver.tls_error)
        code, data = request(receiver, "config", secure=True)
        self.assertEqual(code, 200)
        config = json.loads(data)
        self.assertEqual(config["server_sha256"], receiver.identity["server_sha256"])
        context = ssl.create_default_context(cadata=receiver.identity["ca_pem"].decode())
        with context.wrap_socket(__import__("socket").create_connection(("127.0.0.1", receiver.https_port)), server_hostname="127.0.0.1") as connection:
            peer = connection.getpeercert(binary_form=True)
            actual = ":".join(f"{byte:02X}" for byte in hashlib.sha256(peer).digest())
            self.assertEqual(actual, config["server_sha256"])
        code, root = request(receiver, "ca.cer")
        self.assertEqual(code, 200)
        self.assertEqual(":".join(f"{byte:02X}" for byte in hashlib.sha256(root).digest()), config["ca_sha256"])
        code, profile_data = request(receiver, "phone.mobileconfig")
        profile = __import__("plistlib").loads(profile_data)
        self.assertEqual(code, 200)
        self.assertEqual(len(profile["PayloadContent"]), 1)
        self.assertEqual(profile["PayloadContent"][0]["PayloadContent"], root)
        self.assertEqual(profile["PayloadContent"][0]["PayloadType"], "com.apple.security.root")
        self.assertIn(config["ca_sha256"], profile["PayloadDescription"])
        self.assertFalse(profile["PayloadRemovalDisallowed"])
        app.show_phone_identity(); self.root.update()
        dialogs = [window for window in self.root.winfo_children() if window.winfo_class() == "Toplevel"]
        self.assertEqual(len(dialogs), 1)
        texts = [child.get("1.0", "end").strip() for child in dialogs[0].winfo_children() if child.winfo_class() == "Text"]
        self.assertEqual(texts, [config["server_sha256"], config["ca_sha256"]])
        dialogs[0].destroy()
        request(receiver, "photo", encoded(optical_fixture()), secure=True)
        self.wait_until(lambda: app.detection is not None and not app.analysis_busy)
        app.select_phone()
        self.wait_until(lambda: app.phone_receiver.ready.is_set())
        self.assertEqual(app.phone_receiver.identity["ca_sha256"], config["ca_sha256"])
        with tempfile.TemporaryDirectory() as other:
            separate = PhoneReceiver(Path(other), addresses=["127.0.0.1"], bind_host="127.0.0.1")
            separate.start()
            try:
                self.assertTrue(separate.ready.wait(8))
                self.assertNotEqual(separate.identity["ca_sha256"], config["ca_sha256"])
            finally:
                separate.stop(); self.assertTrue(separate.finished.wait(8))

    def test_http_photos_survive_failed_optional_certificate_setup(self):
        app = self.make_app(lambda index: FakeCapture(index, opened=False))
        self.wait_until(lambda: "No cameras found" in app.loading_label.cget("text"))
        folder = self.options_store.path.parent / "phone-link"
        folder.mkdir(); (folder / "ca.pem").write_bytes(b"incomplete identity")
        app.selected_camera.set(PHONE_SOURCE); app.on_camera_selected(None)
        self.addCleanup(self.finish_receivers, app)
        self.wait_until(lambda: app.phone_receiver.ready.is_set())
        receiver = app.phone_receiver
        self.assertFalse(receiver.https_port)
        self.assertIn("incomplete", receiver.tls_error)
        self.wait_until(lambda: "incomplete" in app.phone_status.get())
        self.assertIn("Video is unavailable", app.phone_status.get())
        self.assertTrue(app.phone_qr.image)
        log = self.options_store.path.parent / "phone-error.log"
        self.assertIn("Interpreter: " + __import__("sys").executable, log.read_text())
        self.assertIn("incomplete", log.read_text())
        self.assertNotIn(receiver.token, log.read_text())
        self.assertEqual((folder / "ca.pem").read_bytes(), b"incomplete identity")
        self.assertEqual(request(receiver, "photo", encoded(optical_fixture()))[0], 200)
        self.wait_until(lambda: app.detection is not None and not app.analysis_busy)
        self.assertFalse(app.phone_certificate_button.instate(["!disabled"]))

    def test_live_phone_tracking_pause_latest_frame_manual_retention_and_disconnect(self):
        app, receiver = self.phone_app(live_tracking=True)
        self.start_stream(receiver)
        self.assertEqual(self.upload(receiver, optical_fixture(), 0)[0], 200)
        self.wait_until(lambda: app.phone_streaming and app.detection is not None and not app.analysis_busy)
        self.assertTrue(app.live_source_active)
        self.assertTrue(app.tracking_active)
        self.assertEqual(app.phone_qr.cget("image"), "")
        app.track_live.set(False); app.tracking_changed()
        self.assertFalse(app.view_frozen)
        shifted = np.roll(optical_fixture(), 8, axis=1)
        for sequence in range(1, 5):
            self.assertEqual(self.upload(receiver, shifted, sequence)[0], 200)
        self.assertEqual(receiver.frames.qsize(), 1)
        self.wait_until(lambda: not app.observations_current and np.mean(np.abs(app.last_frame.astype(float) - shifted)) < 1)
        self.assertFalse(app.camera_on)
        output = self.options_store.path.parent / "paused.png"
        app.export_capture(output)
        self.assertIsNone(json.loads(output.with_suffix(".json").read_text())["alignment_advice"])
        app.track_live.set(True); app.tracking_changed()
        self.wait_until(lambda: not app.analysis_busy and app.observations_current)
        role = "Focuser edge"
        self.assertIn(role, app.selections)
        app.review_role.set(role); app.refresh_review_selection()
        app.radius_text.set("350"); app.commit_review_radius()
        held_radius = app.visible_detection().candidate(app.selections[role]).radius
        analyzed_at = app.last_analysis_time
        self.assertEqual(self.upload(receiver, shifted, 5)[0], 200)
        self.wait_until(lambda: app.last_analysis_time > analyzed_at and not app.analysis_busy)
        self.assertAlmostEqual(app.visible_detection().candidate(app.selections[role]).radius, held_radius)
        # Real stop and lost-stream path restores the QR without selecting a webcam.
        self.assertEqual(request(receiver, "stream/stop", b'{"stream_id":"integration-stream"}')[0], 200)
        self.wait_until(lambda: not app.phone_streaming and bool(app.phone_qr.cget("image")))
        self.assertEqual(app.selected_camera.get(), PHONE_SOURCE)
        self.assertFalse(app.observations_current)
        self.assertEqual(self.upload(receiver, shifted, 6)[0], 409)
        self.start_stream(receiver, "replacement-stream")
        self.assertEqual(self.upload(receiver, shifted, 0, "replacement-stream")[0], 200)
        self.wait_until(lambda: app.phone_streaming and app.phone_generation == receiver.generation and not app.analysis_busy)
        self.assertIn(role, app.manual_references)
        self.assertAlmostEqual(app.visible_detection().candidate(app.selections[role]).radius, held_radius)

    def test_receiver_rejects_bad_inputs_origins_tokens_and_stale_frames(self):
        app, receiver = self.phone_app()
        body = encoded(optical_fixture())
        self.assertEqual(request(receiver, "photo", body, {"Host":"example.invalid"})[0], 403)
        self.assertEqual(request(receiver, "photo", body, {"Origin":"https://example.invalid"})[0], 403)
        address = urlsplit(receiver.url("127.0.0.1"))
        connection = http.client.HTTPConnection(address.hostname, address.port, timeout=5)
        connection.request("GET", "/wrong-token/config"); response = connection.getresponse()
        self.assertEqual(response.status, 404); response.read(); connection.close()
        self.assertEqual(request(receiver, "photo", b"not an image")[0], 400)
        self.assertEqual(request(receiver, "photo", encoded(np.zeros((12, 12, 3), np.uint8)))[0], 400)
        self.assertEqual(request(receiver, "photo", b"x", {"Content-Length":str(MAX_PHOTO+1)})[0], 413)
        import struct
        import zlib
        excessive = bytearray(encoded(np.zeros((40, 40, 3), np.uint8)))
        excessive[16:24] = struct.pack("!II", 12000, 6000)
        excessive[29:33] = struct.pack("!I", zlib.crc32(excessive[12:29]))
        code, error = request(receiver, "photo", excessive)
        self.assertEqual(code, 400)
        self.assertIn("60 megapixels", json.loads(error)["error"])
        for invalid in (b"null", b"[]", b"true", b"{bad", b'{"stream_id":5}'):
            self.assertEqual(request(receiver, "stream/start", invalid)[0], 400)
        self.start_stream(receiver)
        self.assertEqual(self.upload(receiver, optical_fixture(), 2)[0], 200)
        self.assertEqual(self.upload(receiver, optical_fixture(), 1)[0], 409)
        self.assertEqual(self.upload(receiver, optical_fixture(), 2)[0], 409)
        self.assertEqual(self.upload(receiver, optical_fixture(), 3, "another-stream")[0], 409)
        self.assertEqual(request(receiver, "photo", body)[0], 200)
        self.assertEqual(self.upload(receiver, optical_fixture(), 3)[0], 409)
        self.wait_until(lambda: app.phone_kind == "photo" and not app.analysis_busy)

    def test_new_photo_during_detection_uses_latest_image_without_parallel_analysis(self):
        import threading
        app, receiver = self.phone_app()
        first = optical_fixture()
        second = np.roll(optical_fixture(size=(900, 640)), 20, axis=1)
        self.assertEqual(request(receiver, "photo", encoded(first))[0], 200)
        self.wait_until(lambda: app.analysis_busy)
        self.assertEqual(request(receiver, "photo", encoded(second))[0], 200)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            self.root.update()
            self.assertLessEqual(sum(thread.name == "Optical-edge-analysis" for thread in threading.enumerate()), 1)
            if (app.detection is not None and app.detection.image_size == (900, 640)
                    and not app.analysis_busy and app.observations_current):
                break
            time.sleep(.01)
        else:
            self.fail("The latest uploaded photo was not analyzed")
        np.testing.assert_array_equal(app.last_frame, second)
        self.assertEqual(receiver.original_photo, encoded(second))

    def test_slow_upload_backpressure_allows_stop_and_rejects_late_frame(self):
        app, receiver = self.phone_app()
        self.start_stream(receiver)
        body = encoded(optical_fixture(), ".jpg")
        address = urlsplit(receiver.url("127.0.0.1"))
        connection = http.client.HTTPConnection(address.hostname, address.port, timeout=5)
        try:
            connection.putrequest("POST", address.path + "frame")
            connection.putheader("Content-Length", str(len(body)))
            connection.putheader("X-Stream-ID", "integration-stream")
            connection.putheader("X-Frame-Sequence", "0")
            connection.endheaders(body[:10])
            self.wait_until(lambda: receiver.decode_lock._value == 0)
            self.assertEqual(request(receiver, "photo", encoded(optical_fixture()))[0], 503)
            self.assertEqual(request(receiver, "stream/stop", b'{"stream_id":"integration-stream"}')[0], 200)
            connection.send(body[10:])
            response = connection.getresponse()
            self.assertEqual(response.status, 409)
            response.read()
        finally:
            connection.close()
        self.assertEqual(receiver.frames.qsize(), 0)
        self.assertEqual(request(receiver, "photo", encoded(optical_fixture()))[0], 200)
        self.wait_until(lambda: app.detection is not None and not app.analysis_busy)

    def test_live_phone_averaging_timeout_and_reconnect_keep_view(self):
        app, receiver = self.phone_app(live_tracking=True)
        self.start_stream(receiver)
        frame = optical_fixture()
        self.assertEqual(self.upload(receiver, frame, 0)[0], 200)
        self.wait_until(lambda: app.detection is not None and not app.analysis_busy)
        # Keep receipt independent of GUI/analysis cadence, as a phone browser does.
        import threading
        upload_results = []
        def send_frames():
            for sequence in range(1, 26):
                upload_results.append(self.upload(receiver, frame, sequence)[0])
                time.sleep(.1)
        sender = threading.Thread(target=send_frames, daemon=True)
        sender.start()
        averaged = False
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and sender.is_alive():
            self.root.update()
            averaged = averaged or (app.averaged_frames > 1 and app.observations_current)
            time.sleep(.005)
        sender.join(8)
        self.assertFalse(sender.is_alive())
        self.assertEqual(upload_results, [200] * 25)
        self.assertTrue(averaged, "No completed steady-frame average was observed")
        self.wait_until(lambda: not app.analysis_busy)
        self.assertTrue(app.observations_current)
        app.zoom_factor = 1.7
        app.crosshair_angles["optical"] = 12
        # No mocked clock: the production receiver's four-second timeout fires.
        self.wait_until(lambda: not app.phone_streaming and bool(app.phone_qr.cget("image")))
        self.assertEqual(app.zoom_factor, 1.7)
        self.assertFalse(app.observations_current)
        self.start_stream(receiver, "after-timeout")
        self.assertEqual(self.upload(receiver, frame, 0, "after-timeout")[0], 200)
        self.wait_until(lambda: app.phone_streaming and app.phone_generation == receiver.generation)
        self.assertEqual(app.zoom_factor, 1.7)
        self.assertEqual(app.crosshair_angles["optical"], 12)

    def test_phone_switch_to_file_webcam_and_shutdown_releases_ports(self):
        app, receiver = self.phone_app()
        old_port = receiver.http_port
        filename = self.options_store.path.parent / "local.png"
        filename.write_bytes(encoded(optical_fixture()))
        app.load_image(filename)
        self.assertEqual(app.source_mode, "image")
        self.assertIsNone(app.phone_receiver)
        self.assertTrue(receiver.finished.wait(8))
        with self.assertRaises(OSError):
            __import__("socket").create_connection(("127.0.0.1", old_port), timeout=.3)
        app.resume_live()
        self.wait_until(lambda: app.phone_receiver is not None and app.phone_receiver.ready.is_set())
        replacement = app.phone_receiver
        app.selected_camera.set("Camera 0"); app.on_camera_selected(None)
        self.wait_until(lambda: app.camera_on and app.last_frame is not None)
        self.assertTrue(replacement.finished.wait(8))
        self.assertFalse(app.phone_panel.winfo_ismapped())
        app.selected_camera.set(PHONE_SOURCE); app.on_camera_selected(None)
        pending = app.phone_receiver
        app.on_closing()
        self.assertTrue(pending.finished.wait(8))

    def test_mobile_browser_photo_and_video_use_production_page_and_receiver(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Install requirements-test.txt for real browser integration coverage.")
        app, receiver = self.phone_app()
        filename = self.options_store.path.parent / "browser-photo.png"
        filename.write_bytes(encoded(optical_fixture()))
        with sync_playwright() as playwright:
            executable = os.environ.get("COLLIMATOR_TEST_BROWSER")
            if not executable and os.name == "nt":
                candidate = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
                executable = str(candidate) if candidate.exists() else None
            browser = playwright.chromium.launch(executable_path=executable, headless=True,
                args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
            try:
                context = browser.new_context(ignore_https_errors=True, viewport={"width":390,"height":844})
                page = context.new_page()
                external = []; errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                context.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).hostname == "127.0.0.1"
                              else (external.append(route.request.url), route.abort())[-1])
                page.goto(receiver.url("127.0.0.1"))
                page.locator("#choose").set_input_files(str(filename))
                page.get_by_role("status").filter(has_text="Photo received on computer").wait_for()
                self.wait_until(lambda: app.detection is not None and not app.analysis_busy)
                np.testing.assert_array_equal(app.last_frame, optical_fixture())
                self.assertEqual(receiver.original_photo, filename.read_bytes())
                page.locator("summary").click()
                self.assertEqual(page.locator("#ca-fingerprint").inner_text(), receiver.identity["ca_sha256"])
                page.locator("#start").click()
                page.wait_for_url(receiver.url("127.0.0.1", secure=True))
                page.wait_for_load_state("load")
                self.assertEqual(page.locator('input[capture]').count(), 0)
                page.locator("#open").click()
                page.locator("#photo:enabled").wait_for(timeout=10000)
                self.assertFalse(page.locator("#preview").evaluate("element => element.hidden"))
                with page.expect_response(lambda response: urlsplit(response.url).path.endswith("/photo") and response.status == 200, timeout=10000) as photo_response:
                    page.locator("#photo").click()
                photo_receipt = photo_response.value.json()["receipt"]
                page.get_by_role("status").filter(has_text="Photo received on computer").wait_for()
                try:
                    self.wait_until(lambda: receiver.receipt == photo_receipt and app.source_description == "Phone photo" and not app.analysis_busy)
                except AssertionError:
                    self.fail(f"Browser photo transition: receipt={receiver.receipt}; source={app.source_description}; busy={app.analysis_busy}; status={page.locator('#status').inner_text()}; errors={errors}")
                self.assertTrue(receiver.original_photo)
                self.assertTrue(page.locator("#photo").is_enabled())
                self.assertEqual(page.locator("#open").inner_text(), "Close camera")
                self.assertFalse(receiver.status()["streaming"])
                # Pump browser route callbacks until a real frame is accepted,
                # before the separate Tk-only event loop waits for display.
                with page.expect_response(lambda response: urlsplit(response.url).path.endswith("/frame") and response.status == 200, timeout=10000):
                    page.locator("#start").click()
                try:
                    page.locator("#stop:enabled").wait_for(timeout=10000)
                except Exception:
                    self.fail(f"Browser video did not start: {page.locator('#status').inner_text()}; {errors}")
                try:
                    self.wait_until(lambda: receiver.status()["streaming"] and app.phone_streaming)
                except AssertionError:
                    self.fail(f"Browser feed failed: {page.locator('#status').inner_text()}; receiver={receiver.status()}; errors={errors}")
                self.assertFalse(page.locator("#preview").evaluate("element => element.hidden"))
                page.locator("#stop").click()
                self.wait_until(lambda: not receiver.status()["streaming"] and not app.phone_streaming)
                self.assertTrue(page.locator("#photo").is_enabled())
                self.assertFalse(page.locator("#preview").evaluate("element => element.hidden"))
                page.locator("#open").click()
                self.assertTrue(page.locator("#preview").evaluate("element => element.hidden"))
                self.assertTrue(page.locator("#photo").is_disabled())
                self.assertEqual(errors, [])
                self.assertEqual(external, [])
                page.screenshot(path=str(Path(__file__).resolve().parents[2] / "build/gui-validation/phone-browser.png"), full_page=True)
            finally:
                browser.close()

    def test_browser_camera_zoom_stills_live_transition_and_hardware_failures(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Install requirements-test.txt for real browser integration coverage.")
        app, receiver = self.phone_app()
        project = Path(__file__).resolve().parents[2]
        with sync_playwright() as playwright:
            executable = os.environ.get("COLLIMATOR_TEST_BROWSER")
            if not executable and os.name == "nt":
                candidate = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
                executable = str(candidate) if candidate.exists() else None
            browser = playwright.chromium.launch(executable_path=executable, headless=True,
                args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
            try:
                context = browser.new_context(ignore_https_errors=True, viewport={"width":390,"height":844})
                context.add_init_script(path=str(project / "tests/fixtures/phone_camera.js"))
                page = context.new_page()
                errors = []; external = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                context.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).hostname == "127.0.0.1"
                              else (external.append(route.request.url), route.abort())[-1])
                page.goto(receiver.url("127.0.0.1", secure=True))
                page.locator("#open").click()
                page.locator("#photo:enabled").wait_for(timeout=10000)
                slider = page.locator("#zoom")
                self.assertTrue(slider.is_enabled())
                self.assertEqual([float(slider.get_attribute(name)) for name in ("min", "max", "step")], [1, 4, .25])
                slider.evaluate("element => {element.value=2.25; element.dispatchEvent(new Event('input')); element.value=3.75; element.dispatchEvent(new Event('input'));}")
                page.wait_for_function("() => document.getElementById('zoom-value').textContent === '3.75×' && !document.getElementById('photo').disabled")
                self.assertEqual(page.evaluate("phoneCameraHardware.maximumApplying"), 1)
                self.assertEqual(page.evaluate("phoneCameraHardware.requests"), [2.25, 3.75])
                self.assertEqual(page.locator("#preview").evaluate("element => getComputedStyle(element).transform"), "none")
                with page.expect_response(lambda response: urlsplit(response.url).path.endswith("/photo") and response.status == 200, timeout=10000) as photo_response:
                    page.locator("#photo").click()
                photo_receipt = photo_response.value.json()["receipt"]
                page.get_by_role("status").filter(has_text="Photo received on computer").wait_for()
                self.wait_until(lambda: app.source_description == "Phone photo" and not app.analysis_busy)
                self.assertEqual(page.evaluate("phoneCameraHardware.captures"), [3.75])
                self.assertEqual(receiver.receipt, 1)
                np.testing.assert_array_equal(app.last_frame, receiver._decode(receiver.original_photo))
                output = self.options_store.path.parent / "browser-shutter.png"
                app.export_capture(output)
                np.testing.assert_array_equal(cv2.imread(str(output)), app.last_frame)
                # Driver rejection and silently ignored constraints retain actual zoom.
                for failure in ("rejectZoom", "ignoreZoom"):
                    page.evaluate("name => {phoneCameraHardware[name]=true;}", failure)
                    slider.evaluate("element => {element.value=2; element.dispatchEvent(new Event('input'));}")
                    page.wait_for_function("() => document.getElementById('zoom-note').textContent.includes('could not be changed') && !document.getElementById('photo').disabled")
                    self.assertEqual(float(slider.input_value()), 3.75)
                    page.evaluate("name => {phoneCameraHardware[name]=false;}", failure)
                # The shared zoom also applies while real frames are streaming.
                with page.expect_response(lambda response: urlsplit(response.url).path.endswith("/frame") and response.status == 200):
                    page.locator("#start").click()
                self.wait_until(lambda: app.phone_streaming)
                slider.evaluate("element => {element.value=2.5; element.dispatchEvent(new Event('input'));}")
                page.wait_for_function("() => document.getElementById('zoom-value').textContent === '2.50×'")
                # Hardware without native still capture uses an uncropped PNG frame.
                page.evaluate("phoneCameraHardware.fallbackPhoto=true")
                with page.expect_response(lambda response: urlsplit(response.url).path.endswith("/photo") and response.status == 200, timeout=10000) as photo_response:
                    page.locator("#photo").click()
                photo_receipt = photo_response.value.json()["receipt"]
                page.get_by_role("status").filter(has_text="Photo received on computer").wait_for()
                try:
                    self.wait_until(lambda: receiver.receipt == photo_receipt and app.source_description == "Phone photo" and not app.analysis_busy)
                except AssertionError:
                    self.fail(f"Fallback photo: receipt={receiver.receipt}; source={app.source_description}; busy={app.analysis_busy}; status={page.locator('#status').inner_text()}; errors={errors}")
                self.assertFalse(receiver.status()["streaming"])
                self.assertTrue(receiver.original_photo.startswith(b"\x89PNG"))
                dimensions = page.locator("#preview").evaluate("element => [element.videoWidth,element.videoHeight]")
                self.assertEqual(list(app.last_frame.shape[:2]), dimensions[::-1])
                self.assertTrue(page.locator("#photo").is_enabled())
                self.assertEqual(page.evaluate("phoneCameraHardware.captures.at(-1)"), 2.5)
                page.screenshot(path=str(project / "build/gui-validation/phone-camera-zoom.png"), full_page=True)
                # Reopening a camera without a usable range disables zoom only.
                page.locator("#open").click()
                self.assertGreater(page.evaluate("phoneCameraHardware.stopped"), 0)
                page.evaluate("phoneCameraHardware.zoomSupported=false")
                page.locator("#open").click(); page.locator("#photo:enabled").wait_for()
                self.assertTrue(slider.is_disabled())
                self.assertIn("not available", page.locator("#zoom-note").inner_text())
                with page.expect_response(lambda response: urlsplit(response.url).path.endswith("/photo") and response.status == 200, timeout=10000) as photo_response:
                    page.locator("#photo").click()
                photo_receipt = photo_response.value.json()["receipt"]
                page.get_by_role("status").filter(has_text="Photo received on computer").wait_for()
                self.wait_until(lambda: receiver.receipt == photo_receipt and not app.analysis_busy)
                page.locator("#open").click()
                page.evaluate("phoneCameraHardware.denyCamera=true")
                page.locator("#open").click()
                page.get_by_role("status").filter(has_text="permission was denied").wait_for()
                self.assertTrue(page.locator("#photo").is_disabled())
                self.assertTrue(page.locator("#choose").is_enabled())
                # Cancelling pending camera acquisition releases the late track.
                page.evaluate("phoneCameraHardware.denyCamera=false; phoneCameraHardware.delayCamera=300")
                acquired = page.evaluate("phoneCameraHardware.acquired")
                stopped = page.evaluate("phoneCameraHardware.stopped")
                page.locator("#open").click()
                page.wait_for_function("() => document.getElementById('open').textContent === 'Cancel camera'")
                page.locator("#open").click()
                page.wait_for_function("() => phoneCameraHardware.acquired > " + str(acquired) + " && phoneCameraHardware.stopped > " + str(stopped))
                self.assertTrue(page.locator("#preview").evaluate("element => element.hidden"))
                self.assertTrue(page.locator("#photo").is_disabled())
                self.assertEqual(errors, [])
                self.assertEqual(external, [])
            finally:
                browser.close()


def ImageTk_image(photo):
    from PIL.ImageTk import getimage
    return getimage(photo)
