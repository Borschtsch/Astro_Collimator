# Getting started

Astro Collimator helps you collimate a Newtonian telescope from a view through
the focuser. It runs locally on Windows and Linux, without an internet connection.

## Portable applications

Extract the entire release archive to a writable folder. Keep `_internal` beside
the executable. Python is included; no Python installation is required.

- **Windows:** extract the Windows ZIP and open **AstroCollimator.exe**.
- **Linux:** extract the Linux `.tar.gz` for your architecture, then run
  `./AstroCollimator` inside the extracted folder from your desktop session.
  A Linux desktop with X11 or XWayland is required. Linux system libraries still
  need to be installed; see below. Builds are specific to their Linux baseline
  and architecture, recorded in `build-info.json`.

Open **Telescope setup / Options** and enter your telescope's dimensions and
primary mirror center-mark shape. Leave dimensions blank when you do not know
them. Setup is saved in `options.json` beside the executable.

Connect a camera and select it in **Camera**, or open a saved focuser-view image.
See the [user guide](USER_GUIDE.md) for the collimation workflow.

## Run from source

Use Python 3.11 or later (latest patch version) with Tk support.

### Windows

From the project folder:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe start.py
```

For double-click startup, install the dependencies in the Python interpreter
associated with `.py` files, then double-click **start.py** in Explorer. The app
runs directly in that interpreter; it does not switch Python installations or
start another process. No CMD file is required. A local `.venv` is used only when
you explicitly run its Python executable, as in the commands above.
On Windows, an app-only console is hidden during startup; a console shared
with your terminal stays visible. Windows may briefly show its console before
Python reaches the launcher.
Startup failures display the interpreter location and log path. The UTF-8 log
includes the interpreter location, Python version and traceback.
Dependencies are never installed automatically.

### Linux

On Ubuntu 24.04 or later, install the desktop dependencies first:

```bash
sudo apt install python3-venv python3-tk libgl1 libglib2.0-0t64
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python start.py
```

On Debian 12, use `libglib2.0-0` in place of `libglib2.0-0t64`.
Other distributions use equivalent Python/Tk, OpenGL and GLib packages. Use a
normal desktop session; Tk uses XWayland on Wayland desktops. The portable Linux
application also requires the system graphics libraries and a desktop display.
If the executable loses its permissions while being copied, restore them with
`chmod +x AstroCollimator`. Extract the original tar archive to preserve its
permissions and internal symbolic links.

`start.py` is the single source entry point and works from another working
directory. Source installations save setup in the project-root `options.json`;
portable applications save it beside the executable. Use a writable user folder.

Dependency installation requires internet access or pre-downloaded packages.
The installed application makes no runtime network requests and uses no cloud
service or downloaded detection model.

## Camera connection

Use a camera exposed as a video capture device by the operating system:
DirectShow on Windows, V4L2 (`/dev/video*`) on Linux. The driver determines which
gain, exposure, zoom and focus controls are available. Linux exposure uses the
driver's native units of 100 microseconds; Windows drivers may use different units.
Controls locked by automatic mode are unavailable for manual adjustment. Native
range queries do not change camera values or disable automatic modes.
A dedicated astronomy camera that requires a vendor SDK may not appear.

If no camera appears, check the connection, close other applications using it,
and select **Refresh cameras**. On Linux, check that your desktop user has access
to the video device. In a VM, pass the USB camera through to the Linux guest;
SSH access alone does not make the host camera available there.
You can continue with saved images while checking the camera connection.

Linux native validation and release status are recorded in
[platform support](PLATFORM_SUPPORT.md).
