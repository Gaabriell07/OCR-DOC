"""Local, sequential OCR. Large page images live on disk, not in session state."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Callable

from PIL import Image, ImageDraw, ImageOps

MAX_PAGES = 150
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_EDGE = 2600
Image.MAX_IMAGE_PIXELS = 20_000_000


class ConversionError(Exception):
    """An actionable error safe to display in the interface."""


def tesseract_path() -> str | None:
    # Frozen Windows builds use their own engine, never a system installation.
    if getattr(sys, "frozen", False):
        bundled = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "tesseract" / "tesseract.exe"
        return str(bundled) if bundled.is_file() else None
    explicit = os.environ.get("TESSERACT_CMD")
    if explicit and Path(explicit).is_file():
        return explicit
    found = shutil.which("tesseract")
    if found:
        return found
    for root in (os.environ.get("ProgramFiles", "C:/Program Files"),
                 os.environ.get("LOCALAPPDATA", "")):
        for suffix in ("Tesseract-OCR/tesseract.exe", "Programs/Tesseract-OCR/tesseract.exe"):
            candidate = Path(root) / suffix
            if candidate.is_file():
                return str(candidate)
    return None


def run_tesseract(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    executable = tesseract_path()
    if not executable:
        raise ConversionError("Falta Tesseract OCR. Consulta la instalación en README.md.")
    env = os.environ.copy()
    env["OMP_THREAD_LIMIT"] = "1"
    if getattr(sys, "frozen", False):
        env["TESSDATA_PREFIX"] = str(Path(executable).parent / "tessdata")
    try:
        return subprocess.run(
            [executable, *args], capture_output=True, timeout=timeout, env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise ConversionError("Esta página tardó más de 2 minutos. Prueba girarla o usar un escaneo más claro.") from exc
    except OSError as exc:
        raise ConversionError("No se pudo iniciar Tesseract. Revisa su instalación.") from exc


def ocr_status() -> tuple[bool, str]:
    try:
        result = run_tesseract(["--list-langs"], timeout=15)
        if result.returncode:
            return False, "Tesseract no pudo iniciarse. Revisa su instalación."
        if "spa" not in result.stdout.decode(errors="replace").splitlines():
            return False, "Falta el idioma español de Tesseract (spa.traineddata). Consulta README.md."
        return True, "OCR en español disponible"
    except ConversionError as exc:
        return False, str(exc)


def write_json(path: Path, value: dict) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


class Job:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    @classmethod
    def create(cls) -> "Job":
        return cls(tempfile.mkdtemp(prefix="ocr-doc-"))

    def close(self) -> None:
        shutil.rmtree(self.directory, ignore_errors=True)

    def meta(self) -> dict:
        return json.loads((self.directory / "job.json").read_text(encoding="utf-8"))

    def page(self, index: int) -> dict:
        return json.loads((self.directory / f"page-{index}.json").read_text(encoding="utf-8"))

    def save_page(self, index: int, value: dict) -> None:
        write_json(self.directory / f"page-{index}.json", value)
        (self.directory / "resultado.docx").unlink(missing_ok=True)

    def image_path(self, index: int) -> Path:
        return self.directory / f"page-{index}.jpg"


def cleanup_old_jobs(max_age_hours: int = 24) -> None:
    """Delete only our own expired workspaces; no background thread or cache."""
    now = time.time()
    for path in Path(tempfile.gettempdir()).glob("ocr-doc-*"):
        try:
            if path.is_dir() and now - path.stat().st_mtime > max_age_hours * 3600:
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass


def normalize_text(text: str) -> str:
    # Drop XML-invalid control characters before writing a DOCX.
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text).strip()


def recognize(image_path: Path, top: int = 0, bottom: int = 0) -> str:
    with Image.open(image_path) as source:
        image = ImageOps.autocontrast(source.convert("L"))
    try:
        draw = ImageDraw.Draw(image)
        width, height = image.size
        if top:
            draw.rectangle((0, 0, width, round(height * top / 100)), fill=255)
        if bottom:
            draw.rectangle((0, round(height * (100 - bottom) / 100), width, height), fill=255)
        temporary = image_path.with_suffix(".ocr.png")
        image.save(temporary)
    finally:
        image.close()
    try:
        result = run_tesseract([str(temporary), "stdout", "-l", "spa", "--psm", "3", "--dpi", "220"])
        if result.returncode:
            raise ConversionError("No se pudo reconocer esta página. Comprueba que Tesseract tenga el idioma español.")
        return normalize_text(result.stdout.decode("utf-8", errors="replace"))
    finally:
        temporary.unlink(missing_ok=True)


def prepare_job(job: Job, uploaded, name: str, dpi: int = 220,
                progress: Callable[[int, int], None] | None = None) -> None:
    """Stream upload to disk, then render and OCR one page at a time."""
    suffix = Path(name).suffix.lower()
    if suffix not in (".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"):
        raise ConversionError("Usa un PDF o una imagen JPG, PNG o TIFF.")
    input_path = job.directory / ("original" + suffix)
    uploaded.seek(0)
    size = 0
    with input_path.open("wb") as output:
        while chunk := uploaded.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise ConversionError("El archivo supera 50 MB. Divide el documento en varios PDF.")
            output.write(chunk)
    if not size:
        raise ConversionError("El archivo está vacío. Selecciona otro documento.")
    if suffix == ".pdf":
        _prepare_pdf(job, input_path, dpi, progress)
    else:
        _prepare_image(job, input_path, progress)
    meta = job.meta()
    meta["name"] = Path(name).stem
    write_json(job.directory / "job.json", meta)


def _prepare_pdf(job: Job, path: Path, dpi: int, progress) -> None:
    import pymupdf

    try:
        document = pymupdf.open(path)
    except Exception as exc:
        raise ConversionError("No se pudo abrir el PDF. Comprueba que no esté dañado.") from exc
    with document:
        if document.needs_pass:
            raise ConversionError("El PDF tiene contraseña. Guarda primero una copia sin contraseña.")
        count = len(document)
        if not 0 < count <= MAX_PAGES:
            raise ConversionError(f"Procesa entre 1 y {MAX_PAGES} páginas por archivo. Divide este PDF.")
        write_json(job.directory / "job.json", {"count": count})
        for index in range(count):
            page = document[index]
            scale = min(dpi / 72, MAX_EDGE / max(page.rect.width, page.rect.height))
            pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False,
                                 colorspace=pymupdf.csRGB)
            pix.save(str(job.image_path(index)), jpg_quality=86)
            del pix
            # Read existing text only if no large scanned-image region is present.
            # This avoids silently dropping scanned content on hybrid pages.
            text = normalize_text(page.get_text("text", sort=True))
            scanned = any(info["bbox"][2] - info["bbox"][0] > page.rect.width * .6
                          and info["bbox"][3] - info["bbox"][1] > page.rect.height * .4
                          for info in page.get_image_info())
            method = "Texto del PDF"
            if not text or scanned:
                text = recognize(job.image_path(index))
                method = "OCR"
            job.save_page(index, {"text": text, "top": 0, "bottom": 0,
                                  "method": method, "rotation": 0})
            if progress:
                progress(index + 1, count)


def _prepare_image(job: Job, path: Path, progress) -> None:
    try:
        source = Image.open(path)
    except Exception as exc:
        raise ConversionError("No se pudo abrir la imagen. Usa un JPG, PNG o TIFF válido.") from exc
    with source:
        count = getattr(source, "n_frames", 1)
        if not 0 < count <= MAX_PAGES:
            raise ConversionError(f"El archivo debe tener como máximo {MAX_PAGES} páginas.")
        write_json(job.directory / "job.json", {"count": count})
        for index in range(count):
            source.seek(index)
            if source.width * source.height > Image.MAX_IMAGE_PIXELS:
                raise ConversionError("La imagen es demasiado grande. Reduce su resolución antes de cargarla.")
            # JPEG draft decoding reduces memory before allocating RGB pixels.
            if source.format == "JPEG":
                source.draft("RGB", (MAX_EDGE, MAX_EDGE))
            image = ImageOps.exif_transpose(source)
            image.thumbnail((MAX_EDGE, MAX_EDGE))
            rgb = Image.new("RGB", image.size, "white")
            if image.mode == "RGBA":
                rgb.paste(image, mask=image.getchannel("A"))
            else:
                rgb.paste(image.convert("RGB"))
            rgb.save(job.image_path(index), quality=86)
            image.close()
            rgb.close()
            text = recognize(job.image_path(index))
            job.save_page(index, {"text": text, "top": 0, "bottom": 0,
                                  "method": "OCR", "rotation": 0})
            if progress:
                progress(index + 1, count)


def update_regions(job: Job, index: int, top: int, bottom: int, rotation: int = 0) -> None:
    if not (0 <= top <= 45 and 0 <= bottom <= 45 and rotation in (0, 90, 180, 270)):
        raise ConversionError("La selección de imagen o el giro no son válidos.")
    page = job.page(index)
    delta = rotation - page.get("rotation", 0)
    if delta:
        with Image.open(job.image_path(index)) as source:
            rotated = source.rotate(-delta, expand=True)
            rotated.save(job.image_path(index), quality=86)
            rotated.close()
    try:
        text = recognize(job.image_path(index), top, bottom)
    except Exception:
        # Restore image orientation if OCR fails, keeping image and metadata aligned.
        if delta:
            with Image.open(job.image_path(index)) as source:
                restored = source.rotate(delta, expand=True)
                restored.save(job.image_path(index), quality=86)
                restored.close()
        raise
    page.update(text=text, top=top, bottom=bottom, rotation=rotation, method="OCR")
    job.save_page(index, page)


def preview(job: Job, index: int, top: int = 0, bottom: int = 0) -> Image.Image:
    with Image.open(job.image_path(index)) as source:
        source.thumbnail((650, 850))
        result = source.convert("RGB")
    draw = ImageDraw.Draw(result)
    width, height = result.size
    for y in (round(height * top / 100), round(height * (100 - bottom) / 100)):
        if 0 < y < height:
            draw.line((0, y, width, y), fill="#16805E", width=3)
    return result


def _add_crop(document, job: Job, index: int, percent: int, bottom: bool) -> None:
    from docx.shared import Inches

    if not percent:
        return
    with Image.open(job.image_path(index)) as image:
        width, height = image.size
        y0, y1 = ((round(height * (100 - percent) / 100), height) if bottom
                  else (0, round(height * percent / 100)))
        crop = image.crop((0, y0, width, y1))
        crop.thumbnail((1400, 1400))
        crop_path = job.directory / "export-crop.jpg"
        crop.save(crop_path, quality=85)
        crop.close()
    try:
        # Constrain tall images as well as width, preventing oversized DOCX pages.
        inches = min(6.2, 3.0 * width / max(1, y1 - y0))
        document.add_picture(str(crop_path), width=Inches(inches))
    finally:
        crop_path.unlink(missing_ok=True)


def export_docx(job: Job) -> Path:
    from docx import Document
    from docx.shared import Inches, Pt

    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.27), Inches(11.69)
    section.top_margin = section.bottom_margin = Inches(.7)
    section.left_margin = section.right_margin = Inches(.85)
    normal = document.styles["Normal"]
    normal.font.name, normal.font.size = "Arial", Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    for index in range(job.meta()["count"]):
        if index:
            document.add_page_break()
        page = job.page(index)
        _add_crop(document, job, index, page["top"], False)
        for paragraph in re.split(r"\n\s*\n", normalize_text(page["text"])):
            if paragraph.strip():
                document.add_paragraph(" ".join(line.strip() for line in paragraph.splitlines()))
        _add_crop(document, job, index, page["bottom"], True)
    result = job.directory / "resultado.docx"
    document.save(result)
    return result
