@echo off
setlocal

set "REPO_ROOT=%~dp0"
set "BOOTSTRAP=%REPO_ROOT%scripts\start_project.py"

if not exist "%BOOTSTRAP%" (
  echo Bootstrap script not found: "%BOOTSTRAP%"
  exit /b 1
)

set "PYTHON_CMD="
where python >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=python"
) else (
  where py >nul 2>nul
  if %errorlevel%==0 set "PYTHON_CMD=py -3"
)

if "%PYTHON_CMD%"=="" (
  echo Python 3.10+ is required but was not found.
  echo Install Python from https://www.python.org/downloads/
  echo Then run:
  echo   start_project.cmd
  exit /b 1
)

echo Using Python launcher: %PYTHON_CMD%
cd /d "%REPO_ROOT%"
%PYTHON_CMD% "%BOOTSTRAP%" %*
exit /b %errorlevel%
