import os
import glob
import sys
import io
import numpy as np
from PIL import Image
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Try to import EasyOCR, but handle failure gracefully
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("WARNING: EasyOCR not installed. OCR functionality disabled.")
except Exception as e:
    EASYOCR_AVAILABLE = False
    print(f"WARNING: EasyOCR failed to load ({e}). OCR functionality disabled.")

# Increase PIL partial image limit if needed
Image.MAX_IMAGE_PIXELS = None

def extract_text(pdf_path, reader, ocr_reader=None):
    """
    Extracts text from a PDF file. 
    First tries pypdf (fast). If valid text is found, returns it.
    If text is empty, falls back to easyocr (if available).
    """
    text = ""
    filename = os.path.basename(pdf_path)
    
    # 1. Try pypdf
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            extract = page.extract_text()
            if extract:
                text += extract + "\n"
    except Exception as e:
        print(f"Error reading {filename} with pypdf: {e}")

    # 2. Check if text is sufficient
    if text.strip():
        return text
    
    if not EASYOCR_AVAILABLE:
        print(f"  [Skipped] No text found in {filename} and OCR is unavailable.")
        return ""

    print(f"  [OCR Required] No text found in {filename} via pypdf. Switching to OCR...")
    
    # 3. Fallback to EasyOCR
    if ocr_reader is None:
        return "" # Should have been passed if available
    
    try:
        extracted_text = ""
        reader = PdfReader(pdf_path)
        
        # Limit to the first 3 pages and first 2 images per page for speed/stability
        MAX_PAGES = 3
        pages_to_process = reader.pages[:MAX_PAGES]

        for page_num, page in enumerate(pages_to_process):
            # Extracts images from the PDF page
            if 'images' not in dir(page): 
                continue # Safety check
                
            count = 0
            for image_file_object in page.images:
                if count >= 2: break # Limit images per page
                try:
                    # Convert raw bytes to PIL Image
                    image_data = image_file_object.data
                    image = Image.open(io.BytesIO(image_data))
                    
                    # Convert to RGB
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    # Convert to numpy array for EasyOCR
                    image_np = np.array(image)
                    
                    # Pass numpy array to EasyOCR
                    results = ocr_reader.readtext(image_np)
                    
                    # results is list of (bbox, text, prob)
                    page_text = " ".join([res[1] for res in results])
                    extracted_text += page_text + "\n"
                    count += 1
                except Exception as img_err:
                    # print(f"    [Warning] Failed to process image: {img_err}")
                    pass
            
        if extracted_text.strip():
            return extracted_text
        else:
            print(f"  [FAIL] OCR found no text in images for {filename}.")
            return ""

    except Exception as e:
        print(f"Error during OCR for {filename}: {e}")
        return ""

def main():
    # Configuration
    global EASYOCR_AVAILABLE

    pdf_folder = r"d:\MA102_TA\plagiarism\pdf"
    early_stopping_threshold = 0.95
    num_files_to_check = 10

    print(f"Searching for PDFs in: {pdf_folder}")
    
    # Get list of PDF files
    pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in the specified directory.")
        return

    # Take the first N files
    pdf_files = pdf_files[:num_files_to_check]
    print(f"Processing first {len(pdf_files)} files...")

    # Initialize OCR reader once
    ocr_reader = None
    if EASYOCR_AVAILABLE:
        print("Initializing OCR engine (EasyOCR)...")
        try:
            # Using try-except block specifically for instantiation
            # Python 3.14 + Numpy 2.x crash happens here often
            ocr_reader = easyocr.Reader(['en']) 
        except Exception as e:
            print(f"Failed to init EasyOCR (likely Numpy version mismatch): {e}")
            print("Proceeding without OCR.")
            # Global fallback
            EASYOCR_AVAILABLE = False 

    documents = []
    filenames = []
    empty_files = []

    # Extract text
    for pdf_file in pdf_files:
        filename = os.path.basename(pdf_file)
        print(f"\nProcessing: {filename}")
        
        text = extract_text(pdf_file, None, ocr_reader)
        
        if not text.strip():
            empty_files.append(filename)
            print(f"  -> Empty (skipped)")
        else:
            documents.append(text)
            filenames.append(filename)
            print(f"  -> Extracted {len(text)} chars")

    # Check if we have enough documents with text
    if len(documents) < 2:
        print("\nERROR: Not enough documents with extracted text to perform comparison.")
        if not EASYOCR_AVAILABLE:
            print("Reason: OCR is disabled/failed. The PDFs are likely scanned images.")
        return

    # Vectorization (TF-IDF)
    print(f"\nVectorizing {len(documents)} valid documents...")
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(documents)

    # Compute Cosine Similarity (Normalized Covariance)
    print("Computing similarity matrix...")
    similarity_matrix = cosine_similarity(tfidf_matrix)

    # Display Matrix
    print("\nSimilarity Matrix:")
    print(similarity_matrix)

    # Check for Plagiarism (High Similarity)
    print("\nChecking for high similarity pairs (Threshold > 0.8)...")
    
    found_high_similarity = False
    
    rows, cols = similarity_matrix.shape
    for i in range(rows):
        for j in range(i + 1, cols):
            score = similarity_matrix[i, j]
            file1 = filenames[i]
            file2 = filenames[j]
            
            if score > 0.8:
                print(f"MATCH FOUND: {file1} <--> {file2} : Score = {score:.4f}")
                found_high_similarity = True
                
                # Early Stopping
                if score > early_stopping_threshold:
                    print(f"\n!!! EARLY STOPPING TRIGGERED !!!")
                    print(f"Critical similarity detected between {file1} and {file2}.")
                    print("Stopping further analysis.")
                    return

    if not found_high_similarity:
        print("No high similarity pairs found.")

if __name__ == "__main__":
    main()
