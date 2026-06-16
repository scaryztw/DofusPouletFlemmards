@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo Python n'est pas installe ou pas dans le PATH.
  echo Installe-le depuis https://www.python.org/downloads/release/python-31210/
  echo Coche bien "Add python.exe to PATH" pendant l'installation.
  echo.
  pause
  exit /b
)
echo Installation des dependances ^(notifications natives incluses^)...
python -m pip install -r requirements.txt
echo.
echo Termine ! Lance maintenant  2-Lancer-DPF.bat
pause
