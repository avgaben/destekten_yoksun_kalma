@echo off
echo Destekten Yoksun Kalma Programi Calisiyor...
echo.

REM .bat dosyasinin bulundugu klasöre git
cd /d "%~dp0"

REM test dosyasini calistir
python test_life_tables.py

echo.
echo Islem tamamlandi.
pause
