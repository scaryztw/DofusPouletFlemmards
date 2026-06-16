@echo off
REM ============================================================
REM  Construit DPF en .exe autonome (a lancer SUR WINDOWS).
REM  Tes utilisateurs n'auront alors PAS besoin de Python.
REM  Resultat -> dist\DofusPouletFlemmards\DofusPouletFlemmards.exe
REM ============================================================
cd /d "%~dp0"

echo Installation/maj de PyInstaller...
python -m pip install --upgrade pyinstaller

echo.
echo Construction de l'executable (onedir)...
python -m PyInstaller --noconfirm --onedir --windowed ^
  --name DofusPouletFlemmards ^
  --icon dpf-icone.ico ^
  --add-data "dpf-icone.ico;." ^
  --add-data "dpf-banner-light.png;." ^
  --add-data "dpf-banner-dark.png;." ^
  --collect-all winsdk ^
  --hidden-import win32timezone ^
  --hidden-import keyboard ^
  --hidden-import mouse ^
  run.py

echo.
echo ============================================================
echo  Termine.  ->  dist\DofusPouletFlemmards\
echo  Distribue TOUT le dossier "DofusPouletFlemmards" (pas juste l'exe).
echo  La config (dpf_config.json) et les logs se creent a cote de l'exe.
echo ============================================================
pause
