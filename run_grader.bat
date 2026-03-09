@echo off
echo Starting the Gem Grader Script...
echo Make sure you have closed all Chrome windows connected to this profile first!
echo Make sure your PDFs are in the "pdf" folder!

:: Activate the virtual environment if it exists, otherwise just use standard python
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

python gem_grader.py

echo.
pause
