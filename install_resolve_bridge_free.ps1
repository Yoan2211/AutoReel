$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "ERREUR: Python AutoReel introuvable: $Python" -ForegroundColor Red
    exit 1
}

$Commit = "410dbac755e01ad45001ae23b79ade547a386473"
$TempRoot = Join-Path $env:TEMP "autoreel-davinci-resolve-mcp"
$ZipPath = Join-Path $TempRoot "davinci-resolve-mcp.zip"
$RepoDir = Join-Path $TempRoot ("davinci-resolve-mcp-" + $Commit)

if (Test-Path $TempRoot) {
    Remove-Item $TempRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $TempRoot | Out-Null

$Url = "https://github.com/samuelgursky/davinci-resolve-mcp/archive/$Commit.zip"

Write-Host ""
Write-Host "[1/4] Telechargement du bridge gratuit..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $Url -OutFile $ZipPath -UseBasicParsing

Write-Host "[2/4] Extraction..." -ForegroundColor Cyan
Expand-Archive -Path $ZipPath -DestinationPath $TempRoot -Force

$Installer = Join-Path $RepoDir "scripts\install_resolve_bridge.py"
if (-not (Test-Path $Installer)) {
    Write-Host "ERREUR: install_resolve_bridge.py introuvable apres extraction." -ForegroundColor Red
    exit 2
}

Write-Host "[3/4] Installation dans les dossiers Scripts de DaVinci Resolve..." -ForegroundColor Cyan
& $Python $Installer
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR: l'installateur du bridge a retourne le code $LASTEXITCODE." -ForegroundColor Red
    exit $LASTEXITCODE
}

$UserUtility = Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
$Config = Join-Path $HOME ".config\davinci-resolve-mcp\bridge.json"

Write-Host ""
Write-Host "[4/4] Verification..." -ForegroundColor Cyan
Write-Host "Dossier Scripts utilisateur: $UserUtility"
if (Test-Path $UserUtility) {
    Get-ChildItem $UserUtility | Select-Object Name, FullName
} else {
    Write-Host "Le dossier Scripts utilisateur n'existe pas encore." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Configuration attendue: $Config"
if (Test-Path $Config) {
    Write-Host "bridge.json: OK" -ForegroundColor Green
} else {
    Write-Host "bridge.json: NON TROUVE" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "INSTALLATION TERMINEE." -ForegroundColor Green
Write-Host "Ferme completement DaVinci Resolve s'il etait ouvert, puis relance-le."
Write-Host "Ensuite: Workspace > Scripts > resolve_bridge"
Write-Host ""
