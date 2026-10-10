"""Shared source and packaged entry point."""

import argparse
from pathlib import Path

from . import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(description="Advanced Astro Collimator — Newtonian collimation assistance.")
    parser.add_argument("--version", action="version", version=f"Advanced Astro Collimator {__version__}")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--report", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    from .dependencies import check_runtime_dependencies
    check_runtime_dependencies()

    if args.smoke_test:
        from .diagnostics import smoke_test
        return smoke_test(args.report)

    import tkinter as tk
    from .app import WebcamApp

    root = tk.Tk()
    app = WebcamApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
    return 0
