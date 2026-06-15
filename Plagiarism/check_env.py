import sys
import os

try:
    import pypdf
    print("pypdf available")
except ImportError:
    print("pypdf NOT available")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    print("scikit-learn available")
except ImportError:
    print("scikit-learn NOT available")

try:
    import numpy as np
    print("numpy available")
except ImportError:
    print("numpy NOT available")

try:
    import pytesseract
    print("pytesseract available")
except ImportError:
    print("pytesseract NOT available")

# Check if we can read a PDF
pdf_path = r"d:\MA102_TA\plagiarism\pdf\20252501001mathsassignment3 (1).pdf"
if os.path.exists(pdf_path):
    try:
        if 'pypdf' in sys.modules:
            reader = pypdf.PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            if text.strip():
                print(f"Extracted {len(text)} characters from PDF.")
            else:
                print("PDF opened but no text extracted (likely scanned image).")
    except Exception as e:
        print(f"Error reading PDF: {e}")
else:
    print("PDF not found for testing.")
