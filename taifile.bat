@echo off
setlocal

REM ====== CONFIG ======
set "API_URL=http://10.239.2.174:5000/zip"
set "ZIP_PATH=%~dp0api_download.zip"
set "EXTRACT_DIR=C:\app1\mplus"


REM ====== PREP ======
if not exist "%EXTRACT_DIR%" (
    mkdir "%EXTRACT_DIR%"
)

echo [1/2] Dang tai file ZIP tu API...

REM ====== DOWNLOAD ======
where curl >nul 2>&1
if %errorlevel%==0 (
    curl -L "%API_URL%" -o "%ZIP_PATH%"
) else (
    powershell -NoProfile -Command "Invoke-WebRequest -Uri '%API_URL%' -OutFile '%ZIP_PATH%'"
)

if not exist "%ZIP_PATH%" (
    echo Loi: Khong tai duoc file ZIP.
    exit /b 1
)

echo Tai thanh cong: %ZIP_PATH%

REM ====== EXTRACT ======
echo [2/2] Dang giai nen vao C:\\app ...

powershell -NoProfile -Command ^
"Try { Expand-Archive -Path '%ZIP_PATH%' -DestinationPath '%EXTRACT_DIR%' -Force -ErrorAction Stop } Catch { Exit 2 }"

if %errorlevel%==2 (
    echo PowerShell Expand-Archive loi, thu su dung tar...
    tar -xf "%ZIP_PATH%" -C "%EXTRACT_DIR%"
)

echo Hoan tat! File da giai nen tai C:\\app

REM ====== CREATE SHORTCUT ON DESKTOP ======
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP_DIR=%%D"


set "SRC_EXE=%EXTRACT_DIR%\M_PLUS.exe"
set "LNK_PATH=%DESKTOP_DIR%\M_PLUS.lnk"

if exist "%SRC_EXE%" (
    powershell -NoProfile -Command ^
    "$WshShell = New-Object -ComObject WScript.Shell; " ^
    "$shortcut = $WshShell.CreateShortcut('%LNK_PATH%'); " ^
    "$shortcut.TargetPath = '%SRC_EXE%'; " ^
    "$shortcut.WorkingDirectory = '%EXTRACT_DIR%'; " ^
    "$shortcut.IconLocation = '%SRC_EXE%,0'; " ^
    "$shortcut.Save()"
    if %errorlevel%==0 (
        echo Da tao shortcut tren Desktop: "%LNK_PATH%"
    ) else (
        echo Loi: Khong the tao shortcut. Ma loi %errorlevel%.
    )

REM ====== NEW: LAUNCH THE APP AFTER EXTRACTION ======
    echo Dang mo ung dung...
    pushd "%EXTRACT_DIR%"
    start "" "%SRC_EXE%"
    popd

) else (
    echo Khong tim thay "%SRC_EXE%". Hay kiem tra ten file sau khi giai nen.
)

REM ====== DELETE DOWNLOADED ZIP ======
if exist "%ZIP_PATH%" (
    del /f /q "%ZIP_PATH%"
    echo Da xoa file ZIP: %ZIP_PATH%
) else (
    echo Khong tim thay file ZIP de xoa.
)
exit /b 0