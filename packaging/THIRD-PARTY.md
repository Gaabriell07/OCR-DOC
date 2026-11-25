# Componentes incluidos

El instalador incorpora el intérprete de Python y las bibliotecas del proyecto,
además de una copia de Tesseract para Windows y los datos de español.

La compilación recoge los textos de licencias de las bibliotecas Python en
`_internal/licenses/python-licenses.json` y las versiones en
`_internal/licenses/python-versions.txt`. Los avisos distribuidos con Tesseract
se copian en `_internal/tesseract/licenses`.

Fuentes y referencias:

- Python: https://www.python.org/
- PyInstaller: https://pyinstaller.org/
- Streamlit: https://github.com/streamlit/streamlit
- PyMuPDF y MuPDF: https://pymupdf.readthedocs.io/en/latest/about.html
- Pillow: https://github.com/python-pillow/Pillow
- python-docx: https://github.com/python-openxml/python-docx
- Tesseract: https://github.com/tesseract-ocr/tesseract
- Compilación de Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Modelo español rápido, etiqueta 4.1.0:
  https://github.com/tesseract-ocr/tessdata_fast/tree/4.1.0

Se adjunta un ZIP del código de OCR DOC junto al instalador. Los avisos de terceros
no constituyen una licencia nueva para el proyecto ni sustituyen las licencias
originales de los componentes.
