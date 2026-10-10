"""Build and verify an offline portable release on its native operating system."""

import argparse
import importlib.metadata
import platform
import os
import tarfile
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from source.bootstrap import ensure_windows_environment

ensure_windows_environment()


def check_launch(executable, arguments, report, settings_directory):
    subprocess.run([str(executable), *arguments, "--smoke-test", "--report", str(report)],
                   cwd=PROJECT / "build", check=True, timeout=60)
    result = json.loads(report.read_text(encoding="utf-8"))
    if result["status"] != "passed" or Path(result["settings_path"]) != settings_directory / "options.json":
        raise RuntimeError(f"Application check failed: {result}")


def copy_notices(destination):
    destination.mkdir(parents=True, exist_ok=True)
    for package in ("opencv-python", "Pillow", "numpy", "pyinstaller", "qrcode", "cryptography", "pillow-heif", "cffi", "pycparser"):
        distribution = importlib.metadata.distribution(package)
        for file in distribution.files or ():
            if any(word in file.name.lower() for word in ("license", "copying", "notice")):
                source = distribution.locate_file(file)
                if source.is_file():
                    relative = Path(str(file))
                    if relative.is_absolute() or ".." in relative.parts:
                        continue
                    target = destination / package / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
    python_root = Path(sys.base_prefix)
    for source in [python_root / "LICENSE.txt", *python_root.glob("tcl/**/license.terms")]:
        if source.is_file():
            target = destination / "Python-Tcl-Tk" / source.relative_to(python_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

    if sys.platform.startswith("linux"):
        import tkinter as tk
        import sysconfig
        licenses = [Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"]
        tcl_library = Path(tk.Tcl().eval("info library"))
        licenses.extend(tcl_library.parent.glob("*/license.terms"))
        licenses.extend(tcl_library.parent.glob("*/license.txt"))
        # Debian/Ubuntu system Python and Tcl/Tk keep notices in these locations.
        for pattern in ("python3*/copyright", "libtcl*/copyright", "libtk*/copyright", "tcl*/copyright", "tk*/copyright"):
            licenses.extend(Path("/usr/share/doc").glob(pattern))
        for number, source in enumerate(licenses):
            if source.is_file():
                target = destination / "Python-Tcl-Tk" / f"{number}-{source.parent.name}-{source.name}"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        (destination / "Python-COPYRIGHT.txt").write_bytes(sys.copyright.encode("utf-8"))


def check_archive(archive, work):
    """Verify extraction, relocation and launch without the build environment on PATH."""
    with tempfile.TemporaryDirectory(prefix="Release check é ", dir=work) as folder:
        extracted = Path(folder)
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as packaged:
                packaged.extractall(extracted)
        else:
            with tarfile.open(archive, "r:gz") as packaged:
                packaged.extractall(extracted, filter="data")
        bundle = extracted / "AdvancedAstroCollimator"
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        environment["PATH"] = (str(Path(environment.get("SystemRoot", "C:/Windows")) / "System32")
                               if sys.platform == "win32" else "/usr/bin:/bin")
        report = work / "archive-check.json"
        subprocess.run([str(bundle / executable_name()), "--smoke-test", "--report", str(report)],
                       cwd=extracted, env=environment, check=True, timeout=60)
        result = json.loads(report.read_text(encoding="utf-8"))
        if result["status"] != "passed" or Path(result["settings_path"]) != bundle / "options.json":
            raise RuntimeError(f"Extracted release check failed: {result}")


def executable_name():
    return "AdvancedAstroCollimator.exe" if sys.platform == "win32" else "AdvancedAstroCollimator"


def release_target():
    if sys.platform != "win32" and not sys.platform.startswith("linux"):
        raise SystemExit("Portable releases support Windows and Linux.")
    architecture = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine().lower())
    if sys.maxsize <= 2**32 or architecture is None or (sys.platform == "win32" and architecture != "x64"):
        raise SystemExit("Build with native 64-bit Python: Windows x64 or Linux x64/arm64.")
    return f"{'windows' if sys.platform == 'win32' else 'linux'}-{architecture}"


def windows_version_file(work, version_string):
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable,
        VarFileInfo, VarStruct, VSVersionInfo,
    )
    version = tuple(int(part) for part in version_string.split(".")) + (0,)
    resource = VSVersionInfo(ffi=FixedFileInfo(filevers=version, prodvers=version, fileType=1), kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("ProductName", "Advanced Astro Collimator"),
            StringStruct("FileDescription", "Newtonian telescope collimation assistant"),
            StringStruct("FileVersion", version_string), StringStruct("ProductVersion", version_string),
            StringStruct("OriginalFilename", "AdvancedAstroCollimator.exe"),
        ])]), VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ])
    path = work / "windows-version.txt"
    path.write_bytes(str(resource).encode("utf-8"))
    return path


def main(argv=None):
    target = release_target()
    parser = argparse.ArgumentParser(description="Build and verify a native Advanced Astro Collimator release.")
    parser.add_argument("--output-dir", type=Path, default=PROJECT / "dist" / target,
                        help="Release directory (existing application folders are never overwritten).")
    args = parser.parse_args(argv)
    try:
        from PyInstaller.__main__ import run
    except ImportError:
        raise SystemExit("Install requirements-build.txt in the build environment first.")
    from source import __version__
    work = PROJECT / "build" / target
    work.mkdir(parents=True, exist_ok=True)
    release_root = args.output_dir.resolve()
    bundle = release_root / "AdvancedAstroCollimator"
    if bundle.exists():
        # Never overwrite a user's portable settings/captures on a repeat build.
        raise SystemExit(f"Release folder already exists: {bundle}. Move it aside before rebuilding.")
    check_launch(Path(sys.executable), [str(PROJECT / "start.py")], work / "source-check.json", PROJECT)
    arguments = [str(PROJECT / "start.py"), "--name", "AdvancedAstroCollimator", "--onedir",
                 "--noupx", "--noconfirm", "--distpath", str(release_root),
                 "--workpath", str(work / "pyinstaller"), "--specpath", str(work),
                 "--exclude-module", "tests", "--exclude-module", "pytest",
                 "--add-data", f"{PROJECT / 'source' / 'web'}:source/web",
                 "--collect-all", "pillow_heif"]
    if sys.platform == "win32":
        arguments += ["--windowed", "--version-file", str(windows_version_file(work, __version__))]
    run(arguments)
    docs = bundle / "docs"
    docs.mkdir()
    for name in ("GETTING_STARTED.md", "USER_GUIDE.md", "PLATFORM_SUPPORT.md", "PHONE_CAPTURE.md"):
        shutil.copyfile(PROJECT / "docs" / name, docs / name)
    copy_notices(bundle / "third-party-notices")
    launch = "Open AdvancedAstroCollimator.exe." if sys.platform == "win32" else "Run ./AdvancedAstroCollimator from a desktop session."
    (bundle / "START_HERE.txt").write_bytes((
        "Advanced Astro Collimator\nNewtonian collimation assistance\n\n"
        "1. Extract this entire folder to a writable location.\n"
        f"2. {launch} Python is not required.\n"
        "3. Set up your telescope, then select a camera or open a focuser-view image.\n\n"
        "Keep _internal beside the executable. The application works offline.\n"
        "Your telescope setup is saved in options.json beside the executable.\n"
        "See docs/GETTING_STARTED.md for OS dependencies and docs/USER_GUIDE.md for controls.\n"
    ).encode("utf-8"))
    versions = {name: importlib.metadata.version(name)
                for name in ("pyinstaller", "opencv-python", "Pillow", "numpy", "qrcode", "cryptography", "pillow-heif")}
    (bundle / "build-info.json").write_bytes((json.dumps({"app_version": __version__,
        "python": sys.version.split()[0], "platform": sys.platform, "target": target,
        "build_host": platform.platform(), "libc": platform.libc_ver(), "dependencies": versions}, indent=2) + "\n").encode("utf-8"))
    check_launch(bundle / executable_name(), [], work / "portable-check.json", bundle)
    if (bundle / "phone-link").exists():
        raise RuntimeError("Local phone certificates and private keys must not be included in the release.")
    if (bundle / "options.json").exists():
        raise RuntimeError("A personal settings file must not be included in the release.")
    extension = ".zip" if sys.platform == "win32" else ".tar.gz"
    archive = release_root / f"AdvancedAstroCollimator-{__version__}-{target}{extension}"
    if sys.platform == "win32":
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    output.write(path, path.relative_to(release_root))
    else:
        # Linux PyInstaller uses symlinks; tar preserves these and executable bits.
        with tarfile.open(archive, "w:gz") as output:
            output.add(bundle, arcname=bundle.name)
    check_archive(archive, work)
    print(f"Verified portable release: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
