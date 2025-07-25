@echo off
setlocal enableDelayedExpansion
chcp 65001 >nul 2>&1
title VCP Auto Update Tool v1.0

:: Initialize error handling
set "ERROR_LEVEL=0"
set "SCRIPT_SUCCESS=1"

:: Check Windows version and set color support
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
if "%VERSION%" LSS "10.0" (
    echo Warning: Your Windows version may not support colored output
    set "RED="
    set "GREEN="
    set "YELLOW="
    set "BLUE="
    set "PURPLE="
    set "CYAN="
    set "WHITE="
    set "BOLD="
    set "RESET="
) else (
    :: Color definitions using ANSI escape codes
    for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
    set "RESET=%ESC%[0m"
    set "RED=%ESC%[31m"
    set "GREEN=%ESC%[32m"
    set "YELLOW=%ESC%[33m"
    set "BLUE=%ESC%[34m"
    set "PURPLE=%ESC%[35m"
    set "CYAN=%ESC%[36m"
    set "WHITE=%ESC%[37m"
    set "BOLD=%ESC%[1m"
)

:: Display banner
echo.
echo ============================================
echo         VCP Auto Update Tool v1.0
echo ============================================
echo.

:: Change to script directory (VCPUpdate)
cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"

:: Validate required files exist
if not exist "update_vcp.py" (
    echo %RED%[ERROR] update_vcp.py script file not found%RESET%
    echo Please ensure all files are located in VCPUpdate directory
    echo Expected files:
    echo   - update_vcp.py
    echo   - update_vcp.bat
    echo   - update_vcp.sh
    pause
    exit /b 1
)

:: Check and validate Python installation
call :check_python
if !errorlevel! neq 0 (
    echo %RED%[CRITICAL] Python validation failed%RESET%
    pause
    exit /b 1
)

:: Main menu loop
:menu
cls
echo.
echo ============================================
echo         VCP Auto Update Tool v1.0
echo ============================================
echo.
echo %CYAN%Current Directory:%RESET% %CD%
echo %CYAN%Python Command:%RESET% !PYTHON_CMD!
echo %CYAN%Script Directory:%RESET% %SCRIPT_DIR%
echo.
echo Please select an option:
echo.
echo %BOLD%UPDATE OPTIONS:%RESET%
echo [1] Update All Projects ^(Parallel - Recommended^)
echo [2] Update All Projects ^(Sequential^)
echo [3] Update VCPChat Only
echo [4] Update VCPToolBox Only
echo.
echo %BOLD%ROLLBACK OPTIONS:%RESET%
echo [5] Rollback All Projects
echo [6] Rollback VCPChat
echo [7] Rollback VCPToolBox
echo.
echo %BOLD%CHECKPOINT OPTIONS:%RESET%
echo [8] List Git Checkpoints
echo [9] Restore to Specific Checkpoint
echo.
echo %BOLD%MANAGEMENT OPTIONS:%RESET%
echo [A] View Update Logs
echo [S] Show Project Status
echo [C] Edit Configuration File
echo [E] Export Config Template
echo [L] Clean Old Files
echo [T] Test Environment
echo [D] Debug Mode
echo [H] Show Help
echo [0] Exit
echo.
set /p choice="Enter your choice: "

:: Input validation and processing
if "%choice%"=="" (
    echo %YELLOW%[WARNING] No input provided%RESET%
    timeout /t 2 >nul
    goto menu
)

:: Process menu selection
if "%choice%"=="1" goto update_all_parallel
if "%choice%"=="2" goto update_all_sequential
if "%choice%"=="3" goto update_chat
if "%choice%"=="4" goto update_toolbox
if "%choice%"=="5" goto rollback_all
if "%choice%"=="6" goto rollback_chat
if "%choice%"=="7" goto rollback_toolbox
if "%choice%"=="8" goto list_checkpoints
if "%choice%"=="9" goto restore_checkpoint
if /i "%choice%"=="A" goto view_logs
if /i "%choice%"=="S" goto show_status
if /i "%choice%"=="C" goto edit_config
if /i "%choice%"=="E" goto export_config
if /i "%choice%"=="L" goto cleanup_files
if /i "%choice%"=="T" goto test_environment
if /i "%choice%"=="D" goto debug_mode
if /i "%choice%"=="H" goto show_help
if "%choice%"=="0" goto exit

echo.
echo %RED%[ERROR] Invalid choice: %choice%%RESET%
echo Please enter a valid option from the menu
timeout /t 3 >nul
goto menu

:: ============ UPDATE FUNCTIONS ============

:update_all_parallel
cls
echo.
echo %GREEN%Starting parallel update of all VCP projects...%RESET%
echo ====================================================
echo.
call :run_python_script "update_all_parallel" "--parallel"
goto check_result

:update_all_sequential
cls
echo.
echo %GREEN%Starting sequential update of all VCP projects...%RESET%
echo ======================================================
echo.
call :run_python_script "update_all_sequential" "--sequential"
goto check_result

:update_chat
cls
echo.
echo %GREEN%Starting VCPChat update...%RESET%
echo ==============================
echo.
call :run_python_script "update_chat" "--project" "chat"
goto check_result

:update_toolbox
cls
echo.
echo %GREEN%Starting VCPToolBox update...%RESET%
echo =================================
echo.
call :run_python_script "update_toolbox" "--project" "toolbox"
goto check_result

:: ============ ROLLBACK FUNCTIONS ============

:rollback_all
cls
echo.
echo %YELLOW%ROLLBACK CONFIRMATION%RESET%
echo ======================
echo.
echo Are you sure you want to rollback all projects?
echo This will undo the most recent update operations.
echo.
echo %RED%WARNING: This action cannot be undone easily%RESET%
echo.
call :get_confirmation "Enter Y to confirm rollback, any other key to cancel: " rollback_confirmed
if "!rollback_confirmed!"=="1" (
    echo.
    echo %GREEN%Starting rollback of all projects...%RESET%
    call :run_python_script "rollback_all" "--action" "rollback"
    goto check_result
) else (
    echo.
    echo %GREEN%Rollback operation cancelled%RESET%
    timeout /t 2 >nul
    goto menu
)

:rollback_chat
call :confirm_rollback "VCPChat" "chat"
goto menu

:rollback_toolbox
call :confirm_rollback "VCPToolBox" "toolbox"
goto menu

:: ============ CHECKPOINT FUNCTIONS ============

:list_checkpoints
cls
echo.
echo %BLUE%Listing available Git checkpoints...%RESET%
echo ========================================
echo.
call :run_python_script "list_checkpoints" "--action" "list-checkpoints"
echo.
pause
goto menu

:restore_checkpoint
cls
echo.
echo %YELLOW%Restore to Specific Checkpoint%RESET%
echo ==================================
echo.
echo First, let's view available checkpoints:
echo.
call :run_python_script "view_checkpoints" "--action" "list-checkpoints"
echo.
echo %CYAN%Project alias reference:%RESET%
echo - chat / vcpchat = VCPChat
echo - toolbox / tb / vcptoolbox = VCPToolBox
echo.
set /p project_choice="Select project: "

:: Validate and process project selection
call :normalize_project_name "!project_choice!" project_param
if "!project_param!"=="invalid" (
    echo.
    echo %RED%[ERROR] Invalid project selection: !project_choice!%RESET%
    echo Valid options: chat, vcpchat, toolbox, tb, vcptoolbox
    timeout /t 3 >nul
    goto menu
)

set /p checkpoint_name="Enter checkpoint name: "
if "!checkpoint_name!"=="" (
    echo.
    echo %RED%[ERROR] Checkpoint name cannot be empty%RESET%
    timeout /t 3 >nul
    goto menu
)

echo.
echo %GREEN%Restoring !project_choice! to checkpoint: !checkpoint_name!%RESET%
call :run_python_script "restore_checkpoint" "--action" "checkpoint" "--project" "!project_param!" "--checkpoint" "!checkpoint_name!"
goto check_result

:: ============ MANAGEMENT FUNCTIONS ============

:view_logs
cls
echo.
echo %BLUE%View Update Logs%RESET%
echo ===================
echo.

if not exist "%SCRIPT_DIR%update_vcp_logs\" (
    echo %YELLOW%No log directory found%RESET%
    echo Please run an update operation first to generate logs
    echo.
    pause
    goto menu
)

:: Find and list log files
set log_count=0
echo Available log files:
echo.
for /f "delims=" %%i in ('dir /b /o-d "%SCRIPT_DIR%update_vcp_logs\update_vcp_*.log" 2^>nul') do (
    set /a log_count+=1
    echo [!log_count!] %%i
    set "log!log_count!=%%i"
    if !log_count! geq 10 goto show_log_menu
)

:show_log_menu
if %log_count% equ 0 (
    echo %YELLOW%No log files found%RESET%
    echo.
    pause
    goto menu
)

echo.
echo [A] View last 100 lines of newest log
echo [F] View complete newest log
echo [S] Search in logs
echo [0] Return to main menu
echo.
set /p log_choice="Select log number (1-%log_count%) or operation: "

:: Process log choice
if /i "%log_choice%"=="0" goto menu
if /i "%log_choice%"=="A" (
    set log_choice=1
    set show_tail=1
) else if /i "%log_choice%"=="F" (
    set log_choice=1
    set show_tail=0
) else if /i "%log_choice%"=="S" (
    call :search_logs
    goto view_logs
) else (
    set show_tail=0
)

:: Validate numeric input
call :validate_number "!log_choice!" 1 !log_count! valid_choice
if "!valid_choice!"=="0" (
    echo.
    echo %RED%[ERROR] Invalid choice: !log_choice!%RESET%
    timeout /t 2 >nul
    goto view_logs
)

set selected_log=!log%log_choice%!

cls
echo.
echo ===== Log Content: !selected_log! =====
echo.

if !show_tail! equ 1 (
    :: Show last 100 lines using PowerShell or fallback
    call :show_log_tail "update_vcp_logs\!selected_log!"
) else (
    :: Show complete log
    type "update_vcp_logs\!selected_log!" 2>nul || (
        echo %RED%[ERROR] Cannot read log file%RESET%
        pause
        goto view_logs
    )
)

echo.
echo ===== End of Log =====
echo.
pause
goto view_logs

:show_status
cls
echo.
echo %BLUE%Displaying project status...%RESET%
echo ===============================
echo.
call :run_python_script "show_status" "--action" "status"
echo.
pause
goto menu

:edit_config
cls
echo.
echo %BLUE%Edit Configuration File%RESET%
echo ==========================
echo.

if exist "update_vcp_config.ini" (
    echo Opening configuration file...
    call :open_config_file
) else (
    echo %YELLOW%Configuration file does not exist%RESET%
    echo It will be created automatically on first script run
    echo.
    call :get_confirmation "Run status check to create config file? (Y/n): " create_config
    if "!create_config!"=="1" (
        call :run_python_script "create_config" "--action" "status"
        if exist "update_vcp_config.ini" (
            echo.
            echo %GREEN%Configuration file created successfully%RESET%
            call :open_config_file
        )
    )
)
echo.
pause
goto menu

:export_config
cls
echo.
echo %BLUE%Export Configuration Template%RESET%
echo ================================
echo.
call :run_python_script "export_config" "--action" "export-config"
echo.
if exist "update_vcp_config_template.ini" (
    echo %GREEN%Configuration template exported to: update_vcp_config_template.ini%RESET%
    echo.
    call :get_confirmation "Open configuration template? (Y/n): " open_template
    if "!open_template!"=="1" (
        start notepad "update_vcp_config_template.ini" 2>nul || (
            echo %YELLOW%Cannot open with notepad%RESET%
        )
    )
)
echo.
pause
goto menu

:cleanup_files
cls
echo.
echo %BLUE%Clean Old Files%RESET%
echo ==================
echo.
echo The following will be cleaned:
echo - Log files older than 30 days
echo - Expired backup files
echo - Unused Docker resources (if Docker available)
echo.
call :get_confirmation "Confirm cleanup? (Y/n): " confirm_cleanup
if "!confirm_cleanup!"=="1" (
    echo.
    call :run_python_script "cleanup" "--action" "cleanup"
    echo.
    echo %GREEN%Cleanup completed%RESET%
) else (
    echo.
    echo Cleanup cancelled
)
echo.
pause
goto menu

:test_environment
cls
echo.
echo %BLUE%Environment Test%RESET%
echo ===================
echo.

:: Check Python with detailed info
echo Checking Python environment...
call :check_python_detailed

echo.
:: Check Git
echo Checking Git installation...
git --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('git --version 2^>^&1') do echo %GREEN%[OK]%RESET% %%i
    
    :: Check Git configuration
    call :check_git_config
) else (
    echo %RED%[FAIL] Git not installed or not in PATH%RESET%
    echo Download from: https://git-scm.com/download/win
)

echo.
:: Check Docker
echo Checking Docker installation...
call :check_docker_environment

echo.
:: Check project directories
echo Checking project directory structure...
call :check_project_directories

echo.
:: Check VCPUpdate directory structure
echo Checking VCPUpdate directory structure...
call :check_vcpupdate_structure

echo.
:: Check network connectivity
echo Checking network connectivity...
call :check_network_connectivity

echo.
echo %GREEN%Environment test completed%RESET%
pause
goto menu

:debug_mode
cls
echo.
echo %BLUE%Debug Mode%RESET%
echo =============
echo.
echo Running script in debug mode with detailed execution information
echo.
echo Available operations:
echo [1] Status check with debug
echo [2] Update projects with debug
echo [3] Rollback with debug
echo [4] Custom debug command
echo [0] Return to main menu
echo.
set /p debug_choice="Select debug operation: "

if "%debug_choice%"=="1" (
    call :run_python_script "debug_status" "--action" "status" "--debug"
) else if "%debug_choice%"=="2" (
    echo.
    set /p debug_project="Which project to update? (all/chat/toolbox): "
    call :normalize_project_name "!debug_project!" debug_param
    if "!debug_param!"=="all" (
        call :run_python_script "debug_update_all" "--debug"
    ) else if "!debug_param!"=="invalid" (
        echo %RED%[ERROR] Invalid project: !debug_project!%RESET%
        timeout /t 2 >nul
        goto debug_mode
    ) else (
        call :run_python_script "debug_update" "--project" "!debug_param!" "--debug"
    )
) else if "%debug_choice%"=="3" (
    echo.
    set /p debug_project="Which project to rollback? (all/chat/toolbox): "
    call :normalize_project_name "!debug_project!" debug_param
    if "!debug_param!"=="all" (
        call :run_python_script "debug_rollback_all" "--action" "rollback" "--debug"
    ) else if "!debug_param!"=="invalid" (
        echo %RED%[ERROR] Invalid project: !debug_project!%RESET%
        timeout /t 2 >nul
        goto debug_mode
    ) else (
        call :run_python_script "debug_rollback" "--action" "rollback" "--project" "!debug_param!" "--debug"
    )
) else if "%debug_choice%"=="4" (
    echo.
    echo Example debug commands:
    echo   --action status --debug
    echo   --project chat --debug
    echo   --action list-checkpoints --debug
    echo.
    set /p custom_args="Enter custom command arguments: "
    if not "!custom_args!"=="" (
        call :run_python_script "custom_debug" !custom_args!
    )
) else if "%debug_choice%"=="0" (
    goto menu
) else (
    echo %RED%[ERROR] Invalid operation%RESET%
    timeout /t 2 >nul
    goto debug_mode
)

echo.
pause
goto menu

:show_help
cls
echo.
echo %BLUE%Help and Usage Information%RESET%
echo =================================
echo.
echo %CYAN%UPDATE FUNCTIONS:%RESET%
echo   Options 1-4: Different update modes
echo   - Parallel update: Multiple projects updated simultaneously (recommended)
echo   - Sequential update: Projects updated one after another
echo   - Individual updates: Update specific projects only
echo.
echo %CYAN%ROLLBACK FUNCTIONS:%RESET%
echo   Options 5-7: Undo recent updates
echo   - Confirmation required before rollback
echo   - Restores to pre-update state
echo.
echo %CYAN%CHECKPOINT FUNCTIONS:%RESET%
echo   Option 8: View all available Git checkpoints
echo   Option 9: Restore to specific checkpoint
echo   - Checkpoint types: before_update, after_fetch, after_merge, etc.
echo.
echo %CYAN%LOGS AND STATUS:%RESET%
echo   Option A: View detailed update logs
echo   Option S: Display current project status
echo   - Log search functionality available
echo   - Multiple log viewing options
echo.
echo %CYAN%CONFIGURATION MANAGEMENT:%RESET%
echo   Option C: Edit configuration file
echo   Option E: Export configuration template
echo   - Customize update behavior
echo   - Project-specific settings
echo.
echo %CYAN%MAINTENANCE FUNCTIONS:%RESET%
echo   Option L: Clean old logs and backups
echo   Option T: Check environment configuration
echo   Option D: Debug mode execution
echo   - Automatic cleanup of old files
echo   - Comprehensive environment testing
echo.
echo %CYAN%USEFUL TIPS:%RESET%
echo   - Project aliases: chat=VCPChat, toolbox=VCPToolBox
echo   - All runtime files stored in VCPUpdate directory
echo   - First-time users should run environment test (Option T)
echo   - Use debug mode (Option D) when troubleshooting issues
echo   - Backup is automatically created before updates
echo.
echo %CYAN%DIRECTORY STRUCTURE:%RESET%
echo   VCP\
echo   +-- VCPChat-main\      (VCPChat project)
echo   +-- VCPToolBox-main\   (VCPToolBox project)
echo   +-- VCPUpdate\         (Update tool directory)
echo       +-- update_vcp.py           (Main Python script)
echo       +-- update_vcp.bat          (This batch script)
echo       +-- update_vcp.sh           (Linux/macOS script)
echo       +-- update_vcp_config.ini   (Configuration file)
echo       +-- update_vcp_rollback_info.json (Rollback data)
echo       +-- update_vcp_logs\        (Log directory)
echo       +-- backups\                (Backup directory)
echo.
echo %CYAN%REQUIREMENTS:%RESET%
echo   - Python 3.7 or higher
echo   - Git 2.20 or higher
echo   - Docker (optional, for VCPToolBox)
echo   - Internet connection for updates
echo.
echo %CYAN%TROUBLESHOOTING:%RESET%
echo   - Git connection failed: Check network or configure proxy
echo   - Docker startup failed: Ensure Docker Desktop is running
echo   - Permission errors: Run as administrator
echo   - Path errors: Ensure script runs from VCPUpdate directory
echo   - Configuration issues: Check update_vcp_config.ini
echo.
pause
goto menu

:: ============ HELPER FUNCTIONS ============

:check_python
echo %CYAN%Checking Python installation...%RESET%
set PYTHON_CMD=

:: Check python3 first (preferred)
python3 --version >nul 2>&1
if !errorlevel! equ 0 (
    :: Verify Python 3.7+
    for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do (
        call :check_python_version "%%i" "python3" python_valid
        if "!python_valid!"=="1" (
            set PYTHON_CMD=python3
            echo %GREEN%[OK] Found Python3%RESET%
            goto :eof
        )
    )
)

:: Check python command
python --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do (
        call :check_python_version "%%i" "python" python_valid
        if "!python_valid!"=="1" (
            set PYTHON_CMD=python
            echo %GREEN%[OK] Found Python%RESET%
            goto :eof
        )
    )
)

:: Check Python Launcher
py --version >nul 2>&1
if !errorlevel! equ 0 (
    py -3 --version >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=2" %%i in ('py -3 --version 2^>^&1') do (
            call :check_python_version "%%i" "py -3" python_valid
            if "!python_valid!"=="1" (
                set PYTHON_CMD=py -3
                echo %GREEN%[OK] Found Python Launcher%RESET%
                goto :eof
            )
        )
    )
)

echo %RED%[ERROR] Python 3.7+ not found%RESET%
echo.
echo Please install Python 3.7 or higher from:
echo https://www.python.org/downloads/
echo.
echo Installation checklist:
echo [x] Add Python to PATH
echo [x] Install pip
echo [x] Install for all users (recommended)
echo.
exit /b 1

:check_python_version
set "version_string=%~1"
set "cmd_name=%~2"
set "result_var=%~3"

:: Extract major and minor version numbers
for /f "tokens=1,2 delims=." %%a in ("%version_string%") do (
    set major=%%a
    set minor=%%b
)

:: Check if version is 3.7 or higher
if !major! geq 3 (
    if !major! gtr 3 (
        set "%result_var%=1"
    ) else if !minor! geq 7 (
        set "%result_var%=1"
    ) else (
        set "%result_var%=0"
    )
) else (
    set "%result_var%=0"
)
goto :eof

:check_python_detailed
echo %CYAN%Detailed Python Check:%RESET%

if defined PYTHON_CMD (
    %PYTHON_CMD% --version >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do echo %GREEN%[OK]%RESET% %%i
        
        :: Check Python version compatibility
        %PYTHON_CMD% -c "import sys; exit(0 if sys.version_info >= (3,7) else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            echo %GREEN%[OK] Python version meets requirements (3.7+)%RESET%
        ) else (
            echo %YELLOW%[WARN] Python version too old, requires 3.7+%RESET%
        )
        
        :: Check required modules
        %PYTHON_CMD% -c "import json, configparser, subprocess, threading, pathlib" >nul 2>&1
        if !errorlevel! equ 0 (
            echo %GREEN%[OK] Required Python modules available%RESET%
        ) else (
            echo %YELLOW%[WARN] Some Python modules missing%RESET%
        )
        
        :: Check dataclasses module (Python 3.7+ feature)
        %PYTHON_CMD% -c "import dataclasses" >nul 2>&1
        if !errorlevel! equ 0 (
            echo %GREEN%[OK] Dataclasses module available%RESET%
        ) else (
            echo %YELLOW%[WARN] Dataclasses module missing (requires Python 3.7+)%RESET%
        )
    ) else (
        echo %RED%[FAIL] Python command execution failed%RESET%
    )
) else (
    echo %RED%[FAIL] No Python command available%RESET%
)
goto :eof

:run_python_script
set "operation_name=%~1"
shift
set "args="
:collect_args
if "%~1"=="" goto execute_python
set "args=%args% %1"
shift
goto collect_args

:execute_python
echo Executing: %PYTHON_CMD% update_vcp.py%args%
echo.
%PYTHON_CMD% update_vcp.py%args%
set "ERROR_LEVEL=%errorlevel%"
exit /b %ERROR_LEVEL%

:normalize_project_name
set "input=%~1"
set "output_var=%~2"
set "input_lower="

:: Convert to lowercase
for %%i in (A B C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    call set "input_lower=%%input_lower:%%i=%%i%%"
)
for %%i in (a b c d e f g h i j k l m n o p q r s t u v w x y z) do (
    call set "input_lower=%%input_lower:%%i=%%i%%"
)

:: Handle special case for "all"
if /i "%input%"=="all" (
    set "%output_var%=all"
    goto :eof
)

:: Map project aliases
if /i "%input%"=="chat" set "%output_var%=chat" & goto :eof
if /i "%input%"=="vcpchat" set "%output_var%=chat" & goto :eof
if /i "%input%"=="vcpchat-main" set "%output_var%=chat" & goto :eof
if /i "%input%"=="toolbox" set "%output_var%=toolbox" & goto :eof
if /i "%input%"=="tb" set "%output_var%=toolbox" & goto :eof
if /i "%input%"=="vcptoolbox" set "%output_var%=toolbox" & goto :eof
if /i "%input%"=="vcptoolbox-main" set "%output_var%=toolbox" & goto :eof

:: Invalid input
set "%output_var%=invalid"
goto :eof

:confirm_rollback
set "project_name=%~1"
set "project_param=%~2"
cls
echo.
echo %YELLOW%ROLLBACK CONFIRMATION%RESET%
echo ======================
echo.
echo Are you sure you want to rollback %project_name%?
echo This will undo the most recent update for this project.
echo.
echo %RED%WARNING: Rollback will restore to pre-update state%RESET%
echo          including code and configuration files
echo.
call :get_confirmation "Enter Y to confirm rollback, any other key to cancel: " rollback_confirmed
if "!rollback_confirmed!"=="1" (
    echo.
    echo %GREEN%Starting rollback of %project_name%...%RESET%
    call :run_python_script "rollback_%project_param%" "--action" "rollback" "--project" "%project_param%"
    call :check_result
) else (
    echo.
    echo %GREEN%Rollback operation cancelled%RESET%
    timeout /t 2 >nul
)
goto :eof

:get_confirmation
set "prompt=%~1"
set "result_var=%~2"
set /p user_input="%prompt%"
if /i "%user_input%"=="Y" (
    set "%result_var%=1"
) else (
    set "%result_var%=0"
)
goto :eof

:validate_number
set "input=%~1"
set "min_val=%~2"
set "max_val=%~3"
set "result_var=%~4"

:: Check if input is numeric
set /a test_num=%input% 2>nul
if %test_num% geq %min_val% if %test_num% leq %max_val% (
    set "%result_var%=1"
) else (
    set "%result_var%=0"
)
goto :eof

:search_logs
set /p search_term="Enter search term: "
if not "%search_term%"=="" (
    echo.
    echo %YELLOW%Search results:%RESET%
    findstr /i "%search_term%" update_vcp_logs\*.log 2>nul || echo No matches found
    echo.
    pause
)
goto :eof

:show_log_tail
set "log_file=%~1"
powershell -Command "Get-Content '%log_file%' -Tail 100" 2>nul || (
    echo PowerShell not available, showing last 50 lines using more:
    echo.
    more +1000000 "%log_file%" 2>nul || type "%log_file%"
)
goto :eof

:open_config_file
:: Try different editors in order of preference
if exist "%PROGRAMFILES%\Notepad++\notepad++.exe" (
    start "" "%PROGRAMFILES%\Notepad++\notepad++.exe" "update_vcp_config.ini"
    echo %GREEN%Configuration file opened in Notepad++%RESET%
) else if exist "%PROGRAMFILES(x86)%\Notepad++\notepad++.exe" (
    start "" "%PROGRAMFILES(x86)%\Notepad++\notepad++.exe" "update_vcp_config.ini"
    echo %GREEN%Configuration file opened in Notepad++%RESET%
) else if exist "%PROGRAMFILES%\Microsoft VS Code\Code.exe" (
    start "" "%PROGRAMFILES%\Microsoft VS Code\Code.exe" "update_vcp_config.ini"
    echo %GREEN%Configuration file opened in VS Code%RESET%
) else (
    start notepad "update_vcp_config.ini" || (
        echo %YELLOW%Failed to open with notepad, trying alternative...%RESET%
        if exist "%SYSTEMROOT%\system32\write.exe" (
            start write "update_vcp_config.ini"
            echo %GREEN%Configuration file opened in WordPad%RESET%
        ) else (
            echo %RED%Please manually edit: update_vcp_config.ini%RESET%
        )
    )
)
goto :eof

:check_git_config
git config --global user.name >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('git config --global user.name 2^>nul') do (
        if not "%%i"=="" (
            echo %GREEN%[OK] Git user: %%i%RESET%
        ) else (
            echo %YELLOW%[WARN] Git user name not configured%RESET%
        )
    )
) else (
    echo %YELLOW%[WARN] Git user not configured%RESET%
)

git config --global user.email >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('git config --global user.email 2^>nul') do (
        if not "%%i"=="" (
            echo %GREEN%[OK] Git email: %%i%RESET%
        ) else (
            echo %YELLOW%[WARN] Git email not configured%RESET%
        )
    )
) else (
    echo %YELLOW%[WARN] Git email not configured%RESET%
)
goto :eof

:check_docker_environment
docker --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('docker --version 2^>^&1') do echo %GREEN%[OK]%RESET% %%i
    
    :: Check Docker Compose
    docker-compose --version >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=*" %%i in ('docker-compose --version 2^>^&1') do echo %GREEN%[OK]%RESET% %%i
    ) else (
        docker compose version >nul 2>&1
        if !errorlevel! equ 0 (
            for /f "tokens=*" %%i in ('docker compose version 2^>^&1') do echo %GREEN%[OK] Docker Compose (plugin):%RESET% %%i
        ) else (
            echo %YELLOW%[WARN] Docker Compose not found%RESET%
        )
    )
    
    :: Check Docker service status
    docker info >nul 2>&1
    if !errorlevel! equ 0 (
        echo %GREEN%[OK] Docker service is running%RESET%
    ) else (
        echo %YELLOW%[WARN] Docker service not running - please start Docker Desktop%RESET%
    )
) else (
    echo %YELLOW%[WARN] Docker not installed or not running%RESET%
    echo Download from: https://www.docker.com/products/docker-desktop
)
goto :eof

:check_project_directories
pushd "%SCRIPT_DIR%.." 2>nul || (
    echo %RED%[ERROR] Cannot access parent directory%RESET%
    goto :eof
)

if exist "VCPChat-main\" (
    echo %GREEN%[OK] VCPChat-main directory exists%RESET%
    if exist "VCPChat-main\.git\" (
        echo %GREEN%[OK] VCPChat-main is a Git repository%RESET%
    ) else (
        echo %YELLOW%[WARN] VCPChat-main is not a Git repository%RESET%
    )
) else (
    echo %RED%[FAIL] VCPChat-main directory not found%RESET%
)

if exist "VCPToolBox-main\" (
    echo %GREEN%[OK] VCPToolBox-main directory exists%RESET%
    if exist "VCPToolBox-main\.git\" (
        echo %GREEN%[OK] VCPToolBox-main is a Git repository%RESET%
    ) else (
        echo %YELLOW%[WARN] VCPToolBox-main is not a Git repository%RESET%
    )
    
    :: Check for Docker Compose files
    set "compose_found=0"
    if exist "VCPToolBox-main\docker-compose.yml" (
        echo %GREEN%[OK] Docker Compose configuration found (docker-compose.yml)%RESET%
        set "compose_found=1"
    ) else if exist "VCPToolBox-main\docker-compose.yaml" (
        echo %GREEN%[OK] Docker Compose configuration found (docker-compose.yaml)%RESET%
        set "compose_found=1"
    ) else if exist "VCPToolBox-main\compose.yml" (
        echo %GREEN%[OK] Docker Compose configuration found (compose.yml)%RESET%
        set "compose_found=1"
    ) else if exist "VCPToolBox-main\compose.yaml" (
        echo %GREEN%[OK] Docker Compose configuration found (compose.yaml)%RESET%
        set "compose_found=1"
    )
    
    if !compose_found! equ 0 (
        echo %YELLOW%[WARN] Docker Compose configuration not found%RESET%
    )
) else (
    echo %RED%[FAIL] VCPToolBox-main directory not found%RESET%
)

popd
goto :eof

:check_vcpupdate_structure
if exist "update_vcp_logs\" (
    set /a log_file_count=0
    for %%f in ("update_vcp_logs\update_vcp_*.log") do (
        if exist "%%f" set /a log_file_count+=1
    )
    echo %GREEN%[OK] Log directory exists (!log_file_count! log files)%RESET%
) else (
    echo %CYAN%[INFO] Log directory will be created on first run%RESET%
)

if exist "update_vcp_config.ini" (
    echo %GREEN%[OK] Configuration file exists%RESET%
) else (
    echo %CYAN%[INFO] Configuration file will be created on first run%RESET%
)

if exist "update_vcp_rollback_info.json" (
    echo %GREEN%[OK] Rollback info file exists%RESET%
) else (
    echo %CYAN%[INFO] Rollback info file will be created after first update%RESET%
)

if exist "backups\" (
    set /a backup_count=0
    for %%f in ("backups\*.bundle") do (
        if exist "%%f" set /a backup_count+=1
    )
    echo %GREEN%[OK] Backup directory exists (!backup_count! backups)%RESET%
) else (
    echo %CYAN%[INFO] Backup directory will be created when needed%RESET%
)

:: Check for Python cache
if exist "__pycache__\" (
    echo %GREEN%[OK] Python cache directory exists%RESET%
) else (
    echo %CYAN%[INFO] Python cache directory will be created automatically%RESET%
)
goto :eof

:check_network_connectivity
ping -n 1 github.com >nul 2>&1
if !errorlevel! equ 0 (
    echo %GREEN%[OK] Can reach GitHub%RESET%
) else (
    echo %YELLOW%[WARN] Cannot reach GitHub - check network connection%RESET%
    
    :: Try to ping with different parameters
    ping -n 1 -w 5000 8.8.8.8 >nul 2>&1
    if !errorlevel! equ 0 (
        echo %YELLOW%[INFO] Internet connection available but GitHub may be blocked%RESET%
    ) else (
        echo %RED%[WARN] No internet connection detected%RESET%
    )
)

:: Check if running behind corporate firewall
nslookup github.com >nul 2>&1
if !errorlevel! neq 0 (
    echo %YELLOW%[WARN] DNS resolution issues detected%RESET%
)
goto :eof

:check_result
set "operation_result=%ERROR_LEVEL%"
echo.
echo ================================================

if %operation_result% equ 0 (
    echo %GREEN%[SUCCESS] Operation completed successfully!%RESET%
    echo.
    
    :: Show latest log location
    if exist "update_vcp_logs\" (
        for /f "delims=" %%i in ('dir /b /o-d "%SCRIPT_DIR%update_vcp_logs\update_vcp_*.log" 2^>nul') do (
            echo %CYAN%Latest log: update_vcp_logs\%%i%RESET%
            goto show_success_stats
        )
    )
    
    :show_success_stats
    :: Show update statistics if available
    if exist "update_vcp_rollback_info.json" (
        echo %CYAN%Update Statistics:%RESET%
        %PYTHON_CMD% -c "import json; data=json.load(open('update_vcp_rollback_info.json')); stats=data.get('update_stats',{}); [print(f'  {k}: {v}') for k,v in stats.items() if v>0]" 2>nul || (
            echo %YELLOW%  [Statistics unavailable]%RESET%
        )
    )
) else (
    echo %RED%[FAILED] Operation failed - check logs for details%RESET%
    echo.
    
    :: Show error log location
    if exist "update_vcp_logs\" (
        for /f "delims=" %%i in ('dir /b /o-d "%SCRIPT_DIR%update_vcp_logs\update_vcp_*.log" 2^>nul') do (
            echo %YELLOW%Error log: update_vcp_logs\%%i%RESET%
            goto show_troubleshooting
        )
    )
    
    :show_troubleshooting
    echo.
    echo %CYAN%Common troubleshooting steps:%RESET%
    echo 1. Git connection failed: Check network or configure proxy
    echo 2. Docker startup failed: Ensure Docker Desktop is running
    echo 3. Permission errors: Run as administrator
    echo 4. Path errors: Ensure script runs from VCPUpdate directory
    echo 5. Configuration issues: Check update_vcp_config.ini
    echo 6. Python issues: Verify Python 3.7+ installation
    echo.
    echo %CYAN%TIP: Use debug mode (Option D) for detailed error information%RESET%
)

echo ================================================
echo.

:: Check if operation was interrupted
if %operation_result% equ 130 (
    echo %YELLOW%[INFO] Operation was interrupted by user%RESET%
) else if %operation_result% gtr 1 (
    echo %RED%[ERROR] Unexpected error code: %operation_result%%RESET%
)

pause
goto menu

:cleanup_on_interrupt
echo.
echo %YELLOW%[WARNING] Script interrupted by user%RESET%
echo Performing cleanup...
:: Add any necessary cleanup here
echo Cleanup completed
pause
exit /b 130

:validate_environment
:: Validate that we're in the correct directory
if not exist "update_vcp.py" (
    echo %RED%[CRITICAL] Script not running from VCPUpdate directory%RESET%
    echo Expected to find update_vcp.py in current directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

:: Check Windows version compatibility
ver | findstr /i "Windows" >nul 2>&1
if !errorlevel! neq 0 (
    echo %YELLOW%[WARNING] Not running on Windows - script may not work correctly%RESET%
)

:: Check if running with administrator privileges (optional info)
net session >nul 2>&1
if !errorlevel! equ 0 (
    echo %CYAN%[INFO] Running with administrator privileges%RESET%
) else (
    echo %CYAN%[INFO] Running with standard user privileges%RESET%
)
goto :eof

:display_system_info
echo %CYAN%System Information:%RESET%
echo Computer: %COMPUTERNAME%
echo User: %USERNAME%
echo Windows Version: 
ver
echo Architecture: %PROCESSOR_ARCHITECTURE%
echo.
goto :eof

:exit
cls
echo.
echo %GREEN%Thank you for using VCP Auto Update Tool v1.0!%RESET%
echo.
echo %CYAN%Project Information:%RESET%
echo - VCPChat: https://github.com/lioensky/VCPChat
echo - VCPToolBox: https://github.com/lioensky/VCPToolBox
echo.
echo %CYAN%Support:%RESET%
echo For issues or suggestions, please provide feedback on GitHub.
echo.
echo %CYAN%Documentation:%RESET%
echo Check the README.md files in each project for detailed usage instructions.
echo.
echo %YELLOW%Script will exit in 5 seconds...%RESET%
timeout /t 5 >nul
exit /b 0

:: ============ ERROR HANDLING ============

:handle_critical_error
echo.
echo %RED%[CRITICAL ERROR] %~1%RESET%
echo.
echo The script cannot continue due to a critical error.
echo Please check the following:
echo 1. Ensure you are running from the VCPUpdate directory
echo 2. Verify Python 3.7+ is installed and in PATH
echo 3. Check that update_vcp.py exists in the current directory
echo 4. Run the environment test (Option T) for detailed diagnostics
echo.
pause
exit /b 1

:: Set up interrupt handling
if not defined SCRIPT_INTERRUPT_HANDLER (
    set SCRIPT_INTERRUPT_HANDLER=1
    :: This would ideally set up Ctrl+C handling, but batch is limited
    :: The Python script handles most interruption scenarios
)

:: Validate environment before starting
call :validate_environment
if !errorlevel! neq 0 goto handle_critical_error "Environment validation failed"

:: Optional: Display system info in debug mode
if "%1"=="--debug" (
    call :display_system_info
)

goto menu