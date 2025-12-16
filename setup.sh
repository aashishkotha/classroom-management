#!/bin/bash

echo "========================================"
echo "Smart Attendance System - Setup Script"
echo "========================================"
echo ""

echo "[1/5] Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment"
    exit 1
fi
echo "Virtual environment created successfully!"
echo ""

echo "[2/5] Activating virtual environment..."
source venv/bin/activate
echo ""

echo "[3/5] Upgrading pip..."
python -m pip install --upgrade pip
echo ""

echo "[4/5] Installing dependencies..."
echo "This may take several minutes..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo ""
    echo "WARNING: Some packages failed to install"
    echo "If dlib failed, you may need to install CMake"
    echo ""
    echo "On Ubuntu/Debian: sudo apt-get install cmake"
    echo "On macOS: brew install cmake"
    echo ""
fi
echo ""

echo "[5/5] Initializing database..."
python database.py
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to initialize database"
    exit 1
fi
echo ""

echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To start the application:"
echo "1. Run: source venv/bin/activate"
echo "2. Run: python app.py"
echo "3. Open browser to: http://localhost:5000"
echo ""
echo "For detailed instructions, see README.md"
echo ""
