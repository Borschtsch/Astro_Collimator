"""Record native Linux desktop integration and optional portable-release checks."""

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


PROJECT = Path(__file__).resolve().parents[1]


def main():
    if not sys.platform.startswith("linux"):
        raise SystemExit("Run this validation inside the Linux VM.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="Also build and verify the native portable release.")
    args = parser.parse_args()
    work = PROJECT / "build" / "linux-validation"
    work.mkdir(parents=True, exist_ok=True)
    result = {"status": "failed", "platform": platform.platform(),
              "python": sys.version, "libc": platform.libc_ver(),
              "display": os.environ.get("DISPLAY"), "checks": [],
              "physical_camera_checked": False}
    try:
        if not result["display"]:
            raise RuntimeError("Run in the VM desktop terminal, or connect SSH to that user's X11/XWayland display (DISPLAY and XAUTHORITY).")
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        result["tk"] = root.tk.call("info", "patchlevel")
        result["windowing_system"] = root.tk.call("tk", "windowingsystem")
        root.destroy()
        result["dependencies"] = {name: importlib.metadata.version(name)
                                  for name in ("opencv-python", "Pillow", "numpy")}
        commands = [
            ("integration", ["-B", str(PROJECT / "scripts/test_integration.py")]),
            ("source", ["-B", str(PROJECT / "start.py"), "--smoke-test", "--report", str(work / "source-check.json")]),
        ]
        if args.build:
            commands.append(("portable", ["-B", str(PROJECT / "scripts/build_linux.py")]))
        for name, arguments in commands:
            log = work / f"{name}.log"
            print(f"Checking {name}; log: {log}", flush=True)
            with log.open("w", encoding="utf-8") as stream:
                completed = subprocess.run([sys.executable, *arguments], cwd=work,
                                           stdout=stream, stderr=subprocess.STDOUT, timeout=900)
            result["checks"].append({"name": name, "exit_code": completed.returncode, "log": str(log)})
            if completed.returncode:
                raise RuntimeError(f"{name} failed; see {log}")
        result["status"] = "passed"
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    report = work / "results.json"
    report.write_bytes((json.dumps(result, indent=2) + "\n").encode("utf-8"))
    print(f"Linux validation {result['status']}: {report}")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
