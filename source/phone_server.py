"""Offline, session-scoped phone uploads. No Tk calls or public services."""

from io import BytesIO
import json
from pathlib import Path
from queue import Empty, Full, Queue
import secrets
import socket
import sys
import traceback
from threading import Event, Lock, Thread, BoundedSemaphore
from time import monotonic
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from .local_network import network_addresses


PHONE_SOURCE = "Stream from the phone"
MAX_PHOTO = 25 * 1024 * 1024
MAX_FRAME = 4 * 1024 * 1024
MAX_PIXELS = 60_000_000


class ReceiverHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(3)
        return connection, address


class PhoneReceiver:
    """One decoder and one latest frame; uploads never build an analysis backlog."""

    def __init__(self, directory, *, addresses=None, bind_host="0.0.0.0"):
        self.directory = Path(directory)
        self.addresses = list(addresses) if addresses is not None else []
        self.bind_host = bind_host
        self.token = secrets.token_urlsafe(24)
        self.prefix = f"/{self.token}/"
        self.lock = Lock()
        self.decode_lock = BoundedSemaphore(1)
        self.stop_event = Event()
        self.ready = Event()
        self.finished = Event()
        self.events = Queue()
        self.frames = Queue(maxsize=1)
        self.servers = []
        self.threads = []
        self.identity = {}
        self.tls_error = ""
        self.http_port = self.https_port = None
        self.stream_id = None
        self.generation = 0
        self.sequence = -1
        self.last_received = 0
        self.receipt = 0
        self.original_photo = None
        self.start_thread = Thread(target=self._start, name="phone-link-start", daemon=True)

    def start(self):
        self.start_thread.start()

    def url(self, address=None, secure=False):
        port = self.https_port if secure else self.http_port
        return f"{'https' if secure else 'http'}://{address or self.addresses[0]}:{port}{self.prefix}" if port else ""

    def _serve(self, context=None):
        server = ReceiverHTTPServer((self.bind_host, 0), self._handler())
        if context:
            # Handshake in the request thread; a stalled phone cannot block accept.
            server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)
        with self.lock:
            if self.stop_event.is_set():
                server.server_close()
                return None
            self.servers.append(server)
            thread = Thread(target=server.serve_forever, kwargs={"poll_interval": .1}, daemon=True)
            self.threads.append(thread)
            thread.start()
        return server.server_address[1]

    def _start(self):
        try:
            if not self.addresses:
                self.addresses = network_addresses()
            # HTTP photos are available even if certificate creation fails.
            self.http_port = self._serve()
            self.events.put(("http", None))
            if not self.stop_event.is_set():
                try:
                    from .phone_tls import local_identity
                    context, self.identity = local_identity(self.directory, self.addresses)
                    self.https_port = self._serve(context)
                except (OSError, ValueError, ImportError) as error:
                    self.tls_error = str(error)
                    self.write_error_log(error)
            self.events.put(("ready", None))
        except OSError as error:
            self.write_error_log(error)
            self.events.put(("error", str(error)))
        finally:
            self.ready.set()

    def write_error_log(self, error):
        """Record the actual interpreter/cause, without pairing links or keys."""
        detail = f"Interpreter: {sys.executable}\nPython: {sys.version}\n\n{traceback.format_exc()}"
        try:
            self.directory.parent.mkdir(parents=True, exist_ok=True)
            (self.directory.parent / "phone-error.log").write_bytes(detail.encode("utf-8"))
        except OSError:
            pass

    def stop(self):
        self.stop_event.set()
        # shutdown can wait for accept's poll; never hold up the Tk event loop.
        Thread(target=self._close, name="phone-link-close", daemon=True).start()

    def _close(self):
        self.start_thread.join()
        with self.lock:
            servers = list(self.servers)
            self.stream_id = None
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join(2)
        self.finished.set()

    def status(self):
        with self.lock:
            return {"streaming": bool(self.stream_id and monotonic() - self.last_received < 4),
                    "receipt": self.receipt, "sequence": self.sequence}

    def _publish(self, packet):
        try:
            self.frames.put_nowait(packet)
        except Full:
            try:
                self.frames.get_nowait()
            except Empty:
                pass
            self.frames.put_nowait(packet)

    def _decode(self, data):
        # Keep HEIC support lazy so ordinary photos work without the plugin.
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass
        with Image.open(BytesIO(data)) as image:
            if min(image.size) < 32 or image.width * image.height > MAX_PIXELS:
                raise ValueError("Use a photo between 32 pixels and 60 megapixels.")
            image = ImageOps.exif_transpose(image).convert("RGB")
            return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)

    def _handler(self):
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def handle(self):
                try:
                    super().handle()
                except (ConnectionError, TimeoutError, OSError):
                    pass  # Browsers may abandon requests or certificate handshakes.

            def log_message(self, *args):
                pass  # The pairing token must not appear in request logs.

            def reply(self, code, data, content_type="application/json"):
                body = json.dumps(data).encode() if content_type == "application/json" else data
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Permissions-Policy", "camera=(self), microphone=()")
                self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; media-src 'self' blob:; img-src 'self' blob:; frame-ancestors 'none'")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                self.wfile.write(body)

            def route(self):
                host = self.headers.get("Host", "")
                allowed = {f"{address}:{port}" for address in receiver.addresses + ["127.0.0.1", "localhost"]
                           for port in (receiver.http_port, receiver.https_port)}
                if host not in allowed or receiver.stop_event.is_set():
                    self.reply(403, {"error": "This phone link is not available."})
                    return None
                path = urlsplit(self.path).path
                if not path.startswith(receiver.prefix):
                    self.reply(404, {"error": "Open the current QR link from the collimator."})
                    return None
                return path[len(receiver.prefix):]

            def do_GET(self):
                route = self.route()
                if route is None:
                    return
                if route in ("", "phone.js"):
                    name = "phone.html" if route == "" else route
                    self.reply(200, (Path(__file__).parent / "web" / name).read_bytes(),
                               "text/html; charset=utf-8" if route == "" else "text/javascript; charset=utf-8")
                elif route == "config":
                    address = self.headers["Host"].split(":")[0]
                    self.reply(200, {"https_url": receiver.url(address, secure=True),
                                    "ca_sha256": receiver.identity.get("ca_sha256", ""),
                                    "server_sha256": receiver.identity.get("server_sha256", ""),
                                    "tls_error": receiver.tls_error})
                elif route == "status":
                    self.reply(200, receiver.status())
                elif route == "phone.mobileconfig" and receiver.identity:
                    from .phone_profile import certificate_profile
                    self.reply(200, certificate_profile(receiver.identity), "application/x-apple-aspen-config")
                elif route == "ca.cer" and receiver.identity:
                    self.reply(200, receiver.identity["ca_der"], "application/pkix-cert")
                else:
                    self.reply(404, {"error": "Not found."})

            def do_POST(self):
                route = self.route()
                if route is None:
                    return
                origin = self.headers.get("Origin")
                scheme = "https" if self.server.server_address[1] == receiver.https_port else "http"
                if origin and origin != f"{scheme}://{self.headers['Host']}":
                    self.reply(403, {"error": "Open this link directly on your phone."})
                    return
                try:
                    limit = MAX_PHOTO if route == "photo" else MAX_FRAME if route == "frame" else 2048
                    length = int(self.headers.get("Content-Length", "0"))
                    if self.headers.get("Transfer-Encoding") or not 0 < length <= limit:
                        self.reply(413, {"error": "Upload is empty or too large (photos: 25 MB; video frames: 4 MB)."})
                        return
                    decoding = route in ("photo", "frame")
                    if decoding and not receiver.decode_lock.acquire(blocking=False):
                        self.reply(503, {"error": "Receiving another frame. Try again."})
                        return
                    try:
                        data = self.rfile.read(length)
                        if len(data) != length:
                            raise ValueError("Upload was interrupted. Send it again.")
                        if route in ("stream/start", "stream/stop"):
                            payload = json.loads(data)
                            if not isinstance(payload, dict):
                                raise ValueError("Video session must be an object.")
                            stream_id = payload.get("stream_id")
                            if not isinstance(stream_id, str) or not 8 <= len(stream_id) <= 100:
                                raise ValueError("Invalid video session.")
                            with receiver.lock:
                                if route == "stream/start":
                                    receiver.generation += 1
                                    receiver.stream_id, receiver.sequence = stream_id, -1
                                    receiver.last_received = 0
                                elif receiver.stream_id == stream_id:
                                    receiver.stream_id = None
                                    receiver.generation += 1
                            self.reply(200, {"ok": True})
                            return
                        if route not in ("photo", "frame"):
                            self.reply(404, {"error": "Not found."})
                            return
                        sequence = int(self.headers.get("X-Frame-Sequence", "-1"))
                        stream_id = self.headers.get("X-Stream-ID")
                        with receiver.lock:
                            if route == "frame" and (stream_id != receiver.stream_id or not stream_id or sequence <= receiver.sequence):
                                self.reply(409, {"error": "Video session has ended or this frame is stale."})
                                return
                            generation = receiver.generation
                        frame = receiver._decode(data)
                        with receiver.lock:
                            if receiver.stop_event.is_set():
                                self.reply(410, {"error": "Phone receiver stopped. Open the new QR link."})
                                return
                            if route == "frame" and (stream_id != receiver.stream_id or generation != receiver.generation):
                                self.reply(409, {"error": "Video session ended while this frame was arriving."})
                                return
                            receiver.receipt += 1
                            if route == "photo":
                                receiver.stream_id = None
                                receiver.generation += 1
                                receiver.original_photo = data
                            else:
                                receiver.sequence = sequence
                            receiver.last_received = monotonic()
                            packet = {"frame": frame, "kind": route, "generation": receiver.generation,
                                      "sequence": sequence, "receipt": receiver.receipt}
                            receiver._publish(packet)
                        self.reply(200, {"ok": True, "receipt": packet["receipt"],
                                         "width": frame.shape[1], "height": frame.shape[0]})
                    finally:
                        if decoding:
                            receiver.decode_lock.release()
                except (ValueError, TypeError, UnidentifiedImageError, Image.DecompressionBombError, OSError) as error:
                    try:
                        self.reply(400, {"error": f"Could not receive image: {error}"})
                    except OSError:
                        pass

        return Handler
