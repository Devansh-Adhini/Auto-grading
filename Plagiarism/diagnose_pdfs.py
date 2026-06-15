import os
import glob
from pypdf import PdfReader

pdf_folder = r"d:\MA102_TA\plagiarism\pdf"
pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))[:10]

print(f"Checking first {len(pdf_files)} files for text content:")

for pdf_file in pdf_files:
    filename = os.path.basename(pdf_file)
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        if text.strip():
            print(f"[OK] {filename}: Found {len(text)} characters.")
        else:
            print(f"[FAIL] {filename}: No text extracted (likely image-based).")
    except Exception as e:
        print(f"[ERROR] {filename}: {e}")
