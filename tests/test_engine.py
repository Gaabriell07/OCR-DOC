"""Run with: python -m unittest discover -s tests -v."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import ocr_engine as engine


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.job = engine.Job.create()

    def tearDown(self):
        self.job.close()

    def make_image(self, size=(400, 600)):
        with Image.new("RGB", size, "black") as image:
            image.save(self.job.image_path(0))

    def test_job_roundtrip_and_invalidates_old_export(self):
        path = self.job.directory / "resultado.docx"
        path.touch()
        self.job.save_page(0, {"text": "Señoría: S/ 1,234.50"})
        self.assertEqual(self.job.page(0)["text"], "Señoría: S/ 1,234.50")
        self.assertFalse(path.exists())

    def test_json_replacement_leaves_no_partial_file(self):
        path = self.job.directory / "job.json"
        engine.write_json(path, {"count": 1})
        engine.write_json(path, {"count": 2})
        self.assertEqual(self.job.meta()["count"], 2)
        self.assertFalse(path.with_suffix(".tmp").exists())

    def test_ocr_masks_only_selected_regions_and_removes_temporary(self):
        self.make_image()

        def fake_ocr(args):
            with Image.open(args[0]) as image:
                self.assertEqual(image.getpixel((200, 20)), 255)
                self.assertEqual(image.getpixel((200, 300)), 0)
                self.assertEqual(image.getpixel((200, 580)), 255)
            return subprocess.CompletedProcess(args, 0, "Texto íntegro\x0c".encode(), b"")

        with patch.object(engine, "run_tesseract", side_effect=fake_ocr):
            self.assertEqual(engine.recognize(self.job.image_path(0), 10, 20), "Texto íntegro")
        self.assertFalse(self.job.image_path(0).with_suffix(".ocr.png").exists())
        with Image.open(self.job.image_path(0)) as original:
            self.assertEqual(original.getpixel((200, 20)), (0, 0, 0))

    def test_ocr_failure_cleans_scratch_file(self):
        self.make_image()
        with patch.object(engine, "run_tesseract", return_value=subprocess.CompletedProcess([], 1, b"", b"error")):
            with self.assertRaises(engine.ConversionError):
                engine.recognize(self.job.image_path(0))
        self.assertFalse(self.job.image_path(0).with_suffix(".ocr.png").exists())

    def test_rotation_and_region_metadata(self):
        self.make_image()
        self.job.save_page(0, {"text": "old", "rotation": 0})
        with patch.object(engine, "recognize", return_value="nuevo"):
            engine.update_regions(self.job, 0, 10, 20, 90)
        self.assertEqual(self.job.page(0)["rotation"], 90)
        with Image.open(self.job.image_path(0)) as image:
            self.assertEqual(image.size, (600, 400))

    def test_failed_reread_restores_rotation_and_text(self):
        self.make_image()
        self.job.save_page(0, {"text": "Corrección guardada", "rotation": 0})
        with patch.object(engine, "recognize", side_effect=engine.ConversionError("error")):
            with self.assertRaises(engine.ConversionError):
                engine.update_regions(self.job, 0, 0, 20, 90)
        self.assertEqual(self.job.page(0)["text"], "Corrección guardada")
        with Image.open(self.job.image_path(0)) as image:
            self.assertEqual(image.size, (400, 600))

    def test_invalid_regions_rejected(self):
        with self.assertRaises(engine.ConversionError):
            engine.update_regions(self.job, 0, 50, 0)

    def test_preview_is_small_and_does_not_change_source(self):
        self.make_image((2000, 2600))
        with engine.preview(self.job, 0, 10, 20) as image:
            self.assertLessEqual(image.width, 650)
            self.assertLessEqual(image.height, 850)
        with Image.open(self.job.image_path(0)) as image:
            self.assertEqual(image.size, (2000, 2600))

    def test_unsupported_empty_and_oversize_input(self):
        for content, name in [(b"test", "virus.exe"), (b"", "test.pdf")]:
            with self.subTest(name=name), self.assertRaises(engine.ConversionError):
                engine.prepare_job(self.job, io.BytesIO(content), name)
        with patch.object(engine, "MAX_FILE_BYTES", 3):
            with self.assertRaises(engine.ConversionError):
                engine.prepare_job(self.job, io.BytesIO(b"1234"), "test.pdf")

    def test_image_prepare_with_mocked_ocr(self):
        buffer = io.BytesIO()
        Image.new("RGB", (300, 400), "white").save(buffer, format="PNG")
        updates = []
        with patch.object(engine, "recognize", return_value="Contrato"):
            engine.prepare_job(self.job, buffer, "escaneo.png", progress=lambda *x: updates.append(x))
        self.assertEqual(self.job.meta(), {"count": 1, "name": "escaneo"})
        self.assertEqual(self.job.page(0)["text"], "Contrato")
        self.assertEqual(updates, [(1, 1)])

    def test_tiff_processes_all_frames(self):
        buffer = io.BytesIO()
        first = Image.new("RGB", (100, 150), "white")
        second = Image.new("RGB", (100, 150), "gray")
        first.save(buffer, format="TIFF", save_all=True, append_images=[second])
        with patch.object(engine, "recognize", side_effect=["Uno", "Dos"]):
            engine.prepare_job(self.job, buffer, "escaneo.tiff")
        self.assertEqual(self.job.meta()["count"], 2)
        self.assertEqual(self.job.page(1)["text"], "Dos")

    def test_spanish_required(self):
        with patch.object(engine, "run_tesseract", return_value=subprocess.CompletedProcess([], 0, b"eng\nosd\n", b"")):
            self.assertFalse(engine.ocr_status()[0])

    def test_tesseract_limits_threads_and_timeout(self):
        with patch.object(engine, "tesseract_path", return_value="tesseract"), patch.object(engine.subprocess, "run") as run:
            engine.run_tesseract(["--list-langs"])
            self.assertEqual(run.call_args.kwargs["env"]["OMP_THREAD_LIMIT"], "1")
            run.side_effect = subprocess.TimeoutExpired("tesseract", 120)
            with self.assertRaises(engine.ConversionError):
                engine.run_tesseract([])

    def test_normalize_preserves_accents_and_removes_xml_controls(self):
        self.assertEqual(engine.normalize_text("  Señor\x00\x0c\nLima\tPerú  "), "Señor\nLima\tPerú")

    @unittest.skipUnless(importlib.util.find_spec("pymupdf") and importlib.util.find_spec("docx"), "Requiere PyMuPDF y python-docx")
    def test_real_pdf_to_docx_with_preserved_images(self):
        import pymupdf
        from docx import Document
        buffer = io.BytesIO()
        with pymupdf.open() as pdf:
            for text in ("Contrato de servicios", "Segunda pagina"):
                page = pdf.new_page()
                page.insert_text((72, 100), text)
            buffer.write(pdf.tobytes())
        engine.prepare_job(self.job, buffer, "contrato.pdf")
        page = self.job.page(0)
        page.update(top=10, bottom=20)
        self.job.save_page(0, page)
        result = engine.export_docx(self.job)
        document = Document(result)
        self.assertIn("Contrato de servicios", "\n".join(p.text for p in document.paragraphs))
        self.assertIn("Segunda pagina", "\n".join(p.text for p in document.paragraphs))
        self.assertEqual(len(document.inline_shapes), 2)

    @unittest.skipUnless(engine.ocr_status()[0], "Requiere Tesseract con español")
    def test_real_spanish_ocr(self):
        from PIL import ImageFont, ImageDraw
        # Large, crisp print is a smoke test, not a claim about real scans.
        image = Image.new("RGB", (1600, 350), "white")
        font = ImageFont.load_default(size=48)
        ImageDraw.Draw(image).text((50, 80), "CONTRATO DE SERVICIOS 12345", fill="black", font=font)
        image.save(self.job.image_path(0))
        image.close()
        text = engine.recognize(self.job.image_path(0))
        self.assertIn("CONTRATO", text.upper())
        self.assertIn("12345", text)


@unittest.skipUnless(importlib.util.find_spec("streamlit"), "Requiere Streamlit")
class InterfaceTests(unittest.TestCase):
    def test_initial_screen_has_no_exceptions(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "De escaneo a Word")
        convert = next(button for button in app.button if button.label == "Convertir documento")
        self.assertTrue(convert.disabled)


if __name__ == "__main__":
    unittest.main()
