# kobiPass — tek dosya Windows .exe
# Kullanım: .\build_exe.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Update-WindowsIconCache {
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class ShellNotify {
    [DllImport("shell32.dll")]
    public static extern void SHChangeNotify(int eventId, uint flags, IntPtr item1, IntPtr item2);
}
"@
    # SHCNE_ASSOCCHANGED | SHCNF_IDLIST
    [ShellNotify]::SHChangeNotify(0x08000000, 0x00001000, [IntPtr]::Zero, [IntPtr]::Zero)
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Sanal ortam olusturuluyor..."
    python -m venv .venv
}

& .\.venv\Scripts\pip.exe install -q -r requirements.txt

if (-not (Test-Path "assets\logo.png")) {
    Write-Error "assets\logo.png bulunamadi."
}

& .\.venv\Scripts\python.exe scripts\make_assets.py

if (-not (Test-Path "assets\icon.ico")) {
    Write-Error "assets\icon.ico olusmadi."
}

$IconAscii = Join-Path $env:TEMP "KobiPass_icon_v2.ico"
Copy-Item -Path "assets\icon.ico" -Destination $IconAscii -Force
$iconKb = [math]::Round((Get-Item $IconAscii).Length / 1KB, 1)
Write-Host "Ikon: $IconAscii ($iconKb KB)"

$VersionFile = Join-Path $Root "assets\version_info.txt"
if (-not (Test-Path $VersionFile)) {
    Write-Error "assets\version_info.txt bulunamadi."
}

Get-Process -Name "kobiPass" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

& .\.venv\Scripts\pyinstaller.exe `
    --onefile `
    --windowed `
    --noupx `
    --name kobiPass `
    --icon $IconAscii `
    --version-file $VersionFile `
    --add-data "assets;assets" `
    --clean `
    main.py

$ExePath = Join-Path $Root "dist\kobiPass.exe"
if (-not (Test-Path $ExePath)) {
    Write-Error "dist\kobiPass.exe olusmadi."
}
$SizeMb = [math]::Round((Get-Item $ExePath).Length / 1MB, 2)
if ($SizeMb -lt 10) {
    Write-Error "Exe cok kucuk ($SizeMb MB). Derleme basarisiz."
}

$OutDir = "C:\kobiPass"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$DeployPath = Join-Path $OutDir "kobiPass.exe"
Copy-Item -Path $ExePath -Destination $DeployPath -Force
(Get-Item $DeployPath).LastWriteTime = Get-Date
(Get-Item $ExePath).LastWriteTime = Get-Date

Update-WindowsIconCache

Write-Host ""
Write-Host "Derleme tamam ($SizeMb MB):"
Write-Host "  $ExePath"
Write-Host "  $DeployPath"
Write-Host ""
Write-Host "Ikon hala eski gorunuyorsa:"
Write-Host "  1) Masaustu kisayolunu silip $DeployPath uzerinden yeni kisayol olusturun"
Write-Host "  2) Kisayol ozellikleri > Simge Degistir > $DeployPath secin"
Write-Host "  3) Dosya Gezgini'ni yeniden baslatin veya oturumu kapatip acin"
