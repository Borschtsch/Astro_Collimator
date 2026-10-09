"""Isolated real source launcher with an offline-created virtual environment."""

from contextlib import contextmanager
from pathlib import Path
import shutil
import site
import sys
import tempfile
import time
import venv


def source_checkout(directory, dependencies=True):
    project = Path(__file__).resolve().parents[2]
    checkout = Path(directory).resolve() / "Source launch é"
    checkout.mkdir()
    for name in ("start.py",):
        shutil.copyfile(project / name, checkout / name)
    shutil.copytree(project / "source", checkout / "source", ignore=shutil.ignore_patterns("__pycache__"))
    environment = checkout / ".venv"
    venv.EnvBuilder(with_pip=False, system_site_packages=False).create(environment)
    if dependencies:
        # Reuse real installed dependencies offline, including when the test
        # runner itself is inside a Linux venv rather than global Python.
        packages = (environment / "Lib" / "site-packages" if sys.platform == "win32"
                    else environment / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages")
        packages.mkdir(parents=True, exist_ok=True)
        paths = [str(Path(path).resolve()) for path in site.getsitepackages()]
        (packages / "integration-dependencies.pth").write_bytes(
            ("import sys; sys.path.extend(" + ascii(paths) + ")\n").encode("ascii"))
    executable = checkout / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    return checkout, executable


@contextmanager
def launch_directory():
    directory = tempfile.TemporaryDirectory()
    target = Path(directory.name).resolve()
    assert target.parent == Path(tempfile.gettempdir()).resolve()
    try:
        yield directory.name
    finally:
        # Windows venv redirectors can outlive the child that wrote its report
        # briefly. Retry cleanup without terminating any process.
        deadline = time.monotonic() + 10
        while True:
            try:
                directory.cleanup()
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.05)
