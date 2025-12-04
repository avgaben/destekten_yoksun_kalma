@echo off
echo Destekten Yoksun Kalma TAM Rapor Testi Calisiyor...
echo.

cd /d "%~dp0"

python test_full_report.py

echo.
echo Islem tamamlandi.
pause
