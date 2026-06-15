import os
import time
import glob
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import re

# Load environment variables
load_dotenv()

# Load multiple API keys
api_keys = []
key1 = os.getenv("GOOGLE_API_KEY1")
key2 = os.getenv("GOOGLE_API_KEY2")

if key1:
    api_keys.append(key1)
if key2:
    api_keys.append(key2)

# Fallback to single key if specific keys are not found
if not api_keys:
    single_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if single_key:
        api_keys.append(single_key)

if not api_keys:
    print("Error: No API keys found (GOOGLE_API_KEY1, GOOGLE_API_KEY2, GOOGLE_API_KEY, or GEMINI_API_KEY) in .env file.")
    exit(1)

print(f"Loaded {len(api_keys)} API key(s).")

# Configuration
PDF_FOLDER = 'tut4/re'
BATCH_SIZE = 10
# Using gemini-2.5-flash as requested (and verified available)
MODEL_NAME = 'models/gemini-2.5-flash' 
EXCEL_FILE = 'grades.xlsx'

TARGET_STUDENTS = {
    "AANCHAL GUPTA", "ABHINAV SRIVASTAVA", "AKSHAT JAIN", "ANSH PATEL", "APURVA ARYA", 
    "ARMAAN THAKUR", "ARYAN PANDEY", "ARYAN PANDIT", "BANOTH MAHAVIR", "BHUKYA JOSHNA", 
    "BHUMIKA GUPTA", "BODKE YOGESH", "BOTTE JEEVAN", "CHAVAN ATHARVA SUNIL", "DEVAM SHAH", 
    "DHAGE PARTH MAROTI", "HARSH GUPTA", "HARSHIT KUMAR SINHA", "HIMANSHU DAVE", 
    "HIMANSHU SINGH", "HITANSH DARJI", "JIGNESH", "KHUSHWANT KUMAR BASANWAL", 
    "KOLI SEANNA VIJAY", "KARUPATI SUJITH", "KUSHAGRA CHASTA", "KUSUM VERMA", 
    "MADHUR KARNWAL", "MADUGULA SUHAS", "MANVEET JAIN", "MARIPAKAYALA CHARITHA SRI", 
    "MOTA SUHAS PAUL", "NAVEEN JAAT", "NITIN SINGH PADIYAR", "PALAK VERMA", 
    "PAMU PRANAVTEJA", "P SIDDI VINAY", "PATEL DHYEY", "PIYUSH KANSARA", "PRADUM", 
    "PRANJAL VISHWAKARMA", "RIYA RAI", "SACHIN KUMAR", "SAMRIDHI TAPARIA", 
    "SARAGADAM DANUSHKAR", "SHARAD KUMAR", "SHAURYA AVINISH KUMAR", "SVRS UDHBHAV BULUSU", 
    "TANISHQ VERMA", "VANAKUNAVATH MAHESH", "VARUN CHAUHAN", "VUDIMUDI SRI RAM RAJU",
    "SAUMYA RAJESHKUMAR SHERA", "SHAMBHAVI AGRAWAL", "SHIVANG RAJ", "SHREE RAM YADAV",
    "SHUBHAM PAREEK", "SIDHEE VERMA", "SMRUTI VIJAY PAWAR", "SOLANKI ABHIRAJ KIRTIBHAI",
    "SYED AYAN ALI", "TANMOY SARKAR", "THINLES NORBU", "UDIT GOYAL",
    "UJJWALSING AMARSING DHAWLIYA", "UNDI NAVEEN PAUL", "V YOGENDRA",
    "VACHHANI AADITYA BHAVINBHAI", "VAGHELA RUSHIT RAJESHBHAI", "VALECHA JATIN HARESHKUMAR",
    "VEDANSH UPADHYAY", "VIR SHARMA", "VIVEK SUNIL DOKE"
}

PROMPT = r"""You are a lenient and precise teaching assistant. Your task is to grade the attached PDF assignments against the tutorial questions provided below.

Tutorial Questions:
1. Show that a subset of a countable set is also countable.
2. If A is an uncountable set and B is a countable set, must A \ B be uncountable?
3. Suppose that A is a countable set. Show that the set B is also countable if there is an
onto function f from A to B.
4. Show that the set of real numbers that are solutions of quadratic equations ax2 + bx +
c = 0, where a, b, and c are integers, is countable.
5. For each of these relations on the set {1, 2, 3, 4}, decide whether it is reflexive, whether
it is symmetric, whether it is antisymmetric, and whether it is transitive.
(a) {(2, 2), (2, 3), (2, 4), (3, 2), (3, 3), (3, 4)}
(b) {(1, 1), (1, 2), (2, 1), (2, 2), (3, 3), (4, 4)}
(c) {(2, 4), (4, 2)}
(d) {(1, 2), (2, 3), (3, 4)}
(e) {(1, 1), (2, 2), (3, 3), (4, 4)}
(f) {(1, 3), (1, 4), (2, 3), (2, 4), (3, 1), (3, 4)}
6. Determine whether the relation R on the set of all people is reflexive, symmetric,
antisymmetric, and/or transitive, where (a, b) ∈ R if and only if
(a) a is taller than b.
(b) a and b were born on the same day.
(c) a has the same first name as b.
(d) a and b have a common grandparent.
7. Find a bijective map f : [1, 2] → [3, 6], thereby proving that the cardinality of [1, 2]
and [3, 6] are the same.
8. Show that the set of all rational numbers is countable.
9. Determine whether each of the following sets is countable or uncountable.
(a) B = {(x, y) | x ∈ N, y ∈ Z \ {0}}.
(b) C = R \ Q.
(c) A = set of all complex numbers.
10. Find a bijective map f : P(N) → (0, 1), thereby proving the required result.
11. Prove that |R| = |(0, 1)| and |R| = |R2|.

Grading Instructions:
1. Grade ALL attached PDF files.
2. Score each assignment out of 10. You can give partial marks (e.g., 0.5).
3. try to be lenient as long as they get the jest of the question
4. Use definitions according to Kenneth Rosen.
5. Deduct marks for incorrect logic or proofs (max -0.5 if they tried their best).
6. PLAGIARISM CHECK: Briefly scan for exact word-for-word copying between the files in this batch. If found, report it.
7. Identify the student Name and Roll Number from the filename or the top of the PDF or most of the times it is given in the name of the pdf.
8. each question is 10/11. grade according to how much they have solved each question and is the answer correct.

Output Format (Strictly follow this for EACH student):

Student: [PDF name]
   Roll No: [Roll No Found in PDF or ocr]
   Name: [Name Found in PDF or ocr]
   Marks: [Score]/10
   Reason for deduction: [Brief summary of why marks were lost, or "None" if full marks]

Detailed Feedback:
   Questions where marks were deducted:
       Q[No] : [Reason for deduction in one line]
   Missing questions: [List missing questions]
   Plagiarism: [Report plagiarism if the all the questions are plagarised or the entire file is the same with different name or "None"]

---
IMPORTANT:
- The output MUST match the attached files.
- DO NOT generate fake students.
- Make sure to map each response to the pdf name you are refering to.
- Only grade the files provided in this prompt.
"""

def initialize_excel():
    """Initializes the Excel file with target students if it doesn't exist."""
    # We want consistent columns. If file exists, we check if columns match, else warn or recreated?
    # User said "make a excel file", implying we can start fresh or append. 
    # To be safe, if we changed schema, we might want to check.
    # For now, I'll just ensure the headers are there if creating new.
    if not os.path.exists(EXCEL_FILE):
        print(f"Creating new Excel file: {EXCEL_FILE}")
        # Schema: Student Name, Marks, Reason for Deduction, Roll No, PDF Filename, Timestamp
        df = pd.DataFrame(list(TARGET_STUDENTS), columns=["Student Name"])
        df["Marks"] = ""
        df["Reason for Deduction"] = ""
        df["Roll No"] = ""
        df["PDF Filename"] = ""
        df["Timestamp"] = ""
        df.to_excel(EXCEL_FILE, index=False)
    else:
        print(f"Using existing Excel file: {EXCEL_FILE}")
        # Verify columns exist, if not add them
        df = pd.read_excel(EXCEL_FILE)
        changed = False
        if "Marks" not in df.columns:
             # Logic to migrate 'Grade' to 'Marks' if exists
             if "Grade" in df.columns:
                 df.rename(columns={"Grade": "Marks"}, inplace=True)
             else:
                 df["Marks"] = ""
             changed = True
        if "Reason for Deduction" not in df.columns:
            df["Reason for Deduction"] = ""
            changed = True
        
        if changed:
            print("Updated Excel schema to include new columns.")
            df.to_excel(EXCEL_FILE, index=False)

def update_excel(grades_data):
    """Updates the Excel file with new grades."""
    try:
        df = pd.read_excel(EXCEL_FILE)
        
        # Ensure object type for ALL columns to allow strings and prevent float/NaN issues
        df = df.astype(object)
        
        # Create a mapping for faster lookup
        # Normalize names in Excel for comparison (upper case, strip)
        df['Normalized Name'] = df['Student Name'].astype(str).str.upper().str.strip()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for data in grades_data:
            student_name = data.get('Name', '').strip()
            if not student_name:
                continue

            normalized_input_name = student_name.upper()
            
            # Try to find the student in the target list
            # We look for exact match or if the name is contained (e.g. "Doe John" vs "John Doe" might be tricky,
            # but user provided specific list. We will try exact match first, then checks if parts of name match)
            
            match_index = -1
            
            # Exact match check
            exact_matches = df[df['Normalized Name'] == normalized_input_name].index
            if not exact_matches.empty:
                match_index = exact_matches[0]
            else:
                # Fuzzy match / Partial match inside target list?
                # User's list is specific. Let's try to match if the known target name is IN the response name or vice versa
                for idx, row in df.iterrows():
                    target_name = row['Normalized Name']
                    if target_name in normalized_input_name or normalized_input_name in target_name:
                        match_index = idx
                        break
            
            if match_index != -1:
                # Update existing student
                df.at[match_index, 'Marks'] = data.get('Marks', '')
                df.at[match_index, 'Reason for Deduction'] = data.get('Reason for Deduction', '')
                df.at[match_index, 'Roll No'] = data.get('Roll No', '')
                df.at[match_index, 'PDF Filename'] = data.get('PDF Name', '')
                df.at[match_index, 'Timestamp'] = timestamp
                print(f"Updated grade for {df.at[match_index, 'Student Name']}")
            else:
                # Student not in target list, append them?
                # User said "make an excel file with these names". 
                # I will append new students to ensure no data loss, but keep original structure.
                print(f"Student '{student_name}' not in target list. Adding to Excel.")
                new_row = {
                    "Student Name": student_name,
                    "Roll No": data.get('Roll No', ''),
                    "Marks": data.get('Marks', ''),
                    "Reason for Deduction": data.get('Reason for Deduction', ''),
                    "PDF Filename": data.get('PDF Name', ''),
                    "Timestamp": timestamp,
                    "Normalized Name": normalized_input_name
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Drop the temporary normalized column and save
        if 'Normalized Name' in df.columns:
            df = df.drop(columns=['Normalized Name'])
            
        df.to_excel(EXCEL_FILE, index=False)
        print("Excel file updated successfully.")

    except Exception as e:
        print(f"Error updating Excel file: {e}")

def parse_gemini_response(response_text):
    """Parses Gemini response to extract student details."""
    grades_data = []
    # Regex to capture Student blocks
    # Looking for pattern:
    # Student: [PDF name]
    #    Roll No: [Roll No]
    #    Name: [Name]
    #    Marks: [Score]/10
    #    Reason for deduction: [Reason]
    
    student_blocks = re.split(r"Student:\s+", response_text)
    
    for block in student_blocks:
        if not block.strip():
            continue
            
        data = {}
        
        # Extract PDF Name (first line of block usually, or after "Student: " which is split)
        lines = block.strip().split('\n')
        if not lines: continue
        
        # The split removed "Student: ", so the first part is the PDF name
        data['PDF Name'] = lines[0].strip()
        
        # Parse other fields
        for line in lines:
            line = line.strip()
            if line.startswith("Roll No:"):
                data['Roll No'] = line.replace("Roll No:", "").strip()
            elif line.startswith("Name:"):
                data['Name'] = line.replace("Name:", "").strip()
            elif line.startswith("Marks:") or line.startswith("Grade:"):
                # Handle both Marks and Grade just in case model hallucinates old prompt
                score_str = line.split(":", 1)[1].strip()
                # Extract just the score (e.g., "8.5/10" -> "8.5")
                match = re.search(r"([\d\.]+)", score_str)
                if match:
                    data['Marks'] = match.group(1)
                else:
                    data['Marks'] = score_str
            elif line.startswith("Reason for deduction:"):
                data['Reason for Deduction'] = line.split(":", 1)[1].strip()

        if 'Name' in data:
            grades_data.append(data)
            
    return grades_data

def process_pdfs():
    # Initialize Excel
    initialize_excel()

    # Get list of PDF files
    if not os.path.exists(PDF_FOLDER):
        print(f"Error: Folder '{PDF_FOLDER}' not found.")
        return

    pdf_files = sorted(glob.glob(os.path.join(PDF_FOLDER, '*.pdf')))
    
    if not pdf_files:
        print(f"No PDF files found in '{PDF_FOLDER}'.")
        return

    total_files = len(pdf_files)
    print(f"Found {total_files} PDF files to process.")

    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"grading_output_{timestamp}.txt"
    print(f"Output will be saved to: {output_filename}")

    # Process in batches
    for i in range(0, total_files, BATCH_SIZE):
        batch = pdf_files[i : i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (total_files + BATCH_SIZE - 1) // BATCH_SIZE
        
        # Switch API key
        current_key_index = (batch_num - 1) % len(api_keys)
        current_api_key = api_keys[current_key_index]
        genai.configure(api_key=current_api_key)
        print(f"Using API Key index: {current_key_index} (Key ending in ...{current_api_key[-4:] if len(current_api_key) > 4 else '****'})")

        print(f"\n{'='*50}")
        print(f"Processing Batch {batch_num}/{total_batches}")
        print(f"Files: {len(batch)}")
        print(f"{'='*50}")

        uploaded_files = []
        
        try:
            # Upload files
            for file_path in batch:
                filename = os.path.basename(file_path)
                print(f"Uploading: {filename}...")
                try:
                    uploaded_file = genai.upload_file(file_path, display_name=filename)
                    uploaded_files.append(uploaded_file)
                except Exception as e:
                    print(f"Failed to upload {file_path}: {e}")

            # Wait for processing
            print("Waiting for files to be processed...")
            active_files = []
            for uploaded_file in uploaded_files:
                current_file = uploaded_file
                while current_file.state.name == "PROCESSING":
                    print('.', end='', flush=True)
                    time.sleep(2)
                    current_file = genai.get_file(uploaded_file.name)
                
                if current_file.state.name != "ACTIVE":
                    print(f"\nFile {current_file.name} failed to process. State: {current_file.state.name}")
                else:
                    active_files.append(current_file)
            print() # Newline after dots

            if not active_files:
                print("No files were successfully uploaded and processed in this batch.")
                continue

            # Generate content
            print("Sending prompt to Gemini...")
            model = genai.GenerativeModel(MODEL_NAME)
            
            # Construct a specific prompt that lists the filenames to ensure the model addresses each one
            batch_filenames = [os.path.basename(f) for f in batch]
            files_instruction = "\n\nFiles to Grade in this Batch (You MUST provide a separate report for EACH file listed below using the EXACT filename):\n" + "\n".join([f"- {name}" for name in batch_filenames])
            
            final_prompt = PROMPT + files_instruction + "\n\nREMINDER: Output format MUST start with 'Student: [Filename]' for each file."

            # Construct the request parts: Prompt then Files
            request_content = [final_prompt] + active_files
            
            response = model.generate_content(request_content)
            
            print("\nResponse from Gemini:")
            print("-" * 30)
            print(response.text)
            print("-" * 30)

            # Save response to file
            with open(output_filename, "a", encoding="utf-8") as f:
                f.write(f"\n\n{'='*50}\n")
                f.write(f"Batch {batch_num}/{total_batches}\n")
                f.write(f"{'='*50}\n")
                f.write(response.text)

            # Parse and Update Excel
            print("Updating Excel file...")
            grades_data = parse_gemini_response(response.text)
            update_excel(grades_data)

        except Exception as e:
            print(f"An error occurred during batch processing: {e}")

        finally:
            # Cleanup uploaded files
            print("Cleaning up uploaded files...")
            for uploaded_file in uploaded_files:
                try:
                    uploaded_file.delete()
                except Exception as e:
                    print(f"Error deleting file {uploaded_file.name}: {e}")
            print("Cleanup complete.")

        # Wait if there are more batches
        if i + BATCH_SIZE < total_files:
            wait_time = 60 # 1 minute
            print(f"\nTaking a 1 minute break before the next batch...")
            # Simple countdown
            start_time = time.time()
            while time.time() - start_time < wait_time:
                remaining = int(wait_time - (time.time() - start_time))
                if remaining % 60 == 0 and remaining > 0:
                     print(f"{remaining // 60} minutes remaining...", end='\r')
                time.sleep(1)
            print("\nResuming...")

if __name__ == "__main__":
    process_pdfs()
