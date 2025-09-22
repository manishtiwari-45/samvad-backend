@echo off
echo Starting SAMVAD Backend...
echo.
echo Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo.
echo Checking if uvicorn is installed...
python -c "import uvicorn; print('uvicorn is available')" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: uvicorn not found, attempting to install dependencies...
    echo Installing requirements...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install requirements
        pause
        exit /b 1
    )
)

echo.
echo Starting FastAPI server...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
