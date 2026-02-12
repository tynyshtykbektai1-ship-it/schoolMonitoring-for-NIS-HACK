param(
    [Parameter(Mandatory = $true)]
    [string]$StudentId,

    [switch]$EnablePhoneDetection,
    [switch]$WithDashboard,
    [int]$CameraIndex = -1,
    [double]$Cooldown = 8.0,
    [string]$ServerHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

if (-not $SkipInstall) {
    Write-Host "Installing dependencies for demo..."
    python -m pip install -r backend/requirements_demo.txt
}

$argsList = @(
    "backend/run_hackathon_demo.py",
    "--student-id", $StudentId,
    "--host", $ServerHost,
    "--port", "$Port",
    "--camera-index", "$CameraIndex",
    "--cooldown", "$Cooldown"
)

if ($EnablePhoneDetection) { $argsList += "--enable-phone-detection" }
if ($WithDashboard) { $argsList += "--with-dashboard" }

python @argsList
