import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import desktop_launcher as launcher
import ocr_engine as engine


class LauncherTests(unittest.TestCase):
    def test_resources_use_bundled_directory(self):
        with patch.object(sys, "_MEIPASS", "/bundled/resources", create=True):
            self.assertEqual(launcher.resource_directory(), Path("/bundled/resources"))

    def test_port_skips_occupied_listener(self):
        try:
            sock = socket.socket()
        except PermissionError:
            self.skipTest("El sandbox no permite crear sockets locales")
        with sock:
            try:
                sock.bind(("127.0.0.1", 0))
            except PermissionError:
                self.skipTest("El sandbox no permite escuchar en un puerto local")
            occupied = sock.getsockname()[1]
            if occupied >= 65505:
                self.skipTest("Puerto de prueba muy cercano al limite")
            self.assertNotEqual(launcher.available_port(occupied), occupied)

    def test_frozen_runtime_overrides_inherited_system_ocr(self):
        with patch.dict(os.environ, {"TESSERACT_CMD": "wrong.exe", "TESSDATA_PREFIX": "wrong-data"}), \
             patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "_MEIPASS", "/bundled", create=True):
            launcher.configure_runtime()
            self.assertEqual(os.environ["TESSERACT_CMD"], str(Path("/bundled/tesseract/tesseract.exe")))
            self.assertEqual(os.environ["OMP_THREAD_LIMIT"], "1")

    def test_frozen_engine_does_not_fall_back_to_system(self):
        with tempfile.TemporaryDirectory() as root, \
             patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "_MEIPASS", root, create=True), \
             patch.object(engine.shutil, "which", return_value="system-tesseract.exe"):
            self.assertIsNone(engine.tesseract_path())
            executable = Path(root) / "tesseract" / "tesseract.exe"
            executable.parent.mkdir()
            executable.touch()
            self.assertEqual(engine.tesseract_path(), str(executable))

    def test_frozen_subprocess_uses_bundled_language_data(self):
        with patch.object(sys, "frozen", True, create=True), \
             patch.object(engine, "tesseract_path", return_value="/bundle/tesseract/tesseract.exe"), \
             patch.object(engine.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            engine.run_tesseract(["--list-langs"])
            self.assertEqual(run.call_args.kwargs["env"]["TESSDATA_PREFIX"], str(Path("/bundle/tesseract/tessdata")))
