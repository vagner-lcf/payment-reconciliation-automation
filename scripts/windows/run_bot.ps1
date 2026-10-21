$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$lockPath = Join-Path $projectRoot "bot.lock"
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"

try {
    $lock = [System.IO.File]::Open(
        $lockPath,
        [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
}

catch [System.IO.IOException] {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "           ATENCAO!" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "O PROGRAMA JA ESTA EM EXECUCAO!" -ForegroundColor Red
    Write-Host "Nao e necessario abrir outra janela." -ForegroundColor Yellow
    Write-Host "A janela original continua funcionando." -ForegroundColor White
    Write-Host ""
    Read-Host "Pressione Enter para fechar esta janela"
    exit 0
}

try {
    if (-not (Test-Path $pythonPath)) {
        throw "Ambiente Python nao encontrado."
    }

    Set-Location $projectRoot
    & $pythonPath -m src.telegram_bot

    if ($LASTEXITCODE -ne 0) {
        throw "O programa foi encerrado com erro (codigo $LASTEXITCODE)."
    }
}
catch {
    Write-Host ""
    Write-Host "ERRO: $($_.Exception.Message)"
    Read-Host "Pressione Enter para fechar"
}
finally {
    $lock.Dispose()
}
