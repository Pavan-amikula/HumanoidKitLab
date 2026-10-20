$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Write-Host 'Opening HumanoidKitLab desktop simulator'
Write-Host 'Keep this terminal open. Press Ctrl+C to stop.'
python app.py desktop
