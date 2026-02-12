param(
    [string]$ServerHost = "0.0.0.0",
    [int]$Port = 8000,
    [switch]$WithDashboard,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

if (-not $SkipInstall) {
    Write-Host "Installing teacher dependencies..."
    python -m pip install -r backend/requirements.txt
}

Write-Host "Starting server on http://$ServerHost`:$Port ..."
Start-Process -FilePath "python" -ArgumentList @(
    "-m", "uvicorn", "backend.main:app",
    "--host", "$ServerHost",
    "--port", "$Port"
)

if ($WithDashboard) {
    Write-Host "Starting teacher dashboard..."
    Start-Process -FilePath "python" -ArgumentList @("backend/teacher_ws_dashboard.py")
}

Write-Host "Teacher services started."
Write-Host "Open http://127.0.0.1:$Port/ on teacher machine."
