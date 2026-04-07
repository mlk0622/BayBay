@echo off
cd "C:\Users\PC\OneDrive\Documents\PythonProject\gestion-locative"
pyinstaller BayBay.spec --noconfirm
cd electron-app
npx electron-packager . BayBay --platform=win32 --arch=x64 --out=dist-simple --overwrite
if not exist "dist-simple\BayBay-win32-x64\resources\backend" mkdir "dist-simple\BayBay-win32-x64\resources\backend"
xcopy "..\dist\BayBay\*" "dist-simple\BayBay-win32-x64\resources\backend\" /E /Y
cd ..
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
echo BUILD OK
pause