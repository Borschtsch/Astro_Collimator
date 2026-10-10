"""Fail startup before opening a partially working application."""

from io import BytesIO
from pathlib import Path
import tempfile


class DependencyError(ImportError):
    """All missing or unusable runtime components, collected in one report."""


def check_runtime_dependencies():
    """Exercise required native libraries as well as their Python imports.

    No network connection, permanent certificate, camera or installation is
    needed. Each check runs even if another component failed.
    """
    failures = []

    def check(name, operation):
        try:
            operation()
        except Exception as error:
            failures.append(f"{name}: {type(error).__name__}: {error}")

    def numpy_check():
        import numpy as np
        if np.zeros((3, 3), np.uint8).sum() != 0:
            raise RuntimeError("Array operations failed.")

    def opencv_check():
        import cv2
        import numpy as np
        pixels = np.zeros((32, 32, 3), np.uint8)
        for extension in (".png", ".jpg"):
            ok, data = cv2.imencode(extension, pixels)
            if not ok or cv2.imdecode(data, cv2.IMREAD_COLOR).shape != pixels.shape:
                raise RuntimeError(f"{extension} image encoding/decoding failed.")

    def pillow_check():
        from PIL import Image, ImageOps
        for format in ("PNG", "JPEG"):
            data = BytesIO()
            Image.new("RGB", (32, 32)).save(data, format=format)
            data.seek(0)
            with Image.open(data) as image:
                if ImageOps.exif_transpose(image).size != (32, 32):
                    raise RuntimeError(f"{format} image decoding failed.")

    def qr_check():
        import qrcode
        qr = qrcode.QRCode(box_size=2, border=4)
        qr.add_data("Advanced Astro Collimator startup check")
        qr.make(fit=True)
        image = qr.make_image().get_image()
        image.load()
        if image.width < 32:
            raise RuntimeError("QR image generation failed.")

    def tls_check():
        # Real production certificate generation and OpenSSL chain loading.
        # Temporary keys are deleted; the user's phone identity is untouched.
        from .phone_tls import local_identity
        with tempfile.TemporaryDirectory(prefix="astro-dependency-check-") as folder:
            context, identity = local_identity(Path(folder), ["127.0.0.1"])
            if not context or not identity["server_sha256"]:
                raise RuntimeError("Local HTTPS certificate setup failed.")

    def heif_check():
        import pillow_heif
        from PIL import Image
        data = BytesIO()
        pillow_heif.from_pillow(Image.new("RGB", (32, 32))).save(data)
        decoded = pillow_heif.read_heif(data.getvalue())
        if decoded.size != (32, 32) or not decoded.data:
            raise RuntimeError("HEIF image encoding/decoding failed.")

    def tk_check():
        import tkinter as tk
        from PIL import Image, ImageTk
        root = tk.Tk()
        try:
            root.withdraw()
            photo = ImageTk.PhotoImage(Image.new("RGB", (2, 2)), master=root)
            if ImageTk.getimage(photo).size != (2, 2):
                raise RuntimeError("Tk image display failed.")
        finally:
            root.destroy()

    for name, operation in (("numpy", numpy_check), ("opencv-python", opencv_check),
                            ("Pillow", pillow_check), ("qrcode", qr_check),
                            ("cryptography / HTTPS", tls_check), ("pillow-heif", heif_check),
                            ("Python/Tk / Pillow ImageTk", tk_check)):
        check(name, operation)
    # Phone pages must also exist in source and portable distributions.
    for name in ("phone.html", "phone.js"):
        check(f"Phone page {name}", lambda name=name:
              (Path(__file__).parent / "web" / name).read_text(encoding="utf-8"))
    if failures:
        raise DependencyError("Required runtime checks failed:\n\n" + "\n".join(failures))
