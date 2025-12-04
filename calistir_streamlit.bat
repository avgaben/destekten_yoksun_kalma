@echo off
echo Destekten Yoksun Kalma Tazminati Streamlit Arayuzu Calisiyor...
echo.

REM Bu satir .bat dosyasinin bulundugu klasore gider
cd /d "%~dp0"

REM Streamlit arayuzunu calistir
python -m streamlit run app.py

echo.
echo Streamlit uygulamasi kapandi.
pause
