@echo off
cd "C:\Users\PC\OneDrive\Documents\PythonProject\gestion-locative"

echo [1/4] Python build
pyinstaller BayBay.spec --noconfirm
if errorlevel 1 (
    echo ERREUR: Python build failed
    exit /b 1
)

echo [2/4] Electron package
cd electron-app
cmd /c "npx @electron/packager . BayBay --platform=win32 --arch=x64 --out=dist-simple --overwrite"
cd ..

echo [3/4] Copy backend
if not exist "electron-app\dist-simple\BayBay-win32-x64\resources\backend" mkdir "electron-app\dist-simple\BayBay-win32-x64\resources\backend"
xcopy "dist\BayBay\*" "electron-app\dist-simple\BayBay-win32-x64\resources\backend\" /E /Y

echo [4/4] NSIS Installer
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
if errorlevel 1 (
    echo ERREUR: NSIS a echoue
    exit /b 1
)

echo BUILD OK