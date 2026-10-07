import tkinter as tk
from tkinter import messagebox, ttk
import cv2
import math
import sys
from queue import Empty, Full, Queue
from threading import Event, Thread
from time import monotonic
from PIL import Image, ImageTk
from .camera_properties import PropertyInfo, query_camera_properties
from .collimation_review import ReviewTools
from .feature_detection import DisplayTransform, draw_detection


def open_camera(index):
    # Keep native capability queries and capture on the same device ordering.
    if sys.platform == "win32":
        return cv2.VideoCapture(index, cv2.CAP_DSHOW)
    return cv2.VideoCapture(index)


class CameraWorker(Thread):
    """Own the capture device; never access Tkinter from this thread."""

    def __init__(self, capture_factory=None, max_cameras=10, capability_provider=None):
        super().__init__(daemon=True)
        self.capture_factory = capture_factory or open_camera
        self.capability_provider = capability_provider or (
            query_camera_properties if capture_factory is None else lambda index: {})
        self.capabilities = {}
        self.max_cameras = max_cameras
        self.commands = Queue()
        self.events = Queue()
        self.frames = Queue(maxsize=1)
        self.stop_event = Event()
        self.capture = None
        self.session = 0

    def release_camera(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def handle_command(self, session, action, data):
        if action in ("scan", "open", "close"):
            self.release_camera()
            self.session = session
            self.capabilities = {}
        elif session != self.session:
            return

        if action == "scan":
            cameras = []
            for index in range(self.max_cameras):
                if self.stop_event.is_set():
                    return
                cap = None
                try:
                    cap = self.capture_factory(index)
                    if cap.isOpened():
                        cameras.append(index)
                except cv2.error:
                    continue
                finally:
                    if cap is not None:
                        cap.release()
            self.events.put((session, "cameras", cameras))
        elif action == "open":
            try:
                ranges = self.capability_provider(data)
            except OSError:
                ranges = {}
            self.capabilities = {prop: ranges.get(name, PropertyInfo())
                                 for prop, name in CAMERA_PROPERTIES.items()}
            self.capture = self.capture_factory(data)
            if not self.capture.isOpened():
                self.release_camera()
                self.events.put((session, "error", "Failed to open the camera. Try Refresh cameras."))
                return
            values = {}
            for prop in CAMERA_PROPERTIES:
                try:
                    value = self.capture.get(prop)
                    if math.isfinite(value):
                        values[prop] = value
                except cv2.error:
                    continue
            self.events.put((session, "opened", (values, self.capabilities)))
        elif action == "set" and self.capture is not None:
            prop, requested = data
            name = CAMERA_PROPERTIES[prop]
            info = self.capabilities.get(prop, PropertyInfo())
            if info.status == "unsupported" or (info.status == "supported" and not info.adjustable):
                self.events.put((session, "property", (prop, None, f"{name}: manual adjustment is unavailable.")))
                return
            if info.adjustable:
                requested = info.normalize(requested)
            accepted = self.capture.set(prop, requested)
            actual = self.capture.get(prop)
            if not math.isfinite(actual):
                actual = None
            if not accepted:
                message = f"{name}: camera rejected this value or does not support the control."
            elif actual is None:
                message = f"{name}: value sent; camera could not report its value."
            elif not math.isclose(actual, requested, rel_tol=1e-4, abs_tol=1e-4):
                message = f"{name}: requested {requested:g}, camera reports {actual:g} (adjusted or ignored)."
            else:
                message = f"{name}: camera reports {actual:g}."
            self.events.put((session, "property", (prop, actual, message)))

    def run(self):
        try:
            while not self.stop_event.is_set():
                try:
                    command = self.commands.get(timeout=0.01 if self.capture is not None else 0.1)
                except Empty:
                    command = None
                if command is not None:
                    try:
                        self.handle_command(*command)
                    except cv2.error as error:
                        if command[1] != "set":
                            self.release_camera()
                        self.events.put((self.session, "error", f"Camera operation failed: {error}"))
                    # Process queued changes before reading another frame.
                    continue
                if self.capture is None or self.stop_event.is_set():
                    continue
                try:
                    ok, frame = self.capture.read()
                except cv2.error:
                    ok, frame = False, None
                if not ok or frame is None or frame.size == 0:
                    self.release_camera()
                    self.events.put((self.session, "disconnected", "Camera stopped delivering frames. Try Refresh cameras."))
                    continue
                try:
                    self.frames.put_nowait((self.session, frame))
                except Full:
                    try:
                        self.frames.get_nowait()
                    except Empty:
                        pass
                    self.frames.put_nowait((self.session, frame))
        finally:
            self.release_camera()


CAMERA_PROPERTIES = {
    cv2.CAP_PROP_GAIN: "Gain",
    cv2.CAP_PROP_EXPOSURE: "Exposure",
    cv2.CAP_PROP_ZOOM: "Zoom",
    cv2.CAP_PROP_FOCUS: "Focus",
}


# The reflected secondary silhouette is intentionally not a Newtonian target:
# https://catseyecollimation.com/pensack.pdf
# Controls follow the outside-to-inside fitting order. Radii are starter presets,
# not measurements or physical mirror-size ratios; fit them to the camera view.
NEWTONIAN_GUIDES = (
    ("Focuser edge", (255, 170, 0), 200),
    ("Secondary edge", (0, 210, 255), 180),
    ("Primary reflection", (60, 230, 110), 160),
)
NEWTONIAN_HINT = (
    "Fit Focuser edge first, then Secondary edge and Primary reflection. "
    "Preset sizes: resize each to its visible edge."
)
NEWTONIAN_HELP = (
    "1. Fit the orange Focuser edge guide to the inside rim of the focuser or sight tube. "
    "Click the image to place the guides, then use arrow keys to fine-tune their center.\n\n"
    "2. Fit the cyan Secondary edge guide to the actual visible edge of the secondary mirror. "
    "Fit the green Primary reflection guide to the edge of the primary mirror reflected in it.\n\n"
    "The full primary reflection is seen within the secondary's face. Their apparent sizes "
    "depend on the camera and focuser position. The starting circles are presets, not detected edges.\n\n"
    "3. Compare these edges against the same center. The crosshair is also a reference "
    "for the primary mirror's center mark.\n\n"
    "The dark reflected silhouette of the secondary may be offset even when correctly "
    "collimated; do not use it as the Secondary edge target. Confirm final primary alignment "
    "with a suitable Cheshire or star test.\n\n"
    "Each circle marks a different visible boundary. Their sizes are independent "
    "because those boundaries have different apparent sizes. All guides share one center. "
    "Drag a size slider, scroll over it, or use +/− to fit its boundary. "
    "Untick any reference you do not need. These are manual visual guides."
)


def prepare_frame(frame, zoom, display_width, display_height, center=None):
    """Crop for zoom/pan, then fit without stretching the camera image."""
    height, width = frame.shape[:2]
    transform = DisplayTransform.for_image((width, height), zoom, display_width, display_height, center)
    x, y = transform.crop_x, transform.crop_y
    cropped = frame[y:y + transform.crop_height, x:x + transform.crop_width]
    size = (transform.width, transform.height)
    return cv2.cvtColor(cv2.resize(cropped, size), cv2.COLOR_BGR2RGB)


class CameraControl(tk.Frame):
    """Use a driver-defined slider, or a numeric fallback for unknown ranges."""

    def __init__(self, root, prop, name, on_change):
        super().__init__(root)
        self.prop = prop
        self.name = name
        self.on_change = on_change
        self.info = PropertyInfo()
        self.enabled = False
        self.last_value = None
        self.pending_after = None
        self.value = tk.StringVar(value="")
        self.title = tk.Label(self, text=name, anchor="w", width=8)
        self.title.grid(row=0, column=0, sticky="w")
        # Tk's resolution snaps relative to zero. Snap relative to the driver
        # minimum ourselves so a range such as 3..19 with step 4 stays valid.
        self.slider = tk.Scale(self, orient=tk.HORIZONTAL, length=185,
                               resolution=-1, command=self.slider_changed)
        self.slider.grid(row=0, column=1)
        self.numeric = tk.Frame(self)
        self.numeric.grid(row=0, column=1)
        self.entry = ttk.Entry(self.numeric, textvariable=self.value, width=9)
        self.entry.grid(row=0, column=0)
        self.button = ttk.Button(self.numeric, text="Apply", width=6,
                                 command=lambda: self.on_change(self.prop, self.value.get()))
        self.button.grid(row=0, column=1, padx=4)
        self.entry.bind("<Return>", lambda event: self.on_change(self.prop, self.value.get()))
        self.note = tk.Label(self, text="", anchor="w", wraplength=185, justify="left")
        self.note.grid(row=0, column=1, sticky="w")
        for widget in (self, self.slider, self.numeric, self.entry, self.button, self.note):
            widget.bind("<MouseWheel>", self.scroll)
        for key, direction in (("Left", -1), ("Down", -1), ("Right", 1), ("Up", 1)):
            self.slider.bind(f"<{key}>", lambda event, d=direction: self.step_value(d))
        self.configure_for_camera(PropertyInfo(), None, False)

    def cancel_pending(self):
        if self.pending_after is not None:
            self.after_cancel(self.pending_after)
            self.pending_after = None

    def configure_for_camera(self, info, actual, connected=True):
        self.cancel_pending()
        self.enabled = False
        self.info = info
        self.title.config(text=self.name)
        self.note.grid()
        self.slider.config(state="disabled")
        self.slider.grid_remove()
        self.numeric.grid_remove()
        self.entry.config(state="disabled")
        self.button.config(state="disabled")
        self.value.set("" if actual is None else f"{actual:g}")
        if not connected:
            self.note.config(text="Unavailable")
        elif info.status == "unsupported":
            self.note.config(text="Not supported")
        elif info.status == "supported" and not info.adjustable:
            self.note.config(text="Fixed value" if info.flags & 2 else
                             "Automatic only" if info.flags & 1 else "Manual unavailable")
        elif info.adjustable:
            # Tk ignores Scale.set while the widget is disabled.
            self.slider.config(from_=info.minimum, to=info.maximum, state="normal")
            self.last_value = info.normalize(actual if actual is not None else info.default)
            self.slider.set(self.last_value)
            self.slider.grid()
            self.note.grid_remove()
            self.enabled = True
            self.slider.config(state="normal")
        else:
            self.numeric.grid()
            self.note.grid_remove()
            self.enabled = True
            self.entry.config(state="normal")
            self.button.config(state="normal")

    def set_reported_value(self, actual):
        if self.pending_after is not None:
            return  # Preserve a newer user adjustment while it is pending.
        self.value.set(f"{actual:g}")
        if self.info.adjustable:
            self.last_value = self.info.normalize(actual)
            self.slider.set(self.last_value)

    def slider_changed(self, value):
        if not self.enabled or not self.info.adjustable:
            return
        requested = self.info.normalize(float(value))
        self.slider.set(requested)
        if requested == self.last_value:
            return
        self.last_value = requested
        self.value.set(f"{requested:g}")
        self.cancel_pending()
        self.pending_after = self.after(120, self.send_pending)

    def send_pending(self):
        self.pending_after = None
        if self.enabled:
            self.on_change(self.prop, self.last_value)

    def step_value(self, direction):
        if self.enabled and self.info.adjustable:
            self.slider.set(self.info.normalize(self.slider.get() + direction * self.info.step))
        return "break"

    def scroll(self, event):
        if event.delta:
            self.step_value(1 if event.delta > 0 else -1)
        return "break"  # Do not also change the video's digital zoom.


class RingControl(tk.Frame):
    """A named, optional boundary reference with a matching video color."""

    def __init__(self, root, color, radius):
        super().__init__(root)
        self.color = color
        self.name = tk.StringVar(value="")
        self.visible = tk.BooleanVar(value=True)
        tk.Frame(self, background="#{:02x}{:02x}{:02x}".format(*color),
                 width=8, height=12).grid(row=0, column=0, padx=(0, 3))
        self.checkbox = tk.Checkbutton(self, textvariable=self.name, variable=self.visible,
                                       width=17, anchor="w")
        self.checkbox.grid(row=0, column=1, sticky="w")
        tk.Button(self, text="−", width=2, command=lambda: self.resize(-1)).grid(row=0, column=2)
        self.slider = tk.Scale(self, from_=10, to=400, orient=tk.HORIZONTAL,
                               length=95, showvalue=False, width=10)
        self.slider.grid(row=0, column=3)
        self.slider.set(radius)
        tk.Button(self, text="+", width=2, command=lambda: self.resize(1)).grid(row=0, column=4)
        for widget in (self, self.checkbox, self.slider):
            widget.bind("<MouseWheel>", self.scroll)
        for key, direction in (("Left", -1), ("Down", -1), ("Right", 1), ("Up", 1)):
            self.slider.bind(f"<{key}>", lambda event, d=direction: self.resize(d))

    def resize(self, direction):
        self.slider.set(self.slider.get() + direction)
        return "break"

    def scroll(self, event):
        if event.delta:
            self.resize(1 if event.delta > 0 else -1)
        return "break"


class WebcamApp(ReviewTools):
    def __init__(self, root, options_store=None):
        self.root = root
        self.root.geometry("1300x750")
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)
        self.windowed_state = "zoomed"
        self.root.title("Astro Collimator")
        self.session = 0
        self.closing = False
        self.camera_on = False
        self.camera_controls = {}
        self.last_frame = None
        self.after_id = None
        self.worker = CameraWorker()
        self.build_review_tools(options_store)

        row_index = 0

        # Dropdown for webcam selection
        self.camera_label = tk.Label(self.camera_panel, text="Select Camera:")
        self.camera_label.grid(row=row_index, column=0, padx=5)
        row_index += 1

        self.camera_list = []
        self.selected_camera = tk.StringVar(value="")
        self.camera_dropdown = ttk.Combobox(self.camera_panel, textvariable=self.selected_camera, values=self.camera_list,
                                            state="readonly")
        self.camera_dropdown.grid(row=row_index, column=0, padx=5)
        self.camera_dropdown.bind("<<ComboboxSelected>>", self.on_camera_selected)
        row_index += 1

        self.refresh_button = tk.Button(self.camera_panel, text="Refresh cameras", command=self.refresh_cameras)
        self.refresh_button.grid(row=row_index, column=0, padx=5, pady=5)
        row_index += 1

        for prop, name in CAMERA_PROPERTIES.items():
            control = CameraControl(self.camera_panel, prop, name, self.set_camera_value)
            control.grid(row=row_index, column=0, padx=5, pady=0, sticky="w")
            self.camera_controls[prop] = control
            row_index += 1

        tk.Label(self.camera_panel, text="Wheel: zoom. Drag rim: move; elsewhere: pan. Hold right: blink.",
                 wraplength=280).grid(row=row_index, column=0, padx=5)
        row_index += 1

        self.zoom_factor = 1.0
        self.view_center = None
        self.pan_anchor = None
        self.pan_dragged = False
        self.pan_click_token = None
        self.circle_drag = None
        self.resize_hover_anchor = None
        self.display_transform = None
        row_index = 0

        self.guides_frame = ttk.LabelFrame(self.manual_panel, text="Newtonian collimation guides")
        self.guides_frame.grid(row=row_index, column=0, padx=5, pady=6, sticky="ew")
        row_index += 1
        guide_actions = tk.Frame(self.guides_frame)
        guide_actions.grid(row=0, column=0, sticky="ew", padx=4)
        self.guides_visible = tk.BooleanVar(value=True)
        tk.Checkbutton(guide_actions, text="Show guides", variable=self.guides_visible,
                       command=self.on_guide_visibility_changed).grid(row=0, column=0)
        ttk.Button(guide_actions, text="How to use", command=self.show_guide_help).grid(row=0, column=1, padx=5)
        self.ring_controls = []
        for index, (name, color, radius) in enumerate(NEWTONIAN_GUIDES):
            ring = RingControl(self.guides_frame, color, radius)
            ring.name.set(name)
            ring.grid(row=index + 1, column=0, padx=4, sticky="w")
            self.ring_controls.append(ring)
        self.guide_hint = tk.Label(self.guides_frame, text=NEWTONIAN_HINT, wraplength=300, justify="left", anchor="w")
        self.guide_hint.grid(row=4, column=0, padx=5, pady=4, sticky="w")

        tk.Label(self.manual_panel, text="Move guides · drag rim/center or click / arrow keys").grid(row=row_index, column=0)
        row_index += 1

        # D-pad frame
        self.dpad_frame = tk.Frame(self.manual_panel)
        self.dpad_frame.grid(row=row_index, column=0, padx=5)
        row_index += 1

        # D-pad buttons
        self.up_button = tk.Button(self.dpad_frame, text="↑", command=lambda: self.move_crosshair(0, -1), width=5, height=1)
        self.up_button.grid(row=0, column=1)

        self.left_button = tk.Button(self.dpad_frame, text="←", command=lambda: self.move_crosshair(-1, 0), width=5, height=1)
        self.left_button.grid(row=1, column=0)

        self.right_button = tk.Button(self.dpad_frame, text="→", command=lambda: self.move_crosshair(1, 0), width=5, height=1)
        self.right_button.grid(row=1, column=2)

        self.down_button = tk.Button(self.dpad_frame, text="↓", command=lambda: self.move_crosshair(0, 1), width=5, height=1)
        self.down_button.grid(row=2, column=1)

        self.reset_button = tk.Button(self.dpad_frame, text="Center", command=self.reset_crosshair, width=5, height=1)
        self.reset_button.grid(row=1, column=1, padx=5, pady=3)

        # Keyboard bindings for D-pad
        self.root.bind("<Up>", lambda event: self.move_crosshair(0, -1))
        self.root.bind("<Down>", lambda event: self.move_crosshair(0, 1))
        self.root.bind("<Left>", lambda event: self.move_crosshair(-1, 0))
        self.root.bind("<Right>", lambda event: self.move_crosshair(1, 0))

        # Add a blank area below all controls
        self.black_area = tk.Frame(self.manual_panel)
        self.black_area.grid(row=row_index, column=0, sticky="nsew")

        # Video display area
        self.video_label = tk.Label(root, background="black", foreground="white", text="No camera image")
        self.video_label.grid(row=0, column=1, padx=5, sticky="nsew")
        self.video_label.bind("<MouseWheel>", self.zoom_with_scroll)
        self.video_label.bind("<Motion>", self.hover_image)
        self.video_label.bind("<Leave>", lambda event: self.video_label.config(cursor="") if self.pan_anchor is None else None)
        for button in (1, 2):
            self.video_label.bind(f"<ButtonPress-{button}>", self.begin_pan)
            self.video_label.bind(f"<B{button}-Motion>", self.pan_image)
            self.video_label.bind(f"<ButtonRelease-{button}>", self.end_pan)
        self.video_label.bind("<ButtonPress-3>", self.begin_blink)
        self.video_label.bind("<ButtonRelease-3>", self.end_blink)
        self.root.bind("<ButtonRelease-3>", self.end_blink, add="+")
        self.root.bind("<FocusOut>", self.end_blink, add="+")
        self.root.bind("<Control-0>", lambda event: self.reset_view())
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)

        # Ensure the video frame expands with the window
        self.root.grid_columnconfigure(1, weight=1)  # Video frame column

        # Ensure the black area takes up remaining space
        self.root.grid_rowconfigure(0, weight=1)

        # Initialize crosshair state
        self.show_crosshair = self.guides_visible.get()

        # Set initial video dimensions to match the window size
        scaling = 1.5
        self.video_width = int(640 * scaling)
        self.video_height = int(480 * scaling)

        self.crosshair_x = self.video_width // 2  # Initialize crosshair center X
        self.crosshair_y = self.video_height // 2  # Initialize crosshair center Y

        # Keep changing advice/selection text from moving the image viewport.
        self.root.update_idletasks()
        self.sidebar.config(width=max(350, self.sidebar.winfo_reqwidth()))
        self.sidebar.pack_propagate(False)
        self.root.state("zoomed")
        self.worker.start()
        self.refresh_cameras()
        self.after_id = self.root.after(30, self.update_frame)

    def apply_camera_value(self, prop):
        self.set_camera_value(prop, self.camera_controls[prop].value.get())

    def set_camera_value(self, prop, value):
        if not self.camera_on or self.closing:
            return
        control = self.camera_controls[prop]
        if not control.enabled:
            return
        try:
            value = float(value)
            if not math.isfinite(value):
                raise ValueError
        except ValueError:
            self.loading_label.config(text="Enter a finite numeric camera value.")
            return
        if control.info.adjustable:
            value = control.info.normalize(value)
        self.loading_label.config(text="Camera connected.")
        self.worker.commands.put((self.session, "set", (prop, value)))

    def enable_camera_controls(self, enabled):
        self.camera_on = enabled
        for control in self.camera_controls.values():
            control.configure_for_camera(PropertyInfo(), None, enabled)

    def clear_video(self):
        self.invalidate_review()
        self.last_frame = None
        self.reset_fov_crosshair()
        self.reset_view()
        self.display_transform = None
        self.reset_crosshair()
        self.video_label.config(image="", text="No camera image")
        self.video_label.image = None

    def image_position(self, event):
        return (event.x - (self.video_label.winfo_width() - self.video_width) // 2,
                event.y - (self.video_label.winfo_height() - self.video_height) // 2)

    def reset_view(self):
        self.zoom_factor = 1.0
        self.view_center = None
        self.pan_anchor = None
        self.pan_dragged = False
        self.pan_click_token = None
        self.circle_drag = None
        self.resize_hover_anchor = None
        self.video_label.config(cursor="")

    def set_view_center(self, center):
        if self.last_frame is None:
            return
        height, width = self.last_frame.shape[:2]
        clamped = DisplayTransform.for_image((width, height), self.zoom_factor, center=center)
        self.view_center = (clamped.crop_x + clamped.crop_width / 2,
                            clamped.crop_y + clamped.crop_height / 2)

    def zoom_with_scroll(self, event):
        if not event.delta or self.last_frame is None or self.display_transform is None:
            return "break"
        transform = self.display_transform
        if getattr(event, "state", 0) & 0x0004:  # Control: edit the hovered circle, not the viewport.
            point = self.image_position(event) if hasattr(event, "x") else (-1, -1)
            anchor = self.resize_hover_anchor
            if (anchor is not None and anchor[3] == self.session
                    and math.dist(point, anchor[:2]) <= 12 and anchor[2] in self.selections):
                self.select_review_role(anchor[2])
                self.resize_review_circle(1 if event.delta > 0 else -1)
                return "break"
            hit = self.circle_at(point, include_fov=False)
            if hit is not None:
                if hit["kind"] == "candidate":
                    role = next((name for name, value in self.selections.items() if value == hit["edge"].id), None)
                    if role:
                        self.resize_hover_anchor = (*point, role, self.session)
                        self.select_review_role(role)
                        self.resize_review_circle(1 if event.delta > 0 else -1)
                elif hit.get("ring") is not None:
                    hit["ring"].resize(1 if event.delta > 0 else -1)
            return "break"
        self.pan_anchor = None
        self.pan_dragged = False
        self.pan_click_token = None
        self.circle_drag = None
        self.resize_hover_anchor = None
        self.video_label.config(cursor="")
        self.zoom_factor = max(1.0, min(3.0, self.zoom_factor + (0.1 if event.delta > 0 else -0.1)))
        if hasattr(event, "x") and hasattr(event, "y"):
            x, y = self.image_position(event)
        else:
            x, y = transform.width / 2, transform.height / 2
        if not (0 <= x < transform.width and 0 <= y < transform.height):
            x, y = transform.width / 2, transform.height / 2
        anchor = transform.to_original((x, y))
        height, width = self.last_frame.shape[:2]
        crop_width, crop_height = max(1, int(width / self.zoom_factor)), max(1, int(height / self.zoom_factor))
        self.set_view_center((anchor[0] + (0.5 - x / transform.width) * crop_width,
                              anchor[1] + (0.5 - y / transform.height) * crop_height))
        return "break"

    def overlays_shown(self):
        return self.overlays_visible.get() and not self.blink_active

    def begin_blink(self, event=None):
        self.end_pan()
        self.blink_active = True
        return "break"

    def end_blink(self, event=None):
        self.blink_active = False
        return "break"

    def hover_image(self, event):
        if self.pan_anchor is not None:
            return
        if self.resize_hover_anchor is not None and math.dist(self.image_position(event), self.resize_hover_anchor[:2]) > 12:
            self.resize_hover_anchor = None
        if self.picking_role is not None:
            self.video_label.config(cursor="crosshair")
        else:
            self.video_label.config(cursor="fleur" if self.circle_at(self.image_position(event)) else "")

    def fov_crosshair_center(self):
        """Position in full raw-image coordinates, independent of every optical guide."""
        if self.last_frame is None:
            return (0, 0)
        height, width = self.last_frame.shape[:2]
        return tuple(min(size - 1, fraction * size) for fraction, size in zip(self.fov_center_fraction, (width, height)))

    def set_fov_crosshair_center(self, center):
        if self.last_frame is None:
            return
        height, width = self.last_frame.shape[:2]
        self.fov_center_fraction = tuple(max(0.0, min(size - 1, value)) / size
                                        for value, size in zip(center, (width, height)))

    def reset_fov_crosshair(self):
        self.fov_center_fraction = (0.5, 0.5)

    def draw_fov_crosshair(self, frame, transform):
        if not self.fov_crosshair_visible.get() or not self.overlays_shown():
            return
        x, y = (round(value) for value in transform.to_display(self.fov_crosshair_center()))
        height, width = frame.shape[:2]
        # Preserve the startup red crosshair, with a thin contrasting halo.
        segments = []
        if 0 <= x < width:
            segments.append(((x, 0), (x, height - 1)))
        if 0 <= y < height:
            segments.append(((0, y), (width - 1, y)))
        for start, end in segments:
            cv2.line(frame, start, end, (0, 0, 0), 3)
            cv2.line(frame, start, end, (255, 0, 0), 1)

    def circle_at(self, point, include_fov=True):
        """Hit visible rims/centers, including the focuser extrapolation."""
        if self.picking_role is not None or not self.overlays_shown():
            return None
        transform = self.display_transform
        if transform is None or not (0 <= point[0] < transform.width and 0 <= point[1] < transform.height):
            return None
        if include_fov and self.fov_crosshair_visible.get():
            center = self.fov_crosshair_center()
            displayed = transform.to_display(center)
            if (0 <= displayed[0] < transform.width and 0 <= displayed[1] < transform.height
                    and math.dist(point, displayed) <= 12):
                return {"kind": "fov", "center": center,
                        "token": (self.session, self.analysis_generation)}
        if self.detection is not None:
            hits = []
            selected_id = self.selections.get(self.review_role.get())
            for edge in self.detection.candidates:
                if edge.id not in self.selections.values() and not self.show_candidates.get():
                    continue
                center = transform.to_display(edge.center)
                center_distance = math.hypot(point[0] - center[0], point[1] - center[1])
                if edge.axes[0] == edge.axes[1] and not edge.support_bins:
                    # Continuous geometry keeps the grab margin consistent at high zoom.
                    dx, dy = point[0] - center[0], point[1] - center[1]
                    rx = edge.radius * transform.width / transform.crop_width
                    ry = edge.radius * transform.height / transform.crop_height
                    angle = math.atan2(dy / ry, dx / rx)
                    distance = math.hypot(dx - rx * math.cos(angle), dy - ry * math.sin(angle))
                else:
                    points = edge.points(288)
                    if edge.support_bins and edge.id != self.selections.get("Focuser edge"):
                        points = [p for i, p in enumerate(points) if i // 4 in edge.support_bins]
                    distance = min((math.hypot(point[0] - x, point[1] - y)
                                    for x, y in (transform.to_display(p) for p in points)), default=float("inf"))
                if min(center_distance, distance) <= 12:
                    hits.append((min(center_distance, distance), edge.id != selected_id, edge.id, edge))
            if hits:
                edge = min(hits, key=lambda hit: hit[:3])[3]
                return {"kind": "candidate", "edge": edge,
                        "points": tuple(self.manual_points.get(edge.id, ())),
                        "token": (self.session, self.analysis_generation)}
        if self.show_crosshair:
            distance = math.hypot(point[0] - self.crosshair_x, point[1] - self.crosshair_y)
            ring = min((ring for ring in self.ring_controls if ring.visible.get()
                        and abs(distance - ring.slider.get()) <= 12),
                       key=lambda ring: abs(distance - ring.slider.get()), default=None)
            if distance <= 12 or ring is not None:
                return {"kind": "guide", "ring": ring, "center": transform.to_original((self.crosshair_x, self.crosshair_y)),
                        "token": (self.session, self.analysis_generation)}
        return None

    def begin_pan(self, event):
        self.end_pan()
        transform = self.display_transform
        if self.last_frame is not None and transform is not None:
            x, y = self.image_position(event)
            if 0 <= x < transform.width and 0 <= y < transform.height:
                if self.source_mode == "camera" and self.camera_on:
                    self.view_frozen = True
                    self.live_average.reset()
                    self.analysis_generation += 1
                self.pan_anchor = (event.x, event.y, transform)
                if getattr(event, "num", None) == 1:
                    self.pan_click_token = (self.session, self.analysis_generation)
                    self.circle_drag = self.circle_at((x, y))
                    if self.circle_drag is not None and self.circle_drag["kind"] == "candidate":
                        role = next((name for name, candidate_id in self.selections.items()
                                     if candidate_id == self.circle_drag["edge"].id), None)
                        if role is not None:
                            self.select_review_role(role)
        return "break"

    def pan_image(self, event):
        if self.pan_anchor is not None:
            x, y, transform = self.pan_anchor
            if not self.pan_dragged and math.hypot(event.x - x, event.y - y) < 5:
                return "break"
            self.pan_dragged = True
            self.video_label.config(cursor="fleur")
            if self.circle_drag is not None:
                if self.circle_drag["token"] != (self.session, self.analysis_generation):
                    self.end_pan()
                    return "break"
                delta = ((event.x - x) * transform.crop_width / transform.width,
                         (event.y - y) * transform.crop_height / transform.height)
                if self.circle_drag["kind"] == "fov":
                    original = self.circle_drag["center"]
                    self.set_fov_crosshair_center(tuple(original[i] + delta[i] for i in (0, 1)))
                elif self.circle_drag["kind"] == "candidate":
                    self.move_review_candidate(self.circle_drag["edge"], delta, self.circle_drag["points"])
                else:
                    width, height = self.last_frame.shape[1], self.last_frame.shape[0]
                    original = self.circle_drag["center"]
                    center = (max(0, min(width - 1, original[0] + delta[0])),
                              max(0, min(height - 1, original[1] + delta[1])))
                    self.crosshair_x, self.crosshair_y = (round(v) for v in self.display_transform.to_display(center))
                    if self.detection is not None:
                        self.set_review_center(center)
                        self.refresh_review_selection()
                return "break"
            self.set_view_center((transform.crop_x + transform.crop_width / 2 -
                                  (event.x - x) * transform.crop_width / transform.width,
                                  transform.crop_y + transform.crop_height / 2 -
                                  (event.y - y) * transform.crop_height / transform.height))
        return "break"

    def set_fullscreen(self, enabled):
        enabled = bool(enabled)
        if enabled and not self.fullscreen:
            self.windowed_state = self.root.state()
        was_fullscreen = self.fullscreen
        self.fullscreen = enabled
        self.root.attributes("-fullscreen", self.fullscreen)
        if was_fullscreen and not enabled:
            self.root.state(self.windowed_state)
        self.fullscreen_button.config(text="Windowed" if self.fullscreen else "Fullscreen")
        return "break"

    def toggle_fullscreen(self, event=None):
        return self.set_fullscreen(not self.fullscreen)

    def exit_fullscreen(self, event=None):
        if self.fullscreen:
            return self.set_fullscreen(False)

    def end_pan(self, event=None):
        if event is not None and self.pan_anchor is not None:
            self.pan_image(event)
            if (not self.pan_dragged and self.pan_click_token == (self.session, self.analysis_generation)
                    and (self.circle_drag is None or self.circle_drag["kind"] != "fov")):
                self.place_guide_center(event)
        self.pan_anchor = None
        self.pan_dragged = False
        self.pan_click_token = None
        self.circle_drag = None
        self.resize_hover_anchor = None
        self.video_label.config(cursor="")
        if self.source_mode == "camera" and self.camera_on and self.picking_role is None and not self.radius_editing:
            self.view_frozen = False
        return "break"

    def show_guide_help(self):
        messagebox.showinfo(
            "Newtonian collimation · focuser view", NEWTONIAN_HELP,
            parent=self.root,
        )

    def on_guide_visibility_changed(self):
        self.show_crosshair = self.guides_visible.get()

    def toggle_crosshair(self):
        self.guides_visible.set(not self.guides_visible.get())
        self.on_guide_visibility_changed()

    def place_guide_center(self, event):
        if self.last_frame is None or not self.overlays_shown():
            return
        # Tk centers the image within its label; ignore clicks outside it.
        x = event.x - (self.video_label.winfo_width() - self.video_width) // 2
        y = event.y - (self.video_label.winfo_height() - self.video_height) // 2
        if 0 <= x < self.video_width and 0 <= y < self.video_height:
            if self.picking_role is not None:
                self.pick_review_point(self.display_transform.to_original((x, y)))
            elif self.show_crosshair:
                self.crosshair_x, self.crosshair_y = x, y
                if self.detection is not None:
                    self.set_review_center(self.display_transform.to_original((x, y)))
                    self.refresh_review_selection()

    def move_crosshair(self, dx, dy):
        self.crosshair_x = max(0, min(self.video_width - 1, self.crosshair_x + dx))
        self.crosshair_y = max(0, min(self.video_height - 1, self.crosshair_y + dy))
        if self.detection is not None and self.display_transform is not None:
            self.set_review_center(self.display_transform.to_original((self.crosshair_x, self.crosshair_y)))
            self.refresh_review_selection()

    def reset_crosshair(self):
        self.crosshair_x = self.video_width // 2
        self.crosshair_y = self.video_height // 2
        if self.detection is not None and self.display_transform is not None:
            self.set_review_center(self.display_transform.to_original((self.crosshair_x, self.crosshair_y)))
            self.refresh_review_selection()

    def refresh_cameras(self):
        if self.closing:
            return
        self.session += 1
        self.source_mode = "camera"
        self.source_description = "Live camera"
        self.enable_camera_controls(False)
        self.clear_video()
        self.camera_dropdown.config(state="disabled")
        self.refresh_button.config(state="disabled")
        self.loading_label.config(text="Looking for cameras...")
        self.worker.commands.put((self.session, "scan", None))

    def on_camera_selected(self, event):
        if self.closing or self.selected_camera.get() not in self.camera_list:
            return
        self.session += 1
        self.source_mode = "camera"
        self.source_description = self.selected_camera.get()
        self.enable_camera_controls(False)
        self.clear_video()
        self.loading_label.config(text="Loading camera...")
        camera_index = int(self.selected_camera.get().split()[-1])
        self.worker.commands.put((self.session, "open", camera_index))

    def handle_camera_event(self, kind, data):
        if kind == "cameras":
            previous = self.selected_camera.get()
            self.camera_list = [f"Camera {index}" for index in data]
            self.camera_dropdown.config(values=self.camera_list,
                                        state="readonly" if self.camera_list else "disabled")
            self.refresh_button.config(state="normal")
            if self.camera_list:
                self.selected_camera.set(previous if previous in self.camera_list else self.camera_list[0])
                self.on_camera_selected(None)
            else:
                self.selected_camera.set("")
                self.loading_label.config(text="No cameras found. Connect a camera and click Refresh cameras.")
        elif kind == "opened":
            values, capabilities = data
            self.camera_on = True
            for prop, control in self.camera_controls.items():
                control.configure_for_camera(capabilities.get(prop, PropertyInfo()), values.get(prop))
            self.loading_label.config(text="Camera connected.")
        elif kind == "property":
            prop, actual, _message = data
            if actual is not None:
                self.camera_controls[prop].set_reported_value(actual)
        elif kind in ("error", "disconnected"):
            if kind == "disconnected" or not self.camera_on:
                self.enable_camera_controls(False)
                if not self.view_frozen:
                    self.clear_video()
            self.refresh_button.config(state="normal")
            self.loading_label.config(text=data)

    def update_frame(self):
        if self.closing:
            return
        while True:
            try:
                session, kind, data = self.worker.events.get_nowait()
            except Empty:
                break
            if session == self.session:
                self.handle_camera_event(kind, data)
        try:
            session, frame = self.worker.frames.get_nowait()
            if session == self.session and self.camera_on:
                if self.tracking_active:
                    if not self.view_frozen and self.pan_anchor is None and not self.radius_editing and self.picking_role is None:
                        self.live_average.add(frame, monotonic())
                    self.tracking_pending_frame = frame
                elif not self.view_frozen:
                    self.last_frame = frame
                    self.observations_current = False
        except Empty:
            pass
        self.poll_analysis()
        self.maybe_track()

        if self.last_frame is not None:
            available_width = max(160, self.root.winfo_width() - self.sidebar.winfo_width() - 14)
            available_height = max(120, self.root.winfo_height() - 14)
            max_width, max_height = min(960, available_width), min(720, available_height)
            previous_transform = self.display_transform
            self.display_transform = DisplayTransform.for_image(
                (self.last_frame.shape[1], self.last_frame.shape[0]), self.zoom_factor,
                max_width, max_height, self.view_center)
            frame = prepare_frame(self.last_frame, self.zoom_factor, max_width, max_height, self.view_center)
            height, width = frame.shape[:2]
            if previous_transform is not None and previous_transform != self.display_transform:
                original_center = previous_transform.to_original((self.crosshair_x, self.crosshair_y))
                self.crosshair_x, self.crosshair_y = (round(value) for value in
                                                     self.display_transform.to_display(original_center))
                scale = ((self.display_transform.width / self.display_transform.crop_width) /
                         (previous_transform.width / previous_transform.crop_width))
                for ring in self.ring_controls:
                    radius = round(ring.slider.get() * scale)
                    ring.slider.config(to=max(400, math.ceil(400 * self.zoom_factor), radius))
                    ring.slider.set(radius)
            elif previous_transform is None:
                self.crosshair_x = round(self.crosshair_x * width / self.video_width)
                self.crosshair_y = round(self.crosshair_y * height / self.video_height)
            self.video_width, self.video_height = width, height
            if self.detection is not None and self.detection.guide_center is not None:
                self.crosshair_x, self.crosshair_y = (round(v) for v in self.display_transform.to_display(self.detection.guide_center))
            if self.show_crosshair and self.overlays_shown():
                center = (self.crosshair_x, self.crosshair_y)
                for ring in self.ring_controls:
                    if ring.visible.get():
                        cv2.circle(frame, center, ring.slider.get(), ring.color, 1)
            if self.detection is not None and self.overlays_shown():
                draw_detection(frame, self.detection, self.selections, self.confirmed,
                               self.display_transform, self.show_candidates.get(),
                               self.selections.get(self.review_role.get()))
            self.draw_fov_crosshair(frame, self.display_transform)
            for point in self.pick_points if self.overlays_shown() else ():
                center = tuple(round(value) for value in self.display_transform.to_display(point))
                cv2.drawMarker(frame, center, (255, 255, 255), cv2.MARKER_TILTED_CROSS, 10, 1)
            img = ImageTk.PhotoImage(Image.fromarray(frame))
            self.video_label.config(image=img, text="")
            self.video_label.image = img
        self.detect_button.config(state="normal" if self.last_frame is not None and not self.analysis_busy else "disabled")
        self.after_id = self.root.after(30, self.update_frame)

    def on_closing(self):
        self.closing = True
        for control in self.camera_controls.values():
            control.cancel_pending()
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        # The worker releases its own capture after any in-progress driver call.
        self.worker.stop_event.set()
        self.root.destroy()

