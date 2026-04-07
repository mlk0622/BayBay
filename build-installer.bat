@echo off
cd "C:\Users\PC\OneDrive\Documents\PythonProject\gestion-locative"

echo [1/3] Build Python
pyinstaller BayBay.spec --noconfirm

echo [2/3] Build Electron
cd electron-app
npx electron-packager . BayBay --platform=win32 --arch=x64 --out=dist-simple --overwrite
if not exist "dist-simple\BayBay-win32-x64\resources\backend" mkdir "dist-simple\BayBay-win32-x64\resources\backend"
xcopy "..\dist\BayBay\*" "dist-simple\BayBay-win32-x64\resources\backend\" /E /Y

echo [3/3] Create installer
cd ..
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi

if exist "Bay Bay Setup 2.1.0.exe" (
    echo BUILD OK: Bay Bay Setup 2.1.0.exe
) else (
    echo INSTALLER FAILED
)
pause