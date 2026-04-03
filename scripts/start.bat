@echo off
chcp 65001 >nul
REM TOSRC 一键启动脚本 (Windows)
REM 支持开发模式、生产模式、调试模式

setlocal enabledelayedexpansion

REM 项目根目录
set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

REM 默认配置
set HOST=0.0.0.0
set PORT=8080
set MODE=dev
set WORKERS=1
set RELOAD=0

REM 打印帮助信息
goto :parse_args

:print_help
echo TOSRC 启动脚本 (Windows)
echo.
echo 用法: .\scripts\start.bat [选项]
echo.
echo 选项:
echo   -h, --help          显示帮助信息
echo   -p, --port PORT     设置服务端口 (默认: 8080)
echo   -m, --mode MODE     启动模式: dev/prod/debug (默认: dev)
echo   -w, --workers NUM   工作进程数 (仅生产模式有效, 默认: 1)
echo   --reload            启用热重载 (开发模式)
echo.
echo 示例:
echo   .\scripts\start.bat                          开发模式启动
echo   .\scripts\start.bat -m prod -p 8000          生产模式启动
echo   .\scripts\start.bat -m debug                 调试模式启动
echo.
goto :eof

:parse_args
if "%~1"=="" goto :main
if "%~1"=="-h" goto :print_help
if "%~1"=="--help" goto :print_help
if "%~1"=="-p" set "PORT=%~2" & shift & shift & goto :parse_args
if "%~1"=="--port" set "PORT=%~2" & shift & shift & goto :parse_args
if "%~1"=="-m" set "MODE=%~2" & shift & shift & goto :parse_args
if "%~1"=="--mode" set "MODE=%~2" & shift & shift & goto :parse_args
if "%~1"=="-w" set "WORKERS=%~2" & shift & shift & goto :parse_args
if "%~1"=="--workers" set "WORKERS=%~2" & shift & shift & goto :parse_args
if "%~1"=="--reload" set "RELOAD=1" & shift & goto :parse_args

echo 未知参数: %~1
goto :print_help

:main
echo TOSRC 启动脚本 v1.0
echo.

REM 检查 Python
call :check_python
if errorlevel 1 goto :eof

REM 检查端口
call :check_port
if errorlevel 1 goto :eof

REM 设置虚拟环境
call :setup_venv
if errorlevel 1 goto :eof

REM 安装依赖
call :install_deps
if errorlevel 1 goto :eof

REM 设置环境变量
call :setup_env
if errorlevel 1 goto :eof

REM 预启动检查
call :pre_check
if errorlevel 1 goto :eof

REM 启动服务
call :start_service
goto :eof

:check_python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python
    exit /b 1
)
for /f "tokens=*" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo [OK] %PYTHON_VERSION%
exit /b 0

:check_port
netstat -an | findstr ":%PORT% " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [错误] 端口 %PORT% 已被占用
    echo 请使用 -p 参数指定其他端口
    exit /b 1
)
echo [OK] 端口 %PORT% 可用
exit /b 0

:setup_venv
if not exist ".venv" (
    echo [信息] 创建虚拟环境...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo [OK] 虚拟环境已激活
exit /b 0

:install_deps
echo [信息] 检查依赖...
if not exist ".requirements_installed" (
    echo [信息] 安装依赖...
    pip install --quiet -r requirements.txt
    type nul > .requirements_installed
    echo [OK] 依赖安装完成
) else (
    echo [OK] 依赖已是最新
)
exit /b 0

:setup_env
echo [信息] 配置环境变量...

REM 加载 .env 文件
if exist ".env" (
    for /f "tokens=*" %%a in (.env) do (
        set "line=%%a"
        if not "!line:~0,1!"=="#" (
            if not "!line!"=="" (
                set "!line!"
            )
        )
    )
    echo [OK] 已加载 .env 文件
)

REM 设置默认值
if "%ADMIN_API_KEY%"=="" set ADMIN_API_KEY=admin-llm-router-2026
if "%CORS_ORIGINS%"=="" set CORS_ORIGINS=http://localhost:3000,http://localhost:8080
if "%LOG_LEVEL%"=="" set LOG_LEVEL=INFO

echo [OK] 环境变量配置完成
echo   ADMIN_API_KEY: %ADMIN_API_KEY:~0,4%...%ADMIN_API_KEY:~-4%
echo   CORS_ORIGINS: %CORS_ORIGINS%
echo   LOG_LEVEL: %LOG_LEVEL%
exit /b 0

:pre_check
echo [信息] 执行预启动检查...

REM 创建必要的目录
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "config" mkdir config

REM 检查静态资源
if not exist "static" (
    if exist "TOSRC-Single\static" (
        echo [信息] 创建静态资源链接...
        mklink /j "static" "TOSRC-Single\static" >nul 2>&1
        if errorlevel 1 (
            xcopy /e /i /y "TOSRC-Single\static" "static" >nul
        )
    )
)

echo [OK] 预启动检查完成
exit /b 0

:start_service
echo.
echo =================================
echo     TOSRC 服务启动中...
echo =================================
echo.
echo   模式:    %MODE%
echo   主机:    %HOST%
echo   端口:    %PORT%
echo   工作进程: %WORKERS%
echo.
echo   管理后台: http://localhost:%PORT%/admin/
echo   API 文档: http://localhost:%PORT%/docs
echo.
echo =================================
echo.

if "%MODE%"=="dev" (
    if "%RELOAD%"=="1" (
        uvicorn main:app --host %HOST% --port %PORT% --reload --log-level debug
    ) else (
        uvicorn main:app --host %HOST% --port %PORT% --log-level info
    )
) else if "%MODE%"=="prod" (
    echo [信息] 以生产模式启动...
    uvicorn main:app --host %HOST% --port %PORT% --workers %WORKERS% --log-level warning --access-log --proxy-headers
) else if "%MODE%"=="debug" (
    echo [信息] 以调试模式启动...
    set LOG_LEVEL=DEBUG
    uvicorn main:app --host %HOST% --port %PORT% --reload --log-level debug --access-log
) else (
    echo [错误] 未知模式 '%MODE%'
    echo 可选模式: dev, prod, debug
    exit /b 1
)

goto :eof
