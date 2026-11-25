# Instalador autónomo para Windows x64

Objetivo: entregar un instalador que incluya Python, bibliotecas, Tesseract, DLLs
y español, sin instalaciones adicionales en la computadora de la usuaria.

**Estado real:** infraestructura implementada, pendiente de compilar y ejecutar
en Windows. No hay todavía un `.exe` verificado. El entorno Linux de desarrollo
no tiene acceso de red ni permite sockets locales; no puede completar la
compilación, ejecución del servidor o publicación. Las pruebas locales pasaron
18 casos y omitieron 4 por esas limitaciones y por dependencias no instaladas.

## Obtener el instalador con GitHub Actions

1. Sube el código actualizado a `main` de `Gaabriell07/OCR-DOC`.
2. En GitHub abre **Actions → Crear instalador Windows**. Se ejecuta al cambiar
   los archivos de la aplicación en `main`; también puedes pulsar **Run workflow**.
3. Espera a que el flujo completo termine en verde. Si falla, corrige el error
   antes de distribuir un instalador.
4. Descarga el artefacto **OCR-DOC-Windows-x64**. Descomprime y entrega el archivo
   `OCR-DOC-Setup-0.1.0-windows-x64.exe` a tu jefa.

El artefacto incluye el instalador, su SHA256, un ZIP del código y la lista de
versiones Python. No confundas este ZIP de fuentes con el programa instalable.

## Publicar un enlace permanente en Releases

Después de verificar la compilación de `main`, crea una etiqueta de versión
nueva, por ejemplo `v0.1.0`, y súbela. No reemplaces una etiqueta existente.

```bash
git tag v0.1.0
git push origin v0.1.0
```

El workflow compila y vuelve a comprobar el instalador para ese commit. Solo si
la compilación y las pruebas terminan bien, crea la Release con los archivos de
descarga. No publica ningún escaneo ni documento procesado.

## Qué se comprueba automáticamente

- El ejecutable congelado puede generar un PDF de prueba, leer un escaneo con
  Tesseract en español, conservar una firma como imagen y producir un DOCX.
- El instalador puede ejecutarse silenciosamente en una ruta con espacios.
- La aplicación instalada repite la prueba anterior con Python y Tesseract fuera
  del PATH y con variables de idioma heredadas incorrectas: debe usar sus propios
  componentes.
- El servidor local responde a su comprobación de salud y sirve la página HTML.
- Se ejecutan las pruebas del código fuente en Windows.

Esto no sustituye una revisión visual ni una prueba manual con Word. Antes de
entregarlo, instala en Windows 10/11 x64, abre desde el escritorio, convierte un
escaneo representativo, conserva una firma y comprueba el resultado en Word.
Idealmente valida en un equipo sin Python ni Tesseract instalados. No se ha
medido el pico real de memoria del paquete.

## Compilar manualmente en Windows (solo desarrollador)

Requiere Python 3.12 x64, Tesseract con `spa.traineddata` e Inno Setup 6. La
compilación descarga bibliotecas con pip; el programa resultante funciona localmente.

Desde PowerShell, en la carpeta del proyecto:

```powershell
py -3.12 -m venv .venv-build
& .\.venv-build\Scripts\python.exe -m pip install --upgrade pip
& .\packaging\build_windows.ps1 -Python .\.venv-build\Scripts\python.exe
```

Si Tesseract está en otra carpeta, añade `-TesseractSource 'C:\ruta\Tesseract-OCR'`.
Si la política corporativa bloquea scripts de PowerShell, usa el flujo de GitHub
Actions o consulta al administrador; no hace falta cambiar la política global.

Salida: `dist/installer/OCR-DOC-Setup-0.1.0-windows-x64.exe`.

## Decisiones de empaquetado

- PyInstaller en modo `onedir`: el intérprete y los recursos se instalan una vez,
  evitando la extracción del programa completo en cada apertura del modo `onefile`.
- El mismo OCR secuencial del proyecto; empaquetar no agrega modelos grandes ni
  elimina las necesidades de memoria de Streamlit y de las bibliotecas.
- Solo el modelo rápido español se incorpora al paquete. El workflow descarga
  `spa.traineddata` de la etiqueta `4.1.0` del repositorio oficial tessdata_fast.
- Inno Setup instala en `%LOCALAPPDATA%\Programs\OCR DOC`, crea accesos directos y
  registra un desinstalador, sin requerir administrador.
- El iniciador sirve la app en localhost, abre el navegador después de verificar
  que responde y evita varias instancias de la misma instalación en Windows.
- El paquete conserva los avisos de terceros y recopila las licencias de las
  bibliotecas. Tesseract e Inno Setup proceden de Chocolatey en el runner; sus
  versiones no están fijadas. Las versiones de Python se registran con pip freeze.
- El instalador no tiene firma de código. No se incluye ninguna instrucción para
  desactivar las protecciones de Windows.

Referencias técnicas consultadas:

- [PyInstaller: funcionamiento y necesidad de compilar para cada sistema](https://pyinstaller.org/en/stable/operating-mode.html)
- [Inno Setup: instalación sin elevación](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm)
- [Datos rápidos de español para Tesseract](https://github.com/tesseract-ocr/tessdata_fast/tree/4.1.0)
