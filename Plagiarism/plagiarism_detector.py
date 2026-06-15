import os
import glob
import time
import pandas as pd
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("WARNING: GOOGLE_API_KEY not found in environment variables.")
    print("Please create a .env file with your API key.")

try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    print(f"Error configuring Gemini API: {e}")

def pdf_to_images(pdf_path):
    """Converts PDF pages to a list of images using PyMuPDF."""
    images = []
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            pix = page.get_pixmap()
            # Convert to PIL Image for the API
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        return images
    except Exception as e:
        print(f"Error converting PDF {pdf_path}: {e}")
        return []

from google.api_core import exceptions

def extract_text_from_image(image, model_name='gemini-flash-latest'):
    """Uses Gemini API to extract text from an image (OCR) with retries."""
    retries = 0
    max_retries = 5
    base_wait = 2

    while retries < max_retries:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([
                "Transcribe this handwritten note exactly as it appears. Do not summarize.",
                image
            ])
            return response.text
        except exceptions.ResourceExhausted:
            wait_time = base_wait * (2 ** retries)
            print(f"Rate limit hit. Waiting {wait_time}s...")
            time.sleep(wait_time)
            retries += 1
        except Exception as e:
            print(f"Error extracting text from image: {e}")
            return ""
    
    print("Max retries exceeded for this page.")
    return ""

def process_pdfs(directory):
    """Iterates through PDFs, extracts text, and returns a DataFrame."""
    pdf_files = glob.glob(os.path.join(directory, "*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {directory}")
        return pd.DataFrame()

    data = []
    
    # Check for existing cache to save time/money
    cache_file = os.path.join(directory, "extracted_text_cache.csv")
    if os.path.exists(cache_file):
        print("Found cached text data. Loading...")
        return pd.read_csv(cache_file)

    print(f"Found {len(pdf_files)} PDFs. Starting extraction...")

    for pdf_file in pdf_files:
        filename = os.path.basename(pdf_file)
        
        # Skip if already in cache
        if cache_file and os.path.exists(cache_file):
            try:
                cached_df = pd.read_csv(cache_file)
                if filename in cached_df['filename'].values:
                    print(f"Skipping {filename} (already processed)...")
                    existing_row = cached_df[cached_df['filename'] == filename].iloc[0]
                    data.append(existing_row.to_dict())
                    continue
            except Exception as e:
                print(f"Error reading cache: {e}")

        print(f"Processing {filename}...")
        
        images = pdf_to_images(pdf_file)
        full_text = ""
        
        for i, img in enumerate(images):
            print(f"  - OCRing page {i+1}/{len(images)}...")
            page_text = extract_text_from_image(img)
            full_text += page_text + "\n"
            # Sleep proactively to avoid rate limits (Free tier ~15 RPM = 4s/req)
            time.sleep(5) 
            
        new_entry = {
            "filename": filename,
            "text": full_text
        }
        data.append(new_entry)
        
        # Incremental save
        current_df = pd.DataFrame(data)
        current_df.to_csv(cache_file, index=False)
        print(f"Progress saved to {cache_file}")
    
    df = pd.DataFrame(data)
    return df

def analyze_similarity(df):
    """Computes TF-IDF and Cosine Similarity matrix."""
    if df.empty or 'text' not in df.columns:
        print("DataFrame is empty or missing 'text' column.")
        return None, None

    # Replace NaN text with empty string
    documents = df['text'].fillna("")
    filenames = df['filename'].tolist()

    print("Computing TF-IDF vectors...")
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(documents)

    print("Computing Cosine Similarity...")
    similarity_matrix = cosine_similarity(tfidf_matrix)

    # Create a DataFrame for the matrix for better readability
    sim_df = pd.DataFrame(similarity_matrix, index=filenames, columns=filenames)
    
    return sim_df

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "lab1")
    
    if not os.path.exists(data_dir):
        print(f"Directory {data_dir} does not exist. Creating it...")
        os.makedirs(data_dir)
        print(f"Please put your PDF files in {data_dir}")
        return

    # 1. Extract Text
    df = process_pdfs(data_dir)
    
    if df.empty:
        print("No data extracted. Exiting.")
        return

    # 2. Analyze Similarity
    sim_df = analyze_similarity(df)
    
    if sim_df is not None:
        output_matrix_path = os.path.join(current_dir, "similarity_matrix.csv")
        sim_df.to_csv(output_matrix_path)
        print(f"\nSimilarity matrix saved to: {output_matrix_path}")
        print("\nTop 5 pairs by similarity (excluding self):")
        
        # Helper to find top pairs
        # Stack the matrix to get pairs, remove self-correlation (1.0), sort descending
        stacked = sim_df.stack()
        stacked = stacked[stacked.index.get_level_values(0) != stacked.index.get_level_values(1)]
        top_pairs = stacked.sort_values(ascending=False).head(10)
        
        # Deduplicate pairs (A-B is same as B-A)
        seen = set()
        for (f1, f2), score in top_pairs.items():
            pair = tuple(sorted((f1, f2)))
            if pair not in seen:
                print(f"{f1} <--> {f2}: {score:.4f}")
                seen.add(pair)

if __name__ == "__main__":
    main()
