"""Phone source controls; all Tk work stays on the application thread."""

from queue import Empty
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk
import qrcode

from .phone_server import PHONE_SOURCE, PhoneReceiver


class PhoneTools:
    @property
    def live_source_active(self):
        return ((self.source_mode == "camera" and self.camera_on)
                or (self.source_mode == "phone" and self.phone_streaming))

    def build_phone_controls(self, row):
        self.phone_receiver = None
        self.retired_receivers = []
        self.phone_streaming = False
        self.phone_generation = None
        self.phone_kind = None
        self.phone_detect_pending = False
        self.phone_connection_visible = False
        self.phone_qr_key = None
        self.phone_url = tk.StringVar()
        self.phone_address = tk.StringVar()
        self.phone_status = tk.StringVar(value="Preparing phone connection…")
        self.phone_panel = ttk.Frame(self.camera_panel, padding=4)
        self.phone_panel.grid(row=row, column=0, sticky="ew")
        ttk.Label(self.phone_panel, text="Phone camera", font="TkHeadingFont").pack(anchor="w")
        ttk.Label(self.phone_panel, textvariable=self.phone_status, wraplength=300,
                  justify="left").pack(fill="x", pady=4)
        self.phone_addresses = ttk.Combobox(self.phone_panel, textvariable=self.phone_address,
                                            state="readonly", width=29)
        self.phone_addresses.pack(fill="x", pady=3)
        self.phone_addresses.bind("<<ComboboxSelected>>", lambda event: self.update_phone_link())
        ttk.Entry(self.phone_panel, textvariable=self.phone_url, state="readonly", width=32).pack(fill="x")
        actions = ttk.Frame(self.phone_panel)
        actions.pack(fill="x", pady=4)
        ttk.Button(actions, text="Copy link", command=self.copy_phone_link).pack(side="left")
        self.phone_certificate_button = ttk.Button(actions, text="Compare certificates",
                                                    command=self.show_phone_identity, state="disabled")
        self.phone_certificate_button.pack(side="left", padx=3)
        self.phone_view_button = ttk.Button(self.phone_panel, text="Show image",
                                             command=self.toggle_phone_connection, state="disabled")
        self.phone_view_button.pack(anchor="w", pady=3)
        ttk.Label(self.phone_panel, text="Same Wi-Fi or hotspot. Choose photo needs no certificate. Browser camera uses local HTTPS.",
                  wraplength=300, justify="left").pack(fill="x")
        self.phone_panel.grid_remove()

    def build_phone_view(self):
        """The pairing card lives in the image viewport, never the sidebar."""
        self.phone_view = tk.Frame(self.video_label, background="black")
        tk.Label(self.phone_view, text="Connect your phone", background="black",
                 foreground="white", font=("TkDefaultFont", 18)).pack(pady=(0, 12))
        self.phone_qr = ttk.Label(self.phone_view)
        self.phone_qr.pack()
        self.phone_view_hint = tk.Label(self.phone_view, text="Scan this QR on the same Wi-Fi or hotspot.\nChoose Open camera or Send video.",
                                       background="black", foreground="white", wraplength=420)
        self.phone_view_hint.pack(pady=(12, 0))
        self.video_label.bind("<Configure>", lambda event: self.update_phone_link()
                              if self.phone_connection_visible else None)

    def show_phone_connection(self):
        self.phone_connection_visible = True
        self.video_label.config(image="", text="", cursor="")
        self.video_label.image = None
        self.phone_view.place(relx=.5, rely=.5, anchor="center")
        self.phone_view_button.config(text="Show image",
                                      state="normal" if self.last_frame is not None else "disabled")
        self.update_phone_link()

    def hide_phone_connection(self):
        self.phone_connection_visible = False
        self.phone_view.place_forget()
        self.phone_qr.config(image="")
        self.phone_qr.image = None
        self.phone_qr_key = None
        self.phone_view_button.config(text="Show QR", state="normal")

    def toggle_phone_connection(self):
        if self.phone_connection_visible:
            self.hide_phone_connection()
        else:
            self.show_phone_connection()

    def show_phone_panel(self, visible):
        for control in self.camera_controls.values():
            control.grid_remove() if visible else control.grid()
        if visible:
            self.phone_panel.grid()
        else:
            self.phone_panel.grid_remove()

    def select_phone(self):
        self.stop_phone()
        self.session += 1
        self.worker.commands.put((self.session, "close", None))
        self.enable_camera_controls(False)
        self.source_mode = "phone"
        self.source_description = "Phone camera"
        self.clear_video()
        self.live_average.max_age = .35
        self.show_phone_connection()
        self.show_phone_panel(True)
        self.phone_status.set("Preparing phone connection…")
        self.loading_label.config(text="Phone: waiting for a photo or video.")
        self.phone_receiver = PhoneReceiver(self.options_store.path.parent / "phone-link")
        self.phone_receiver.start()
        self.camera_dropdown.config(state="readonly")
        self.refresh_button.config(state="normal")

    def stop_phone(self):
        if getattr(self, "phone_receiver", None):
            self.phone_receiver.stop()
            self.retired_receivers.append(self.phone_receiver)
            self.phone_receiver = None
        self.phone_streaming = False
        self.phone_generation = None
        self.phone_kind = None
        self.phone_detect_pending = False
        self.live_average.max_age = .12
        if hasattr(self, "phone_panel"):
            self.show_phone_panel(False)
            self.hide_phone_connection()
            self.phone_url.set("")
            self.phone_certificate_button.config(state="disabled")

    def update_phone_link(self):
        receiver = self.phone_receiver
        if not receiver or not receiver.http_port:
            return
        addresses = receiver.addresses
        self.phone_addresses.config(values=addresses)
        if self.phone_address.get() not in addresses:
            self.phone_address.set(addresses[0])
        url = receiver.url(self.phone_address.get())
        self.phone_url.set(url)
        self.phone_certificate_button.config(state="normal" if receiver.identity else "disabled")
        if self.phone_connection_visible:
            qr = qrcode.QRCode(border=4, box_size=1)
            qr.add_data(url)
            qr.make(fit=True)
            image = qr.make_image(fill_color="black", back_color="white").get_image()
            width = self.video_label.winfo_width()
            height = self.video_label.winfo_height()
            available = min(500, width - 40 if width > 1 else 500,
                            height - 120 if height > 1 else 500)
            scale = max(2, available // image.width)
            key = (url, scale)
            if key != self.phone_qr_key:
                image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
                photo = ImageTk.PhotoImage(image)
                self.phone_qr.config(image=photo)
                self.phone_qr.image = photo
                self.phone_qr_key = key
            self.phone_view_hint.config(wraplength=max(200, min(420, width - 40)))

    def copy_phone_link(self):
        if self.phone_url.get():
            self.root.clipboard_clear()
            self.root.clipboard_append(self.phone_url.get())

    def show_phone_identity(self):
        receiver = self.phone_receiver
        if not receiver or not receiver.identity:
            return
        window = tk.Toplevel(self.root)
        window.title("Compare local certificates")
        window.transient(self.root)
        ttk.Label(window, text="Match these SHA-256 fingerprints with your phone's certificate details.\n"
                  "Choose photo works without installation. Browser camera trust setup is optional.",
                  padding=10, justify="left").pack(fill="x")
        for label, key in (("HTTPS server certificate", "server_sha256"), ("Local root certificate", "ca_sha256")):
            ttk.Label(window, text=label, padding=(10, 3)).pack(anchor="w")
            text = tk.Text(window, height=3, width=65, wrap="char")
            text.insert("1.0", receiver.identity[key])
            text.config(state="disabled")
            text.pack(fill="x", padx=10)
        ttk.Label(window, text="Check the server fingerprint in browser certificate details; check the root\n"
                  "fingerprint before installing it. The phone page also shows both numbers.\n"
                  "Certificates and private keys are generated only on this computer.",
                  padding=10, justify="left").pack(fill="x")
        ttk.Button(window, text="Close", command=window.destroy).pack(pady=8)

    def poll_phone(self):
        self.retired_receivers[:] = [receiver for receiver in self.retired_receivers if not receiver.finished.is_set()]
        receiver = self.phone_receiver
        if not receiver:
            return
        while True:
            try:
                kind, message = receiver.events.get_nowait()
            except Empty:
                break
            if kind == "error":
                self.phone_status.set(f"Could not start phone receiver: {message}")
            else:
                self.phone_status.set("Scan this QR with your phone. Choose Open camera or Send video."
                                      + (f" Video is unavailable: {receiver.tls_error} Choose photo still works." if receiver.tls_error else ""))
                if receiver.addresses == ["127.0.0.1"]:
                    self.phone_status.set("No usable local IPv4 address. Connect this computer to the phone’s Wi-Fi or hotspot, then select the phone source again.")
                self.update_phone_link()
        try:
            packet = receiver.frames.get_nowait()
        except Empty:
            packet = None
        if packet is not None:
            # A stopped/replaced video session cannot reappear from the queue.
            if packet["kind"] == "frame" and not receiver.status()["streaming"]:
                packet = None
        if packet is not None:
            self.hide_phone_connection()
            fresh = (packet["kind"] == "photo" or packet["generation"] != self.phone_generation
                     or (self.last_frame is not None and self.last_frame.shape != packet["frame"].shape))
            continuing = (packet["kind"] == "frame" and self.phone_kind == "frame"
                          and self.last_frame is not None and self.detection is not None
                          and self.last_frame.shape == packet["frame"].shape)
            self.phone_streaming = packet["kind"] == "frame"
            self.phone_kind = packet["kind"]
            self.phone_generation = packet["generation"]
            self.source_description = "Phone video" if self.phone_streaming else "Phone photo"
            if fresh and continuing:
                # A reconnect of the same view retains manual circles and view edits.
                self.analysis_generation += 1
                self.vane_generation += 1
                self.live_average.reset()
                self.tracking_active = self.track_live.get()
                self.view_frozen = self.picking_role is not None or self.radius_editing or self.pan_anchor is not None
                self.accept_live_frame(packet["frame"])
            elif fresh:
                self.invalidate_review()
                self.last_frame = packet["frame"]
                self.reset_view()
                self.display_transform = None
                self.reset_crosshair()
                self.phone_detect_pending = True
            else:
                self.accept_live_frame(packet["frame"])
            if self.phone_streaming:
                self.phone_status.set("Video connected. Stop it on the phone to send photos.")
                self.loading_label.config(text="Phone video connected.")
            else:
                self.phone_status.set(f"Photo received (receipt {packet['receipt']}). Ready for another photo or video.")
                self.loading_label.config(text="Image: phone photo")
                self.update_phone_link()
        if self.phone_detect_pending and not self.analysis_busy and self.last_frame is not None:
            self.phone_detect_pending = False
            self.start_detection()
        if self.phone_streaming and not receiver.status()["streaming"]:
            self.phone_streaming = False
            self.phone_generation = None
            self.phone_detect_pending = False
            self.tracking_active = False
            self.tracking_pending_frame = None
            self.live_average.reset()
            self.analysis_generation += 1
            self.observations_current = False
            self.view_frozen = True
            self.phone_status.set("Video stopped or disconnected. Scan the link or tap Send video again.")
            self.loading_label.config(text="Phone: waiting for video. Last image retained.")
            self.show_phone_connection()
            self.refresh_review_selection()
