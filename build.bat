@echo off
setlocal
echo ===================================================
echo  NVM2App Release Build Script
echo ===================================================
:: NOTE: this file must stay ASCII-only. cmd.exe parses batch files with the
::       system ANSI codepage (CP949), so UTF-8 Korean comments break parsing.
::
:: Output layout:
::   0_build\[YYYYMMDD]-v[version]\
::       NVM2App\  : deploy files (NVM2App.exe + 2_resource)
::       source\   : project snapshot at build time
::                   (excludes .git/.venv/__pycache__/temp_build,
::                    0_build and 3_log are included as empty folders)
:: app_info.py is restored to the dev version after the build.
:: (the snapshot keeps the injected build version)

:: 1. Check virtual environment
if not exist ".venv" (
    echo [ERROR] Virtual environment ^(.venv^) not found.
    echo Please set up the development environment first.
    pause
    exit /b 1
)

:: 2. Get version from user
::    leading 'v'/'V' and spaces are stripped - app_info.py stores pure version ("1.0.0")
set /p USER_VERSION="Enter build version (e.g. 1.0.0): "
set "USER_VERSION=%USER_VERSION: =%"
if /i "%USER_VERSION:~0,1%"=="v" set "USER_VERSION=%USER_VERSION:~1%"
if "%USER_VERSION%"=="" (
    echo [ERROR] Version cannot be empty.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

:: 3. Prepare temp build folder + backup app_info.py (restored after build)
if exist "temp_build" rd /s /q "temp_build"
mkdir "temp_build"
copy /y "b_core\a_define\app_info.py" "temp_build\app_info.py.bak" > nul

:: 4. Inject version into app_info.py
::    (replaces only the quoted value, keeps trailing comment, count=1)
python -c "import sys, re; fp='b_core/a_define/app_info.py'; q=chr(34); c=open(fp, encoding='utf-8').read(); c=re.sub('APP_VERSION = ' + q + '[^' + q + ']*' + q, 'APP_VERSION = ' + q + sys.argv[1] + q, c, count=1); open(fp, 'w', encoding='utf-8').write(c)" "%USER_VERSION%"
if %errorlevel% neq 0 goto :fail

:: 5. Resolve release folder: 0_build\[date]-v[version]\
::    (0_build accumulates releases - only a same-named folder is recreated)
for /f %%i in ('python -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%d'))"') do set TODAY=%%i
set "RELEASE_DIR=0_build\%TODAY%-v%USER_VERSION%"
if exist "%RELEASE_DIR%" rd /s /q "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%\NVM2App"
mkdir "%RELEASE_DIR%\source"

:: 6. Build resource file
echo [1/5] Compiling resource file...
call .venv\Scripts\pyside6-rcc resources.qrc -o resources_rc.py
if %errorlevel% neq 0 goto :fail

:: 7. Check PyInstaller package
echo [2/5] Checking PyInstaller...
python -m pip show pyinstaller > nul 2>&1
if %errorlevel% neq 0 python -m pip install pyinstaller

:: 8. Build single exe (intermediate files go to temp_build)
::    ftd2xx.dll is embedded into the exe. At runtime dll_setup.py adds the
::    onefile extraction dir (sys._MEIPASS) to the DLL search path.
echo [3/5] Running PyInstaller build...
python -m PyInstaller --noconsole --onefile --name NVM2App --icon="%CD%\a_assets\icons\nova_icon.ico" --add-binary "%CD%\ftd2xx.dll;." --distpath "%RELEASE_DIR%\NVM2App" --workpath "temp_build" --specpath "temp_build" "%CD%\main.py"
if %errorlevel% neq 0 goto :fail

:: 9. Copy runtime resources next to exe
echo [4/5] Copying 2_resource to deploy folder...
if exist "2_resource" (
    xcopy "2_resource" "%RELEASE_DIR%\NVM2App\2_resource" /E /I /H /R /Y > nul
) else (
    echo [WARNING] 2_resource folder not found. Skipping copy.
)

:: 10. Source snapshot
::     robocopy exit codes 0-7 mean success, 8+ mean failure
echo [5/5] Creating source snapshot...
robocopy . "%RELEASE_DIR%\source" /E /XD .git .venv __pycache__ temp_build 0_build 3_build 3_log /XF *.pyc /NFL /NDL /NJH /NJS > nul
if %errorlevel% geq 8 goto :fail
mkdir "%RELEASE_DIR%\source\0_build"
mkdir "%RELEASE_DIR%\source\3_log"
python -m pip freeze > "%RELEASE_DIR%\source\requirements_snapshot.txt"

:: 11. Restore dev app_info.py and clean temp folder
copy /y "temp_build\app_info.py.bak" "b_core\a_define\app_info.py" > nul
rd /s /q "temp_build"

echo ===================================================
echo  Build completed successfully!
echo  Deploy : %RELEASE_DIR%\NVM2App\NVM2App.exe
echo  Source : %RELEASE_DIR%\source\
echo ===================================================
pause
exit /b 0

:fail
echo ===================================================
echo  [ERROR] Build failed.
echo ===================================================
if exist "temp_build\app_info.py.bak" (
    copy /y "temp_build\app_info.py.bak" "b_core\a_define\app_info.py" > nul
    echo app_info.py restored.
)
pause
exit /b 1
