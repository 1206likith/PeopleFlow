@echo off
setlocal

REM One-command backend bootstrap for Windows
python scripts\bootstrap_backend.py
if %ERRORLEVEL% neq 0 (
  echo.
  echo Backend bootstrap failed.
  exit /b %ERRORLEVEL%
)

echo.
echo Backend bootstrap completed successfully.
endlocal
