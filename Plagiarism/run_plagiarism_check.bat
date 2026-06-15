@echo off
echo Installing dependencies...
rem Removed strict numpy<2 requirement as it fails on Python 3.14. 
rem If EasyOCR fails, the script will skip it.
pip install pypdf scikit-learn numpy easyocr pillow

echo.
echo Running Plagiarism Checker...
python d:\MA102_TA\plagiarism\plagiarism_check.py

echo.
echo Done.
pause
