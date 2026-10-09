"""Run in the caller's Python interpreter and report startup errors."""

import os
from pathlib import Path
import sys
import tempfile
import traceback


def startup_error(error, gui, project):
    message = "Astro Collimator could not start."
    if isinstance(error, ImportError):
        message += "\n\nInstall the application dependencies in the Python interpreter that launched this file. See docs/GETTING_STARTED.md."
    message += "\n\n" + str(error) + "\n\nInterpreter: " + sys.executable
    detail = "Interpreter: " + sys.executable + "\nPython: " + sys.version + "\n\n" + traceback.format_exc()
    destinations = [project / "build" / "startup-error.log",
                    Path(tempfile.gettempdir()) / "AstroCollimator-startup-error.log"]
    for path in destinations:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(detail.encode("utf-8"))
            message += "\n\nDetails: " + str(path)
            break
        except OSError:
            continue
    if sys.stderr is not None:
        print(message, file=sys.stderr)
    if gui and sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "Astro Collimator", 0x10)


def hide_launch_console():
    """Hide an app-only Windows console; preserve consoles shared with a shell."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes as ct
        kernel = ct.WinDLL("kernel32", use_last_error=True)
        user = ct.WinDLL("user32", use_last_error=True)
        kernel.GetConsoleWindow.argtypes = ()
        kernel.GetConsoleWindow.restype = ct.c_void_p
        kernel.GetConsoleProcessList.argtypes = (ct.POINTER(ct.c_uint32), ct.c_uint32)
        kernel.GetConsoleProcessList.restype = ct.c_uint32
        kernel.OpenProcess.argtypes = (ct.c_uint32, ct.c_int, ct.c_uint32)
        kernel.OpenProcess.restype = ct.c_void_p
        kernel.QueryFullProcessImageNameW.argtypes = (ct.c_void_p, ct.c_uint32, ct.c_wchar_p, ct.POINTER(ct.c_uint32))
        kernel.QueryFullProcessImageNameW.restype = ct.c_int
        kernel.CloseHandle.argtypes = (ct.c_void_p,)
        user.ShowWindow.argtypes = (ct.c_void_p, ct.c_int)
        user.ShowWindow.restype = ct.c_int
        window = kernel.GetConsoleWindow()
        if not window:
            return False
        processes = (ct.c_uint32 * 32)()
        count = kernel.GetConsoleProcessList(processes, len(processes))
        if not 0 < count <= len(processes) or os.getpid() not in processes[:count]:
            return False
        for pid in processes[:count]:
            if pid == os.getpid():
                continue
            handle = kernel.OpenProcess(0x1000, False, pid)
            if not handle:
                return False
            try:
                name = ct.create_unicode_buffer(32768)
                length = ct.c_uint32(len(name))
                if not kernel.QueryFullProcessImageNameW(handle, 0, name, ct.byref(length)):
                    return False
                if Path(name.value).name.lower() != "py.exe":
                    return False
            finally:
                kernel.CloseHandle(handle)
        user.ShowWindow(window, 0)  # SW_HIDE, in the original Python process.
        return True
    except (OSError, AttributeError):
        return False


def launch(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    gui = not arguments
    project = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
               else Path(__file__).resolve().parents[1])
    try:
        if gui or "--smoke-test" in arguments:
            hide_launch_console()
        if sys.version_info < (3, 11):
            raise RuntimeError("Python 3.11 or later with Tk support is required.")
        from .launcher import main
        return main(arguments)
    except Exception as error:
        startup_error(error, gui, project)
        return 1
