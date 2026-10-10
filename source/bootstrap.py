"""Run in the caller's Python interpreter and report startup errors."""

import os
from pathlib import Path
import sys
import tempfile
import traceback


def ensure_windows_environment():
    """Repair missing Windows paths in this process before native shell/GUI calls."""
    if sys.platform != "win32":
        return
    import ctypes as ct
    import ntpath

    kernel = ct.WinDLL("kernel32", use_last_error=True)
    kernel.GetWindowsDirectoryW.argtypes = (ct.c_wchar_p, ct.c_uint)
    kernel.GetWindowsDirectoryW.restype = ct.c_uint
    buffer = ct.create_unicode_buffer(32768)
    length = kernel.GetWindowsDirectoryW(buffer, len(buffer))
    if not 0 < length < len(buffer):
        raise OSError("Could not resolve the Windows directory.")
    windows = buffer.value
    drive = ntpath.splitdrive(windows)[0]
    current_drive = os.environ.get("SystemDrive", "")
    if len(current_drive) != 2 or current_drive[1:] != ":" or not current_drive[0].isalpha():
        os.environ["SystemDrive"] = drive

    def preserve_or_set(name, value):
        current = os.environ.get(name, "")
        if not current or "%" in current or not ntpath.isabs(current):
            os.environ[name] = value

    preserve_or_set("SystemRoot", windows)
    preserve_or_set("WINDIR", windows)
    # Resolve the actual common app-data location, including relocated systems.
    shell = ct.WinDLL("shell32")
    shell.SHGetFolderPathW.argtypes = (ct.c_void_p, ct.c_int, ct.c_void_p, ct.c_uint, ct.c_wchar_p)
    shell.SHGetFolderPathW.restype = ct.c_long
    if shell.SHGetFolderPathW(None, 0x23, None, 0, buffer) != 0:  # CSIDL_COMMON_APPDATA
        raise OSError("Could not resolve the Windows shared application-data directory.")
    preserve_or_set("ProgramData", buffer.value)
    preserve_or_set("ALLUSERSPROFILE", buffer.value)


def startup_error(error, gui, project):
    message = "Advanced Astro Collimator could not start."
    if isinstance(error, ImportError):
        message += "\n\nInstall the application dependencies in the Python interpreter that launched this file. See docs/GETTING_STARTED.md."
    message += "\n\n" + str(error) + "\n\nInterpreter: " + sys.executable
    detail = "Interpreter: " + sys.executable + "\nPython: " + sys.version + "\n\n" + traceback.format_exc()
    destinations = [project / "build" / "startup-error.log",
                    Path(tempfile.gettempdir()) / "AdvancedAstroCollimator-startup-error.log"]
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
        ctypes.windll.user32.MessageBoxW(None, message, "Advanced Astro Collimator", 0x10)
    elif gui:
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            try:
                messagebox.showerror("Advanced Astro Collimator", message, parent=root)
            finally:
                root.destroy()
        except Exception:
            pass  # A missing Tk/display still has stderr and the UTF-8 log.


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
        ensure_windows_environment()
        if gui or "--smoke-test" in arguments:
            hide_launch_console()
        if sys.version_info < (3, 11):
            raise RuntimeError("Python 3.11 or later with Tk support is required.")
        from .launcher import main
        return main(arguments)
    except Exception as error:
        startup_error(error, gui, project)
        return 1
