@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  Lancement de DPF en mode DIAGNOSTIC (la fenetre reste ouverte).
echo  Si DPF plante, le message d'erreur s'affiche ci-dessous.
echo  Copie-le et envoie-le.
echo ============================================================
echo.
python run.py
echo.
echo ============================================================
echo  DPF s'est arrete (code %errorlevel%).
echo ============================================================
pause
