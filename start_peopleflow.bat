@echo off
setlocal

pushd "%~dp0" >nul

set "POWERSHELL_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%POWERSHELL_EXE%" set "POWERSHELL_EXE=powershell.exe"

"%POWERSHELL_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_peopleflow.ps1" %*
set "exit_code=%errorlevel%"

popd >nul

if not "%exit_code%"=="0" (
  echo.
  echo PeopleFlow launcher failed with exit code %exit_code%.
  echo See the launcher output above for details.
  pause
)

exit /b %exit_code%
