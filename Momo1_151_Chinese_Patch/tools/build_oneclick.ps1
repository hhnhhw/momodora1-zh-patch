$ErrorActionPreference = 'Stop'
$PatchDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RepoRoot = (Resolve-Path (Join-Path $PatchDir '..')).Path
$OutputDir = Join-Path $PatchDir 'oneclick-out'
$WorkDir = Join-Path $PatchDir 'oneclick-build'
$SetupPath = Join-Path $PatchDir 'Momodora1ZH_Setup.exe'

if ($env:PROCESSOR_ARCHITECTURE -notmatch 'AMD64') {
    throw 'Build requires 64-bit Windows Python.'
}
& py -3 -c "import sys; assert sys.version_info >= (3, 10); assert sys.maxsize > 2**32"
if ($LASTEXITCODE -ne 0) { throw 'Use 64-bit Python 3.12.6 for reproducible zlib output.' }
$ZlibVersion = (& py -3 -c 'import zlib;print(zlib.ZLIB_VERSION)').Trim()
if ($LASTEXITCODE -ne 0 -or $ZlibVersion -ne '1.3.1') { throw "Expected zlib 1.3.1, found $ZlibVersion. Regenerating with a different compressor can change the target EXE hash." }
$PythonVersion = (& py -3 -c 'import platform;print(platform.python_version())').Trim()
if ($LASTEXITCODE -ne 0 -or $PythonVersion -ne '3.12.6') { throw "Expected Python 3.12.6, found $PythonVersion." }
$PyInstallerVersion = (& py -3 -m PyInstaller --version).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Install PyInstaller 6.22.3 before building.' }
if ($PyInstallerVersion -ne '6.22.3') { throw "Expected PyInstaller 6.22.3, found $PyInstallerVersion" }

# Remove stale output before compiling, so a broken build cannot look successful.
Remove-Item -LiteralPath $SetupPath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $OutputDir 'Momodora1ZH_Setup.exe') -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Path $OutputDir,$WorkDir -Force | Out-Null
$Manifest = Join-Path $PatchDir 'patch.json'
$Atlas = Join-Path $PatchDir 'assets\momo1_zh_text.png'
$Entry = Join-Path $PatchDir 'oneclick_gui.py'
$Tools = Join-Path $PatchDir 'tools'
$Licenses = Join-Path $PatchDir 'Licenses'
$AddData = @('--add-data', "$Manifest;.", '--add-data', "$Atlas;assets", '--add-data', "$Licenses;Licenses")
$Args = @('-3','-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed',
    '--name','Momodora1ZH_Setup','--distpath',$OutputDir,'--workpath',$WorkDir,
    '--specpath',$WorkDir,'--paths',$Tools,'--hidden-import','oneclick_core',
    '--hidden-import','apply_patch','--hidden-import','gm7','--hidden-import','tkinter',
    '--hidden-import','tkinter.ttk','--hidden-import','tkinter.filedialog',
    '--hidden-import','tkinter.messagebox') + $AddData + @($Entry)
& py @Args
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
$Built = Join-Path $OutputDir 'Momodora1ZH_Setup.exe'
if (-not (Test-Path $Built)) { throw 'Expected EXE was not created.' }
Copy-Item -LiteralPath $Built -Destination $SetupPath -Force
$Sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $SetupPath).Hash.ToLowerInvariant()
$Size = (Get-Item -LiteralPath $SetupPath).Length
$Report = [ordered]@{
    product = 'Momodora 1.51 Simplified Chinese One-click Installer'
    version = '0.1.0'
    file = 'Momodora1ZH_Setup.exe'
    architecture = 'x64'
    one_file = $true
    python_required_on_target = $false
    pyinstaller = $PyInstallerVersion
    python_build_version = (& py -3 -c 'import platform;print(platform.python_version())').Trim()
    size_bytes = $Size
    sha256 = $Sha
}
$Json = $Report | ConvertTo-Json -Depth 4
Set-Content -Path (Join-Path $PatchDir 'oneclick_build_report.json') -Value $Json -Encoding utf8
Set-Content -Path (Join-Path $PatchDir 'Momodora1ZH_Setup.exe.sha256') -Value "$Sha  Momodora1ZH_Setup.exe" -Encoding ascii
Write-Host "Built: $SetupPath"
Write-Host "Size: $Size bytes"
Write-Host "SHA-256: $Sha"
