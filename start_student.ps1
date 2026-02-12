param(
    [Parameter(Mandatory = $true)]
    [string]$StudentId,

    [Parameter(Mandatory = $true)]
    [string]$ServerUrl,

    [int]$CameraIndex = -1,
    [int]$CameraSearchMax = 5,
    [double]$Cooldown = 8.0,
    [switch]$EnablePhoneDetection,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

if (-not $SkipInstall) {
    Write-Host "Installing student dependencies..."
    python -m pip install -r backend/requirements_webcam.txt
}

$argsList = @(
    "backend/webcam_monitor.py",
    "--student-id", $StudentId,
    "--server-url", $ServerUrl,
    "--camera-index", "$CameraIndex",
    "--camera-search-max", "$CameraSearchMax",
    "--cooldown", "$Cooldown"
)

if ($EnablePhoneDetection) { $argsList += "--enable-phone-detection" }

python @argsList
