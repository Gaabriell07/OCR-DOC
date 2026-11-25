"""Entry point frozen by PyInstaller on Windows; no external Python required."""
from __future__ import annotations

import argparse
import contextlib
import os
from pathlib import Path
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

NONINTERACTIVE = "--self-test" in sys.argv or "--no-browser" in sys.argv


def resource_directory() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def configure_runtime() -> Path:
    root = resource_directory()
    if getattr(sys, "frozen", False):
        os.environ["TESSERACT_CMD"] = str(root / "tesseract" / "tesseract.exe")
        os.environ["TESSDATA_PREFIX"] = str(root / "tesseract" / "tessdata")
    os.environ["OMP_THREAD_LIMIT"] = "1"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    return root


def available_port(first: int = 8517) -> int:
    for port in range(first, min(first + 30, 65536)):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No hay un puerto local disponible. Cierra otras instancias de OCR DOC.")


def open_when_ready(port: int) -> None:
    url = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            with urllib.request.urlopen(url + "/_stcore/health", timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except OSError:
            time.sleep(.5)
    print(f"Si el navegador no se abre, entra en {url}", flush=True)


@contextlib.contextmanager
def single_instance():
    """Keep repeated desktop clicks from starting more OCR servers on Windows."""
    if sys.platform != "win32":
        yield True
        return
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    # Installation path distinguishes separate installations without a global lock.
    import hashlib
    identity = hashlib.sha256(str(Path(sys.executable).resolve()).encode()).hexdigest()[:20]
    handle = kernel32.CreateMutexW(None, False, "Local\\OCRDOC-" + identity)
    if not handle:
        raise OSError("No se pudo iniciar OCR DOC. Prueba abrirlo otra vez.")
    duplicate = ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS
    try:
        yield not duplicate
    finally:
        kernel32.CloseHandle(handle)


def run_self_test(destination: Path) -> None:
    """Exercise the bundled interpreter, DLLs, Spanish OCR, PDF and DOCX offline."""
    import json
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont
    from docx import Document
    from ocr_engine import Job, export_docx, ocr_status, prepare_job, update_regions

    destination.mkdir(parents=True, exist_ok=True)
    ready, message = ocr_status()
    if not ready:
        raise RuntimeError(message)
    job = Job.create()
    try:
        scan = destination / "muestra.png"
        with Image.new("RGB", (1600, 1000), "white") as image:
            draw = ImageDraw.Draw(image)
            font = ImageFont.load_default(size=64)
            draw.text((90, 180), "CONTRATO DE SERVICIOS 12345", font=font, fill="black")
            draw.text((90, 850), "FIRMA", font=font, fill="black")
            image.save(scan)
        pdf_path = destination / "muestra.pdf"
        with pymupdf.open() as document:
            page = document.new_page(width=800, height=500)
            page.insert_image(page.rect, filename=str(scan))
            page = document.new_page()
            page.insert_text((72, 100), "Segunda pagina editable")
            document.save(pdf_path)
        with pdf_path.open("rb") as source:
            prepare_job(job, source, pdf_path.name)
        update_regions(job, 0, 0, 22)
        if "CONTRATO" not in job.page(0)["text"].upper() or "12345" not in job.page(0)["text"]:
            raise RuntimeError("El OCR empaquetado no reconoció la muestra en español.")
        output = export_docx(job)
        document = Document(output)
        text = "\n".join(p.text for p in document.paragraphs)
        if "Segunda pagina editable" not in text or len(document.inline_shapes) != 1:
            raise RuntimeError("El Word no conservó el texto o la imagen seleccionada.")
        import shutil
        shutil.copy2(output, destination / "resultado.docx")
        (destination / "resultado.json").write_text(json.dumps({
            "ok": True, "frozen": bool(getattr(sys, "frozen", False)),
            "pages": job.meta()["count"], "images": len(document.inline_shapes),
        }), encoding="utf-8")
        print("Prueba integrada completada.", flush=True)
    finally:
        job.close()


def main() -> None:
    import multiprocessing
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", type=Path)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--port", type=int, default=8517)
    args = parser.parse_args()
    root = configure_runtime()
    if args.self_test:
        run_self_test(args.self_test.resolve())
        return
    with single_instance() as first:
        if not first:
            print("OCR DOC ya está abierto. Revisa tu navegador y su ventana de inicio.")
            return
        port = available_port(args.port)
        os.chdir(root)
        print("OCR DOC · Escaneos a Word", flush=True)
        print("Mantén esta ventana abierta mientras trabajas.", flush=True)
        print("Descarga el Word antes de cerrar. Para apagar la aplicación, cierra esta ventana.", flush=True)
        print(f"Dirección local: http://127.0.0.1:{port}", flush=True)
        if not args.no_browser:
            threading.Thread(target=open_when_ready, args=(port,), daemon=True).start()
        from streamlit.web import cli
        sys.argv = ["streamlit", "run", str(root / "app.py"),
                    "--server.address=127.0.0.1", f"--server.port={port}",
                    "--server.headless=true", "--server.maxUploadSize=50",
                    "--browser.gatherUsageStats=false", "--global.developmentMode=false"]
        cli.main()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"No se pudo iniciar OCR DOC: {exc}", file=sys.stderr, flush=True)
        if getattr(sys, "frozen", False) and not NONINTERACTIVE:
            input("Pulsa Enter para cerrar…")
        raise SystemExit(1)
