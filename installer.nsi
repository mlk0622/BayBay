;Bay Bay Installer Script
!define APP_NAME "Bay Bay"
!define APP_VERSION "2.2.2"
!define APP_PUBLISHER "Bay Bay"
!define APP_URL "https://github.com/mlk0622/BayBay"
!define APP_DIR "BayBay-win32-x64"

Name "${APP_NAME}"
OutFile "Bay Bay Setup ${APP_VERSION}.exe"
InstallDir "$LOCALAPPDATA\${APP_NAME}"
InstallDirRegKey HKCU "Software\${APP_NAME}" ""
RequestExecutionLevel user

!include MUI2.nsh

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

!insertmacro MUI_PAGE_LICENSE "license.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "French"

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=${LANG_FRENCH} "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=${LANG_FRENCH} "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey /LANG=${LANG_FRENCH} "LegalCopyright" "© ${APP_PUBLISHER}"
VIAddVersionKey /LANG=${LANG_FRENCH} "FileDescription" "${APP_NAME} Setup"
VIAddVersionKey /LANG=${LANG_FRENCH} "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=${LANG_FRENCH} "ProductVersion" "${APP_VERSION}"

Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  File /r "electron-app\dist-simple\${APP_DIR}\*.*"

  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\BayBay.exe"
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\BayBay.exe"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\Désinstaller.lnk" "$INSTDIR\uninstall.exe"
SectionEnd

Section -AdditionalIcons
  WriteIniStr "$INSTDIR\${APP_NAME}.url" "InternetShortcut" "URL" "${APP_URL}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\Site Web.lnk" "$INSTDIR\${APP_NAME}.url"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\${APP_NAME}" "" $INSTDIR
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" "$INSTDIR\BayBay.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "URLInfoAbout" "${APP_URL}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
SectionEnd

Section Uninstall
  Delete "$INSTDIR\${APP_NAME}.url"
  Delete "$INSTDIR\uninstall.exe"

  RMDir /r "$INSTDIR"

  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey /ifempty HKCU "Software\${APP_NAME}"

  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Site Web.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Désinstaller.lnk"
  Delete "$DESKTOP\${APP_NAME}.lnk"

  RMDir "$SMPROGRAMS\${APP_NAME}"
SectionEnd
