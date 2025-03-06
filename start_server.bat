@echo off
cd %~dp0
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment
    exit /b 1
)

echo Starting FastAPI server...
python -m src.api.main 2>&1
if errorlevel 1 (
    echo Failed to start the FastAPI server
    pause
    exit /b 1
)