# Desbloquea la instalacion de Veu llevando a D: lo que pesa.
#
# NO borra nada y NO toca la cache de HuggingFace de C: (de la que dependen
# esdrac, Balua y demas). Solo crea el venv y la cache de modelos de ESTE
# proyecto en D:\Veu.
#
#   .\preparar_disco.ps1              # ver que haria, sin tocar nada
#   .\preparar_disco.ps1 -Ejecutar    # hacerlo de verdad

param(
    [switch]$Ejecutar,
    [string]$Destino = "D:\Veu"
)

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
$venvViejo = Join-Path $raiz ".venv"

Write-Host "Plan:" -ForegroundColor Cyan
Write-Host "  1. Crear $Destino\.venv con Python 3.12"
Write-Host "  2. Instalar torch cu128 + transformers alli"
Write-Host "  3. Dejar los modelos en $Destino\modelos (HF_HOME solo de este proyecto)"
Write-Host "  4. Escribir activar.ps1 en $raiz para usarlo comodamente"
if (Test-Path $venvViejo) {
    Write-Host "  5. Borrar el venv incompleto de C: ($venvViejo)" -ForegroundColor Yellow
}

$libre = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
Write-Host "`nLibre en D: $libre GB (hacen falta ~25 GB)" -ForegroundColor Cyan

if (-not $Ejecutar) {
    Write-Host "`nEnsayo. Relanza con -Ejecutar para hacerlo." -ForegroundColor Yellow
    exit 0
}

if ($libre -lt 30) { throw "Menos de 30 GB libres en D:, mejor revisarlo antes." }

New-Item -ItemType Directory -Force -Path "$Destino\modelos" | Out-Null
New-Item -ItemType Directory -Force -Path "$Destino\pip-cache" | Out-Null
New-Item -ItemType Directory -Force -Path "$Destino\tmp" | Out-Null

# Critico: por defecto pip cachea el wheel (2,7 GB el de torch) y descomprime
# en C:, que es justo lo que no tenemos. Todo a D: mientras dure la instalacion.
$env:HF_HOME = "$Destino\modelos"
$env:PIP_CACHE_DIR = "$Destino\pip-cache"
$env:TMP = "$Destino\tmp"
$env:TEMP = "$Destino\tmp"

py -3.12 -m venv "$Destino\.venv"
$py = "$Destino\.venv\Scripts\python.exe"

& $py -m pip install --upgrade pip
& $py -m pip install numpy sounddevice soundfile
& $py -m pip install torch --index-url https://download.pytorch.org/whl/cu128
& $py -m pip install transformers accelerate librosa

# Comprobacion real: que la GPU Blackwell responda, no solo que importe torch.
& $py -c "import torch; print('torch', torch.__version__, '| CUDA', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'sin GPU')"

$activar = @"
# Activa el entorno de Veu (venv y modelos viven en $Destino)
`$env:HF_HOME = "$Destino\modelos"
& "$Destino\.venv\Scripts\Activate.ps1"
"@
Set-Content -Path (Join-Path $raiz "activar.ps1") -Value $activar -Encoding utf8

if (Test-Path $venvViejo) {
    Remove-Item -Recurse -Force $venvViejo
    Write-Host "Borrado el venv incompleto de C:" -ForegroundColor Yellow
}

Write-Host "`nListo. A partir de ahora:  .\activar.ps1  y luego  python grabar.py" -ForegroundColor Green
