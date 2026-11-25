@echo off
setlocal
cd /d "%~dp0"
echo Instalando OCR DOC...
py -3 --version >nul 2>&1
if errorlevel 1 (
  echo Instala Python 3.12 o superior desde https://www.python.org/downloads/windows/
  echo Activa el lanzador de Python durante la instalacion.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
if not exist .venv\Scripts\python.exe goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
echo.
echo Listo. Instala tambien Tesseract con el idioma espanol, como indica README.md.
echo Para usar la aplicacion, abre iniciar_windows.bat.
pause
exit /b 0
:error
echo No se pudo completar la instalacion. Revisa tu conexion y la version de Python.
pause
exit /b 1
