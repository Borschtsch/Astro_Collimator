"""Build and verify an offline portable Windows release from the current source."""

import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))


def check_launch(executable, arguments, report, settings_directory):
    subprocess.run([str(executable), *arguments, "--smoke-test", "--report", str(report)],
                   cwd=PROJECT / "build", check=True, timeout=60)
    result = json.loads(report.read_text(encoding="utf-8"))
    if result["status"] != "passed" or Path(result["settings_path"]) != settings_directory / "options.json":
        raise RuntimeError(f"Application check failed: {result}")


def copy_notices(destination):
    destination.mkdir(parents=True, exist_ok=True)
    for package in ("opencv-python", "Pillow", "numpy"):
        distribution = importlib.metadata.distribution(package)
        for file in distribution.files or ():
            if any(word in file.name.lower() for word in ("license", "copying", "notice")):
                source = distribution.locate_file(file)
                if source.is_file():
                    target = destination / package / Path(str(file))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
    python_root = Path(sys.base_prefix)
    for source in [python_root / "LICENSE.txt", *python_root.glob("tcl/**/license.terms")]:
        if source.is_file():
            target = destination / "Python-Tcl-Tk" / source.relative_to(python_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


def check_archive(archive, work):
    """Verify extraction, relocation and launch without the build environment on PATH."""
    import os
    with tempfile.TemporaryDirectory(prefix="Release check é ", dir=work) as folder:
        extracted = Path(folder)
        with zipfile.ZipFile(archive) as packaged:
            packaged.extractall(extracted)
        bundle = extracted / "AstroCollimator"
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        environment["PATH"] = str(Path(environment.get("SystemRoot", "C:/Windows")) / "System32")
        report = work / "archive-check.json"
        subprocess.run([str(bundle / "AstroCollimator.exe"), "--smoke-test", "--report", str(report)],
                       cwd=extracted, env=environment, check=True, timeout=60)
        result = json.loads(report.read_text(encoding="utf-8"))
        if result["status"] != "passed" or Path(result["settings_path"]) != bundle / "options.json":
            raise RuntimeError(f"Extracted release check failed: {result}")


def main():
    if sys.platform != "win32" or sys.maxsize <= 2**32:
        raise SystemExit("Build the Windows x64 release with 64-bit Python on Windows.")
    try:
        from PyInstaller.__main__ import run
    except ImportError:
        raise SystemExit("Install requirements-build.txt in the build environment first.")
    from source import __version__
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable,
        VarFileInfo, VarStruct, VSVersionInfo,
    )

    work = PROJECT / "build"
    work.mkdir(exist_ok=True)
    release_root = PROJECT / "dist"
    bundle = release_root / "AstroCollimator"
    if bundle.exists():
        # Never overwrite a user's portable settings/captures on a repeat build.
        raise SystemExit(f"Release folder already exists: {bundle}. Move it aside before rebuilding.")
    check_launch(Path(sys.executable), [str(PROJECT / "start.py")], work / "source-check.json", PROJECT)
    version = tuple(int(part) for part in __version__.split(".")) + (0,)
    resource = VSVersionInfo(ffi=FixedFileInfo(filevers=version, prodvers=version, fileType=1), kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("ProductName", "Astro Collimator"),
            StringStruct("FileDescription", "Newtonian telescope collimation assistant"),
            StringStruct("FileVersion", __version__), StringStruct("ProductVersion", __version__),
            StringStruct("OriginalFilename", "AstroCollimator.exe"),
        ])]), VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ])
    version_file = work / "windows-version.txt"
    version_file.write_bytes(str(resource).encode("utf-8"))
    run([str(PROJECT / "start.py"), "--name", "AstroCollimator", "--onedir", "--windowed",
         "--noupx", "--noconfirm", "--distpath", str(release_root), "--workpath", str(work / "pyinstaller"),
         "--specpath", str(work), "--version-file", str(version_file),
         "--exclude-module", "tests", "--exclude-module", "pytest"])
    docs = bundle / "docs"
    docs.mkdir()
    for name in ("GETTING_STARTED.md", "USER_GUIDE.md"):
        shutil.copyfile(PROJECT / "docs" / name, docs / name)
    copy_notices(bundle / "third-party-notices")
    (bundle / "START_HERE.txt").write_bytes(
        b"Astro Collimator\nNewtonian collimation assistance\n\n"
        b"1. Extract this entire folder to a writable location.\n"
        b"2. Open AstroCollimator.exe. Python is not required.\n"
        b"3. Set up your telescope, then select a camera or open a focuser-view image.\n\n"
        b"Keep _internal beside the executable. The application works offline.\n"
        b"Your telescope setup is saved in options.json beside the executable.\n"
        b"See docs/USER_GUIDE.md for collimation workflow and controls.\n")
    versions = {name: importlib.metadata.version(name)
                for name in ("pyinstaller", "opencv-python", "Pillow", "numpy")}
    (bundle / "build-info.json").write_bytes((json.dumps({"app_version": __version__,
        "python": sys.version.split()[0], "platform": sys.platform, "dependencies": versions}, indent=2) + "\n").encode("utf-8"))
    check_launch(bundle / "AstroCollimator.exe", [], work / "portable-check.json", bundle)
    if (bundle / "options.json").exists():
        raise RuntimeError("A personal settings file must not be included in the release.")
    archive = release_root / f"AstroCollimator-{__version__}-windows-x64.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                output.write(path, path.relative_to(release_root))
    check_archive(archive, work)
    print(f"Verified portable release: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
