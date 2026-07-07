@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
::  ZERO RECON FRAMEWORK — WINDOWS LAUNCHER
::  (c) 2026 Zero Labs — Offensive Security Research
::  এক-ক্লিকে: Venv তৈরি → Pip Install → Framewok চালু
:: ============================================================

title Zero Recon Framework v1.0.0
color 0A

echo ============================================================
echo   ███████╗███████╗██████╗  ██████╗
echo   ╚══███╔╝██╔════╝██╔══██╗██╔═══██╗
echo     ███╔╝ █████╗  ██████╔╝██║   ██║
echo    ███╔╝  ██╔══╝  ██╔══██╗██║   ██║
echo   ███████╗███████╗██║  ██║╚██████╔╝
echo   ╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝
echo ============================================================
echo    ZERO RECON FRAMEWORK v1.0.0  (Windows-Native)
echo    (c) 2026 Zero Labs — Offensive Security Research
echo ============================================================
echo.

:: ১. Python চেক
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+ from python.org
    echo         Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo        ✅ Python found.

:: ২. Virtual Environment তৈরি
echo [2/4] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo        ✅ Virtual environment created.
) else (
    echo        ✅ Virtual environment already exists.
)

:: ৩. Pip আপডেট + ডিপেন্ডেন্সি ইনস্টল
echo [3/4] Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    echo         Please check requirements.txt and try again.
    pause
    exit /b 1
)
echo        ✅ All dependencies installed.

:: ৪. স্ক্রিপ্ট রান
echo [4/4] Starting Zero Recon Framework...
echo.
echo ============================================================
echo  🎯 MISSION START
echo ============================================================
echo.

:: যদি কোনো আর্গুমেন্ট না দেয়া হয়, তাহলে ইন্টারঅ্যাকটিভ মোড
if "%1"=="" (
    set /p target="Enter target domain (e.g., example.com): "
    python main.py !target!
) else (
    python main.py %*
)

:: ৫. শেষ হলে Venv থেকে বের হও
call deactivate
echo.
echo ============================================================
echo  🛑 Zero Recon Framework shutdown complete.
echo ============================================================
pause