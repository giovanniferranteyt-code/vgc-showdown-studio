@echo off
echo ========================================================
echo Compiling VGC ^& Showdown Studio with PyInstaller...
echo ========================================================

python -m PyInstaller --noconfirm --onedir --windowed --name "VGC_Showdown_Studio" --collect-all customtkinter --collect-all PIL --add-data "data;data" app.py

if exist "data" (
    echo Copying data folder to distribution...
    xcopy /E /I /Y "data" "dist\VGC_Showdown_Studio\data" >nul
)

echo.
echo ========================================================
echo Build finished! Executable located at:
echo dist\VGC_Showdown_Studio\VGC_Showdown_Studio.exe
echo ========================================================
if not "%1"=="--no-pause" (
    pause
)
