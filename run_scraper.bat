@echo off
echo Starting the Scraper Script...
echo Make sure you have closed all Chrome windows connected to this profile first!

:: Activate the virtual environment if it exists, otherwise just use standard python
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

python scrape.py

echo.
pause
