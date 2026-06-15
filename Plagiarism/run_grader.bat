@echo off
echo Installing minimal dependencies for batch grader...
venv\Scripts\python -m pip install -r requirements_grader.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies.
    pause
    exit /b %errorlevel%
)

echo Running batch grader...
venv\Scripts\python batch_grader.py
if %errorlevel% neq 0 (
    echo Error running script.
    pause
    exit /b %errorlevel%
)

echo Done.
pause
