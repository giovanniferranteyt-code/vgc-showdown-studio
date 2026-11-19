@echo off
echo ========================================================
echo Compiling VGC ^& Showdown Studio with PyInstaller...
echo ========================================================

python -m PyInstaller --noconfirm --onedir --windowed --name "VGC_Showdown_Studio" --collect-all customtkinter --collect-all PIL app.py

echo.
echo ========================================================
echo Build finished! Executable located at:
echo dist\VGC_Showdown_Studio\VGC_Showdown_Studio.exe
echo ========================================================
pause
