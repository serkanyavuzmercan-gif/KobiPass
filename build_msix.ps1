# KobiPass - Microsoft Store (MSIX) paketi
# Kullanim: .\build_msix.ps1  [-Version 1.2.0.0] [-LayoutOnly] [-SkipSign]
#
# Store, surumun 4. bolumunun (revision) 0 olmasini ister: 1.2.0.0 (1.2.0.3 degil).

param(
    [string]$PackageName = "",
    [string]$Publisher = "",
    [string]$PublisherDisplayName = "",
    [string]$Version = "1.2.0.0",
    [switch]$SkipSign,
    [switch]$LayoutOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$DisplayName = "KobiPass"
$IdentityPath = Join-Path $Root "msix\identity.json"
if (Test-Path $IdentityPath) {
    $identity = Get-Content $IdentityPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $PSBoundParameters.ContainsKey("PackageName")) { $PackageName = $identity.PackageName }
    if (-not $PSBoundParameters.ContainsKey("Publisher")) { $Publisher = $identity.Publisher }
    if (-not $PSBoundParameters.ContainsKey("PublisherDisplayName")) { $PublisherDisplayName = $identity.PublisherDisplayName }
    if ($identity.PSObject.Properties.Name -contains "DisplayName") { $DisplayName = $identity.DisplayName }
}

$DistDir = Join-Path $Root "dist"
$PyDistDir = Join-Path $DistDir "kobiPass"
$LayoutDir = Join-Path $DistDir "msix-layout"
$MsixOutput = Join-Path $DistDir "KobiPass-$Version.msix"

function Find-WindowsKitTool {
    param([string]$ToolName)
    $roots = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
        "${env:ProgramFiles}\Windows Kits\10\bin"
    )
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        $match = Get-ChildItem -Path $root -Recurse -Filter $ToolName -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "\\x64\\" } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($match) { return $match.FullName }
    }
    return $null
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Sanal ortam olusturuluyor..."
    python -m venv .venv
}
$Py = ".\.venv\Scripts\python.exe"

Write-Host "Bagimliliklar kuruluyor..."
& $Py -m pip install -q -r (Join-Path $Root "requirements.txt")

Write-Host "logo.png ve icon.ico yeniden uretiliyor (kaynak: logo2.png)..."
& $Py (Join-Path $Root "scripts\make_assets.py")

Write-Host "Yurutulebilir dosya (onedir) PyInstaller ile derleniyor..."
if (Test-Path $PyDistDir) { Remove-Item $PyDistDir -Recurse -Force }
& $Py -m PyInstaller `
    --noconfirm `
    --windowed `
    --noupx `
    --name kobiPass `
    --icon (Join-Path $Root "assets\icon.ico") `
    --version-file (Join-Path $Root "assets\version_info.txt") `
    --add-data "assets;assets" `
    --distpath $DistDir `
    --workpath (Join-Path $Root "build\pyinstaller") `
    --clean `
    main.py

if (-not (Test-Path (Join-Path $PyDistDir "kobiPass.exe"))) {
    throw "PyInstaller ciktisi bulunamadi: $PyDistDir\kobiPass.exe"
}

Write-Host "MSIX yerlesimi hazirlaniyor..."
if (Test-Path $LayoutDir) { Remove-Item $LayoutDir -Recurse -Force }
New-Item -ItemType Directory -Path $LayoutDir | Out-Null
Copy-Item -Path (Join-Path $PyDistDir "*") -Destination $LayoutDir -Recurse -Force

Write-Host "MSIX gorselleri uretiliyor..."
& $Py (Join-Path $Root "scripts\generate_msix_assets.py") --output (Join-Path $LayoutDir "Assets")

Write-Host "AppxManifest.xml yaziliyor..."
& $Py (Join-Path $Root "scripts\apply_msix_manifest.py") --layout $LayoutDir --version $Version

$makeAppx = Find-WindowsKitTool "makeappx.exe"
if (-not $makeAppx) {
    Write-Warning "makeappx.exe bulunamadi. Windows SDK kurup tekrar calistirin."
    Write-Host "Kurulum:"
    Write-Host "  winget install --id Microsoft.WindowsSDK.10.0.18362 --accept-package-agreements --accept-source-agreements"
    Write-Host "MSIX yerlesimi hazir:"
    Write-Host "  $LayoutDir"
    if ($LayoutOnly) { exit 0 }
    throw "makeappx.exe yok. -LayoutOnly ile calistirin veya Windows SDK kurun."
}

if (Test-Path $MsixOutput) { Remove-Item $MsixOutput -Force }

Write-Host "MSIX paketleniyor..."
& $makeAppx pack /d $LayoutDir /p $MsixOutput /o | Write-Host

if (-not (Test-Path $MsixOutput)) { throw "MSIX paketi olusturulamadi: $MsixOutput" }

if (-not $SkipSign) {
    $signtool = Find-WindowsKitTool "signtool.exe"
    if ($signtool) {
        Write-Host "MSIX imzalaniyor (signtool)..."
        & $signtool sign /fd SHA256 /a $MsixOutput | Write-Host
    } else {
        Write-Warning "signtool.exe bulunamadi. Paket imzasiz olusturuldu."
    }
}

Write-Host ""
Write-Host "MSIX paketi hazir:"
Write-Host "  $MsixOutput"
Write-Host ""
Write-Host "Partner Center yukleme:"
Write-Host "  1. Paketi Manage packages altinda yukleyin."
Write-Host "  2. Kimlik degerleri msix\identity.json dosyasindan okunur - GERCEK Publisher (CN) ve PackageName ile guncelleyin."
Write-Host "  3. Yerelde imzalama basarisiz olursa, yukleme sirasinda Partner Center imzalasin."
