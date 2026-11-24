$ErrorActionPreference = 'Stop'
$PatchDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
foreach ($Name in @('oneclick-build','oneclick-out')) {
    $Target = Join-Path $PatchDir $Name
    if (Test-Path $Target) {
        $Full = (Resolve-Path $Target).Path
        if (-not $Full.StartsWith($PatchDir + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to delete a path outside patch directory: $Full"
        }
        Remove-Item -LiteralPath $Full -Recurse -Force
    }
}
Write-Host 'Removed temporary PyInstaller build folders; published EXE preserved.'
