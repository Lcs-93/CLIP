param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$requiredDirs = @("backend", "frontend", "worker")
foreach ($dir in $requiredDirs) {
    $fullPath = Join-Path $root $dir
    if (-not (Test-Path $fullPath)) {
        throw "Missing directory: $fullPath"
    }
}

$activateScript = @(
    (Join-Path $root "venv\Scripts\Activate.ps1"),
    (Join-Path $root ".venv\Scripts\Activate.ps1")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
$hasVenv = [bool]$activateScript

function New-ServiceCommand {
    param(
        [string]$Title,
        [string]$WorkingDir,
        [string]$RunCommand
    )

    $parts = @(
        "`$Host.UI.RawUI.WindowTitle = '$Title'",
        "Set-Location '$WorkingDir'"
    )
    if ($hasVenv) {
        $parts += "& '$activateScript'"
    }
    $parts += $RunCommand
    return ($parts -join "; ")
}

$services = @(
    @{
        Name = "backend"
        Command = New-ServiceCommand -Title "CLIP VIDEO - backend" -WorkingDir $root -RunCommand "uvicorn backend.main:app --reload --port 8000"
    },
    @{
        Name = "worker"
        Command = New-ServiceCommand -Title "CLIP VIDEO - worker" -WorkingDir $root -RunCommand "python -m worker.worker"
    },
    @{
        Name = "frontend"
        Command = New-ServiceCommand -Title "CLIP VIDEO - frontend" -WorkingDir (Join-Path $root "frontend") -RunCommand "npm run dev"
    }
)

foreach ($service in $services) {
    if ($DryRun) {
        Write-Host "[dry-run] $($service.Name): $($service.Command)"
        continue
    }

    Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $service.Command) `
        -WindowStyle Normal

    Start-Sleep -Milliseconds 250
}

if ($DryRun) {
    Write-Host ""
    Write-Host "Dry run complete."
} else {
    Write-Host ""
    Write-Host "Services started."
    Write-Host "Frontend: http://localhost:3000"
    Write-Host "Backend:  http://localhost:8000"
    Write-Host "API docs: http://localhost:8000/docs"
}
