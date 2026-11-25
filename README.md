# OCR DOC — de escaneo a Word

Aplicación local para convertir documentos impresos escaneados en texto editable
y descargarlos como Word. Diseñada para un flujo sencillo: cargar → revisar →
descargar. Funciona con el mismo código en Windows y Linux.

**Estado:** primera versión implementada. En el entorno de desarrollo pasaron
14 pruebas de lógica y procesamiento de imágenes. Las pruebas integradas PDF → DOCX,
OCR real y pantalla inicial, y la revisión visual de Streamlit están pendientes:
este entorno no pudo descargar dependencias y no tiene Tesseract. La instalación
y apertura en Windows también necesitan validación en un equipo Windows.

## Qué permite

- Arrastrar un PDF o una imagen JPG, PNG o TIFF (incluido TIFF de varias páginas).
- Recuperar texto existente del PDF o reconocer el español de páginas escaneadas.
- Revisar una página a la vez, con el original junto al texto editable.
- Girar una página mal orientada y volver a reconocerla.
- Conservar una franja superior como imagen (por ejemplo un logo) y/o una franja
  inferior (sello y firma). El usuario selecciona los límites con una vista previa.
- Descargar un `.docx` con texto editable, párrafos y las imágenes seleccionadas.
- Borrar los temporales de la sesión al terminar.

No reconstruye exactamente el formato del PDF, tablas complejas, columnas,
tipografías ni márgenes. Las imágenes no se detectan automáticamente: deben
seleccionarse mediante las franjas. El texto incluido en ellas se conserva como
imagen y deja de ser editable. Un sello superpuesto al cuerpo del documento puede
requerir edición manual en Word. No es un reconocedor de escritura a mano ni crea
firmas digitales. Una página de origen puede ocupar más de una página en Word
según la cantidad de texto y los recortes.

## Windows: instalación una sola vez

1. Descarga este proyecto como ZIP desde GitHub y **extrae toda la carpeta**.
2. Instala **Python 3.12 o superior de 64 bits**, con el lanzador `py`, desde
   [python.org](https://www.python.org/downloads/windows/).
3. Instala **Tesseract OCR**. La [documentación oficial de Tesseract para Windows](https://tesseract-ocr.github.io/tessdoc/Installation.html)
   enlaza los instaladores de UB Mannheim. En su instalador selecciona el idioma
   **Spanish / español** en los datos de idiomas adicionales. La ruta habitual es
   `C:\Program Files\Tesseract-OCR\tesseract.exe`.
4. Haz doble clic en **`instalar_windows.bat`** y espera a que termine. Este paso
   necesita internet para descargar las bibliotecas de Python.
5. Haz doble clic en **`iniciar_windows.bat`**. Se abrirá el navegador. Si no se abre,
   entra en `http://127.0.0.1:8501`.

Puedes crear un acceso directo a `iniciar_windows.bat` en el escritorio. Mantén
abierta la consola mientras trabajas; ciérrala o pulsa Ctrl+C para apagar la app.
Después de la instalación, el OCR no requiere internet. Word solo es necesario
para abrir y modificar el archivo descargado.

Si instalaste Tesseract en otra ruta, configura la variable `TESSERACT_CMD` con
la ruta completa del ejecutable. Para comprobar español, ejecuta en PowerShell:

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --list-langs
```

Debe aparecer `spa`. Si falta, instala el idioma español. También puedes descargar
`spa.traineddata` del repositorio oficial
[tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast)
y colocarlo en la carpeta `tessdata` de Tesseract.

## Linux

Necesitas Python 3.12 o superior y Tesseract con español. En Debian/Ubuntu con
una versión de Python compatible:

```bash
sudo apt install python3-venv python3-pip tesseract-ocr tesseract-ocr-spa
bash instalar_linux.sh
bash iniciar_linux.sh
```

En Arch Linux, instala `python`, `python-pip`, `tesseract` y
`tesseract-data-spa` con el gestor del sistema antes de ejecutar los scripts.
No se instala ningún paquete del sistema automáticamente.

Si utilizas `uv`:

```bash
uv venv
uv pip install -r requirements.txt
bash iniciar_linux.sh
```

## Uso diario

1. Escanea el documento como PDF, preferiblemente recto y bien iluminado.
2. Abre OCR DOC y arrastra el archivo. Pulsa **Convertir documento**.
3. Selecciona cada página y revisa nombres, fechas, montos y párrafos.
4. Si hay logos o firmas, abre **Conservar logo, sello o firma / girar la página**.
   Ajusta la franja superior/inferior; las líneas verdes indican los límites.
   Pulsa **Aplicar selección y volver a leer**. Esto reemplaza las correcciones de
   texto de esa página: configura las franjas antes de corregir el texto.
5. Corrige el texto y pulsa **Preparar Word**, luego **Descargar Word (.docx)**.
6. Abre el resultado en Word para ajustar su formato y personalizarlo.
7. Cuando termines, abre **Terminar y cargar otro documento** para borrar la sesión.

Los cambios del editor se guardan al salir del campo. No se recupera una sesión
desde la interfaz después de cerrar/reiniciar la aplicación: descarga el Word
antes de cerrar.

## Memoria y privacidad

- **Un solo proceso OCR y una página a la vez**, con `OMP_THREAD_LIMIT=1`.
- Las páginas comprimidas y los textos se guardan en una carpeta temporal local,
  no en una lista de imágenes en memoria ni en una caché global de Streamlit.
- La página renderizada tiene como máximo 2600 píxeles en su lado mayor. El modo
  equilibrado usa 180 DPI; el de más detalle, 220 DPI, ambos con el mismo máximo.
- La vista previa está limitada a 650 × 850 píxeles y los recortes a 1400 × 1400.
- Los PDF que ya contienen texto no necesitan OCR, salvo páginas con una imagen
  grande que puedan contener un escaneo.
- Límite de protección: **50 MB y 150 páginas por archivo**, e imágenes de hasta
  **20 megapíxeles**. No son cuotas de pago; se pueden procesar más archivos.
- No carga modelos de lenguaje, no requiere GPU y no utiliza una API de pago.
- La aplicación escucha solo en `127.0.0.1`. La telemetría de Streamlit está
  desactivada. No se suben documentos a terceros.
- Los temporales se borran al finalizar la sesión explícitamente. Si se cierra
  abruptamente, las carpetas `ocr-doc-*` de más de 24 horas se limpian al abrir una
  nueva sesión. No hay borrado seguro ni cifrado propio de esos archivos.

**No se ha medido todavía el pico de RAM de una conversión completa.** Streamlit
mantiene la carga y la descarga temporalmente en memoria; exportar el DOCX también
requiere memoria proporcional a sus recortes comprimidos. No se promete un límite
fijo de RAM. Para documentos grandes conviene dividir el PDF.

## Stack

Python + Streamlit + PyMuPDF + Tesseract en español + Pillow + python-docx.
Se usa Pillow en lugar de OpenCV para reducir dependencias. No hay base de datos,
servicio externo, Node.js ni alojamiento en Vercel.

## Validación

Con las dependencias instaladas:

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py ocr_engine.py
```

La prueba integrada genera un PDF real de dos páginas y verifica el texto y las
imágenes del DOCX. Se omite si faltan PyMuPDF o python-docx. Las pruebas unitarias
de OCR simulan Tesseract: no miden su precisión. Hay una prueba adicional con
Tesseract real que se omite si falta el motor o el idioma español. La prueba de
pantalla inicial se omite si falta Streamlit. El workflow de GitHub ejecuta las
pruebas con las dependencias completas en Linux al publicar el repositorio;
todavía no se ha ejecutado aquí. Valida el resultado con escaneos
representativos antes de utilizarlo como parte del trabajo diario.

Para una comprobación manual: convierte un PDF de texto, un escaneo y un TIFF;
comprueba el giro, la selección de firmas, el cambio de página y la descarga.
Abre el `.docx` en Word y compara su contenido con el original.
