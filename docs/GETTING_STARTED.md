# Getting started

Astro Collimator helps you collimate a Newtonian telescope from a view through
the focuser. It runs locally and works without an internet connection.

## Portable Windows application

Extract the entire release ZIP to a writable folder, then open
**AstroCollimator.exe**. Keep the `_internal` folder beside the executable.
You do not need Python or an installer.

Open **Telescope setup / Options** and enter your telescope's dimensions and
primary mirror center-mark shape. Leave dimensions blank when you do not know
them. The application saves your setup in `options.json` beside the executable.

Connect a camera and select it in **Camera**, or open a saved focuser-view image.
See the [user guide](USER_GUIDE.md) for the collimation workflow.

## Run from source

Use Python 3.11 or later with Tk support. Development and release checks use
64-bit Python 3.13 on Windows. From the project folder:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe start.py
```

`start.py` is the source entry point. It also works when launched from a different
working directory. Source installations save setup in the project-root
`options.json`; packaged applications save it beside the executable.

Dependency installation requires internet access or pre-downloaded wheels.
The installed application makes no runtime network requests and uses no cloud
service or downloaded detection model.

## Camera connection

Use a camera that Windows exposes as a video capture device. The application
queries available gain, exposure, zoom and focus controls; the camera driver
determines which are available. A dedicated astronomy camera that requires a
vendor SDK may not appear in the list.

If no camera appears, check the connection, close other applications using it,
and select **Refresh cameras**. You can continue with saved images while checking
the camera connection.
