@echo off
echo ===================================================
echo  NVM2App Release Build Script
echo ===================================================

:: 1. Check virtual environment
if not exist ".venv" (
    echo [ERROR] Virtual environment ^(.venv^) not found.
    echo Please set up the development environment first.
    pause
    exit /b
)

:: 2. Get Version from User
echo ===================================================
set /p USER_VERSION="Enter build version (e.g. v 1.0.0): "
if "%USER_VERSION%"=="" (
    echo [ERROR] Version cannot be empty.
    pause
    exit /b
)

:: 3. Update version in app_info.py
echo Updating version in app_info.py to "%USER_VERSION%"...
call .venv\Scripts\activate.bat
python -c "import sys, re; fp = 'b_core/a_define/app_info.py'; c = open(fp, 'r', encoding='utf-8').read(); c = re.sub(r'APP_VERSION\s*=\s*.*', 'APP_VERSION = ' + chr(34) + sys.argv[1] + chr(34), c); open(fp, 'w', encoding='utf-8').write(c)" "%USER_VERSION%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to update version in app_info.py.
    pause
    exit /b
)

:: 3.5. Get today's date and define release folder name
for /f %%i in ('python -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%d'))"') do set TODAY=%%i
set RELEASE_DIR=3_build\%TODAY%-%USER_VERSION%

:: 3.7. Clean and recreate 3_build directory
echo Cleaning and preparing 3_build directory...
if exist "3_build" (
    rd /s /q "3_build"
)
mkdir "3_build"

:: 4. Build resource file
echo [1/4] Compiling resource file...
call .venv\Scripts\pyside6-rcc resources.qrc -o resources_rc.py
if %errorlevel% neq 0 (
    echo [ERROR] Resource file compilation failed.
    pause
    exit /b
)

:: 5. Check PyInstaller package
echo [2/4] Checking and installing PyInstaller...
python -m pip show pyinstaller > nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller is not installed. Installing now...
    python -m pip install pyinstaller
)

:: 6. Build release executable
echo [3/4] Running PyInstaller build (%RELEASE_DIR%/NVM2App.exe)...
python -m PyInstaller --noconsole --onefile --name NVM2App --icon="a_assets\icons\nova_icon.ico" --distpath "%RELEASE_DIR%" main.py
if %errorlevel% neq 0 (
    echo [ERROR] Build process failed.
    pause
    exit /b
)

:: 7. Copy extra resource folder
echo [4/4] Copying 2_resource folder to release folder...
if exist "2_resource" (
    xcopy "2_resource" "%RELEASE_DIR%\2_resource" /E /I /H /R /Y > nul
    echo 2_resource folder copied successfully.
) else (
    echo [WARNING] 2_resource folder not found. Skipping copy.
)

echo ===================================================
echo  Build completed successfully!
echo  Output: %RELEASE_DIR%/NVM2App.exe and %RELEASE_DIR%/2_resource/
echo ===================================================
pause
