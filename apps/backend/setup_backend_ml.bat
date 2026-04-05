@echo off
setlocal

REM Optional ML bootstrap for backend extras (PyTorch / YOLO path)
python scripts\bootstrap_backend.py --with-ml
if %ERRORLEVEL% neq 0 (
  echo.
  echo Backend ML bootstrap failed.
  exit /b %ERRORLEVEL%
)

echo.
echo Backend ML bootstrap completed successfully.
endlocal
