param(
    [switch]$InstallPython,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-PythonCommand {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{
            Exe = "python"
            Args = @()
        }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @{
            Exe = "py"
            Args = @("-3")
        }
    }
    return $null
}

function Install-PythonIfPossible {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "winget is not available. Install Python manually from https://www.python.org/downloads/"
        return $false
    }

    Write-Host "Installing Python via winget (Python.Python.3.11)..."
    winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Python installation via winget failed."
        return $false
    }
    return $true
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$bootstrapScript = Join-Path $repoRoot "scripts\start_project.py"

if (-not (Test-Path $bootstrapScript)) {
    Write-Error "Bootstrap script not found: $bootstrapScript"
}

$pythonCmd = Get-PythonCommand
if ($null -eq $pythonCmd) {
    Write-Host "Python 3.10+ is required but was not found."
    if ($InstallPython) {
        $ok = Install-PythonIfPossible
        if ($ok) {
            $pythonCmd = Get-PythonCommand
        }
    }

    if ($null -eq $pythonCmd) {
        Write-Host ""
        Write-Host "Install Python, then run again:"
        Write-Host "  .\start_project.ps1"
        Write-Host ""
        Write-Host "Optional auto-install:"
        Write-Host "  .\start_project.ps1 -InstallPython"
        exit 1
    }
}

Write-Host "Using Python launcher: $($pythonCmd.Exe) $($pythonCmd.Args -join ' ')"
$pythonExe = $pythonCmd.Exe
$pythonArgs = @($pythonCmd.Args)

Push-Location $repoRoot
try {
    & $pythonExe @pythonArgs $bootstrapScript @AppArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
