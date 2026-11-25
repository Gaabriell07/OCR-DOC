param(
    [string]$TesseractSource = "$env:ProgramFiles\Tesseract-OCR",
    [string]$Python = "python",
    [ValidatePattern('^\d+\.\d+\.\d+$')][string]$Version = "0.1.0"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($env:OS -ne "Windows_NT") { throw "Compila este instalador en Windows x64." }
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    if (-not (Test-Path "$TesseractSource\tesseract.exe")) { throw "Falta Tesseract en $TesseractSource" }
    if (-not (Test-Path "$TesseractSource\tessdata\spa.traineddata")) { throw "Falta el idioma espanol spa.traineddata" }
    & $Python -c "import struct; assert struct.calcsize('P') == 8, 'Usa Python de 64 bits'"
    if ($LASTEXITCODE -ne 0) { throw "Python no es compatible." }
    & $Python -m pip install -r packaging/requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias de compilacion." }

    $vendor = Join-Path $root "vendor\tesseract"
    if (Test-Path $vendor) { Remove-Item $vendor -Recurse -Force }
    New-Item "$vendor\tessdata" -ItemType Directory -Force | Out-Null
    Copy-Item "$TesseractSource\tesseract.exe" $vendor
    Get-ChildItem $TesseractSource -Filter *.dll -File | Copy-Item -Destination $vendor
    Copy-Item "$TesseractSource\tessdata\spa.traineddata" "$vendor\tessdata"
    # Preserve bundled engine notices and dependency licenses when provided.
    Get-ChildItem $TesseractSource -Recurse -File |
        Where-Object { $_.Name -match '(?i)license|copying|copyright|notice' } |
        ForEach-Object {
            $relative = $_.FullName.Substring($TesseractSource.TrimEnd('\').Length).TrimStart('\')
            $destination = Join-Path "$vendor\licenses" $relative
            New-Item (Split-Path $destination) -ItemType Directory -Force | Out-Null
            Copy-Item $_.FullName $destination
        }
    & "$vendor\tesseract.exe" --list-langs
    if ($LASTEXITCODE -ne 0) { throw "El motor copiado no puede ejecutarse sin su instalacion." }

    New-Item build -ItemType Directory -Force | Out-Null
    & $Python -m piplicenses --with-license-file --format=json --output-file=build/python-licenses.json
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron recopilar las licencias." }
    & $Python -m pip freeze | Set-Content build/python-versions.txt -Encoding utf8
    $arguments = @(
        '--noconfirm', '--clean', '--onedir', '--console', '--name', 'OCR-DOC',
        '--collect-all', 'streamlit', '--copy-metadata', 'streamlit',
        '--collect-all', 'pymupdf', '--collect-all', 'docx',
        '--hidden-import', 'ocr_engine',
        '--add-data', 'app.py;.', '--add-data', '.streamlit;.streamlit',
        '--add-data', 'README.md;.', '--add-data', 'packaging/THIRD-PARTY.md;.',
        '--add-data', 'build/python-licenses.json;licenses',
        '--add-data', 'build/python-versions.txt;licenses',
        '--add-data', 'vendor/tesseract;tesseract', 'desktop_launcher.py'
    )
    & $Python -m PyInstaller @arguments
    if ($LASTEXITCODE -ne 0) { throw "Fallo PyInstaller." }
    # An .exe existing is insufficient: test its interpreter, OCR, DLLs and DOCX.
    & "dist\OCR-DOC\OCR-DOC.exe" --self-test "build\frozen-smoke"
    if ($LASTEXITCODE -ne 0) { throw "Fallo la prueba integrada del ejecutable." }
    $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    $iscc = if ($compiler) { $compiler.Source } else { '' }
    if (-not $iscc) {
        foreach ($candidate in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe")) {
            if (Test-Path $candidate) { $iscc = $candidate; break }
        }
    }
    if (-not $iscc) { throw "Instala Inno Setup 6 para generar el instalador." }
    & $iscc "/DAppVersion=$Version" packaging/windows.iss
    if ($LASTEXITCODE -ne 0) { throw "Fallo Inno Setup." }
    & $Python packaging/smoke_windows.py "dist\installer\OCR-DOC-Setup-$Version-windows-x64.exe"
    if ($LASTEXITCODE -ne 0) { throw "Fallo la comprobacion de la aplicacion instalada." }
    Get-FileHash "dist\installer\OCR-DOC-Setup-$Version-windows-x64.exe" -Algorithm SHA256 |
        ForEach-Object { "$($_.Hash.ToLower())  OCR-DOC-Setup-$Version-windows-x64.exe" } |
        Set-Content "dist\installer\SHA256SUMS.txt" -Encoding ascii
    Write-Host "Instalador preparado y comprobado en dist\installer."
} finally {
    Pop-Location
}
