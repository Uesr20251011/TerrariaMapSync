$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot
$python = Join-Path $env:USERPROFILE '.conda\envs\terraria-sync\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw '未找到 terraria-sync 环境，请先安装 requirements.txt 和 PyInstaller。'
}
$envRoot = Split-Path -Parent $python
$env:PATH = "$(Join-Path $envRoot 'Library\bin');$(Join-Path $envRoot 'Library\shiboken6');$(Join-Path $envRoot 'Scripts');$envRoot;$env:PATH"
& $python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name TerrariaMapSync --icon 'assets\app.ico' --add-data 'assets;assets' main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller 构建失败。' }
Write-Host '已生成 dist\TerrariaMapSync.exe'
