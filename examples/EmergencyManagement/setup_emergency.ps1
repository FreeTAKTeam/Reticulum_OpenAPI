<#
.SYNOPSIS
    Provision and launch the Emergency Management example on Windows.
.DESCRIPTION
    Installs required Python and Node dependencies, ensures the web UI has a
    default .env file, and opens three PowerShell consoles for the server,
    FastAPI gateway, and Vite dev server respectively.
#>
[CmdletBinding()]
param(
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'

function Assert-CommandExists {
    param(
        [Parameter(Mandatory=$true)][string]$CommandName,
        [string]$FriendlyName = $null
    )
    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        $label = if ($FriendlyName) { $FriendlyName } else { $CommandName }
        throw "Required command '$label' was not found on PATH."
    }
}

$scriptRoot = Split-Path -LiteralPath $MyInvocation.MyCommand.Path -Parent
$repoRoot   = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
$serverDir  = Join-Path $scriptRoot 'Server'
$webUiDir   = Join-Path $scriptRoot 'webui'
$requirementsPath = Join-Path $repoRoot 'requirements.txt'
$envExample = Join-Path $webUiDir '.env.example'
$envFile    = Join-Path $webUiDir '.env'

Write-Host "Repository root: $repoRoot"

Assert-CommandExists -CommandName 'python' -FriendlyName 'Python 3'
Assert-CommandExists -CommandName 'npm' -FriendlyName 'Node.js/npm'

if (-not $SkipInstall) {
    Write-Host 'Installing Python dependencies...' -ForegroundColor Cyan
    python -m pip install --upgrade pip
    python -m pip install -r $requirementsPath

    Write-Host 'Installing web UI dependencies (npm install)...' -ForegroundColor Cyan
    Push-Location $webUiDir
    try {
        npm install
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host 'Skipping dependency installation as requested.' -ForegroundColor Yellow
}

function Start-AppConsole {
    param(
        [Parameter(Mandatory=$true)][string]$Title,
        [Parameter(Mandatory=$true)][string]$WorkingDirectory,
        [Parameter(Mandatory=$true)][string]$Command
    )

    $escapedTitle = $Title.Replace("'", "''")
    $escapedDir = $WorkingDirectory.Replace("'", "''")
    $commandBlock = "& {`$Host.UI.RawUI.WindowTitle = '$escapedTitle'; Set-Location -LiteralPath '$escapedDir'; $Command }"

    Write-Host "Launching: $Title -> $Command" -ForegroundColor Cyan
    Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-Command', $commandBlock) -WorkingDirectory $WorkingDirectory
}


if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Write-Host 'Creating default webui/.env configuration...' -ForegroundColor Cyan
        Copy-Item -Path $envExample -Destination $envFile
    } else {
        Write-Warning 'webui/.env.example not found; skipping .env creation.'
    }
} else {
    Write-Host 'webui/.env already exists; leaving it untouched.' -ForegroundColor Green
}


Start-AppConsole -Title 'Emergency Server' -WorkingDirectory $serverDir -Command 'python server_emergency.py'
Start-AppConsole -Title 'FastAPI Gateway' -WorkingDirectory $repoRoot -Command 'python -m uvicorn examples.EmergencyManagement.web_gateway.app:app --host 127.0.0.1 --port 8000 --reload'
Start-AppConsole -Title 'Web UI Dev Server' -WorkingDirectory $webUiDir -Command 'npm run dev'

Write-Host 'All components launched. Use Ctrl+C in each console to stop them when finished.' -ForegroundColor Green


