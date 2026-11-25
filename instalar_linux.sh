#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
printf '%s\n' 'Instalación Python completa. Instala tesseract-ocr y tesseract-ocr-spa con el gestor de tu distribución (ver README.md).'
