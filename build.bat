@echo off
setlocal
cd /d "%~dp0"

echo [0/3] Clean artefacts precedents
if exist "electron-app\dist-simple" rmdir /s /q "electron-app\dist-simple"

echo [1/3] PyInstaller Backend Compile
pyinstaller BayBay.spec --noconfirm
if errorlevel 1 (
    echo ERREUR: PyInstaller a echoue
    exit /b 1
)

echo [2/3] Electron package
cd electron-app
cmd /c "npx @electron/packager . BayBay --platform=win32 --arch=x64 --out=dist-simple --icon=build/icon.ico --overwrite"
cd ..

echo [3/3] NSIS Installer
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
if errorlevel 1 (
    echo ERREUR: NSIS a echoue
    exit /b 1
)

echo BUILD OK