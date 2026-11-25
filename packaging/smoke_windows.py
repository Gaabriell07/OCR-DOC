"""Install and exercise the Windows package without Python/Tesseract on PATH."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request


def check_installer(installer: Path) -> None:
    if sys.platform != "win32":
        raise RuntimeError("Esta comprobación requiere Windows.")
    with tempfile.TemporaryDirectory(prefix="OCR DOC install test ") as directory:
        root = Path(directory)
        target = root / "Installed OCR DOC"
        subprocess.run([str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                        "/CURRENTUSER", f"/DIR={target}", f"/LOG={root / 'install.log'}"],
                       check=True, timeout=180)
        executable = target / "OCR-DOC.exe"
        if not executable.is_file():
            raise RuntimeError("El instalador no creó OCR-DOC.exe.")
        environment = os.environ.copy()
        environment["PATH"] = os.pathsep.join([
            str(Path(environment["SystemRoot"]) / "System32"), environment["SystemRoot"]])
        # Deliberately wrong inherited settings must not override bundled resources.
        environment["TESSERACT_CMD"] = str(root / "nonexistent.exe")
        environment["TESSDATA_PREFIX"] = str(root / "nonexistent-tessdata")
        try:
            subprocess.run([str(executable), "--self-test", str(root / "self-test")],
                           check=True, timeout=180, env=environment, cwd=root,
                           stdin=subprocess.DEVNULL)
            result = json.loads((root / "self-test" / "resultado.json").read_text())
            if not result.get("ok") or not result.get("frozen"):
                raise RuntimeError("La prueba no ejecutó un paquete autónomo.")
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            with (root / "server.log").open("w", encoding="utf-8") as log:
                process = subprocess.Popen([str(executable), "--no-browser", "--port", str(port)],
                                           cwd=root, env=environment, stdout=log,
                                           stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
                try:
                    deadline = time.monotonic() + 90
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            raise RuntimeError("El servidor empaquetado terminó antes de abrirse.")
                        try:
                            base = f"http://127.0.0.1:{port}"
                            with urllib.request.urlopen(base + "/_stcore/health", timeout=2) as response:
                                if response.status == 200:
                                    with urllib.request.urlopen(base, timeout=2) as page:
                                        if b"<html" not in page.read().lower():
                                            raise RuntimeError("No se sirvió la interfaz HTML.")
                                    print("Instalación, OCR, Word y servidor local comprobados.")
                                    return
                        except OSError:
                            time.sleep(.5)
                    raise RuntimeError("El servidor empaquetado no respondió en 90 segundos.")
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=10)
        except Exception:
            for name in ("install.log", "server.log"):
                path = root / name
                if path.exists():
                    print(path.read_text(encoding="utf-8", errors="replace")[-12000:])
            raise
        finally:
            # Do not leave an uninstall registration or shortcuts on the build host.
            uninstall = target / "unins000.exe"
            if uninstall.exists():
                subprocess.run([str(uninstall), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                               check=True, timeout=120)


if __name__ == "__main__":
    check_installer(Path(sys.argv[1]).resolve())
