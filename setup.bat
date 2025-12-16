@echo off
echo ========================================
echo Smart Attendance System - Setup Script
echo ========================================
echo.

echo [1/5] Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
echo Virtual environment created successfully!
echo.

echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat
echo.

echo [3/5] Upgrading pip...
python -m pip install --upgrade pip
echo.

echo [4/5] Installing dependencies...
echo This may take several minutes...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Some packages failed to install
    echo If dlib failed, you may need to install CMake and Visual Studio Build Tools
    echo.
    echo You can try installing dlib separately:
    echo pip install cmake
    echo pip install dlib
    echo.
)
echo.

echo [5/5] Initializing database...
python database.py
if %errorlevel% neq 0 (
    echo ERROR: Failed to initialize database
    pause
    exit /b 1
)
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To start the application:
echo 1. Run: venv\Scripts\activate
echo 2. Run: python app.py
echo 3. Open browser to: http://localhost:5000
echo.
echo For detailed instructions, see README.md
echo.
pause
