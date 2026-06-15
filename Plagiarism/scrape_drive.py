
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration ---
TARGET_URL = "https://drive.google.com/drive/folders/1CVQlv_qBpnn3r2KOnF1hG8W0nbMGrt1DDF9jhX1n6MtlE8vWmkmb4wPHOvOXiwXRYHtdNr9j"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "tut4")
PROFILE_DIR = os.path.join(BASE_DIR, "chrome_profile")

# Hardcoded list of target students
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

def setup_driver(download_path):
    """Sets up the Chrome driver with persistent profile."""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    
    if not os.path.exists(PROFILE_DIR):
        os.makedirs(PROFILE_DIR)
    options.add_argument(f"user-data-dir={PROFILE_DIR}")
    
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_settings.popups": 0
    }
    options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def scroll_to_bottom(driver):
    """Scrolls the main container to load all files."""
    print("Scrolling to load all files...")
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        for _ in range(30): 
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.2)
    except:
        pass
    
    time.sleep(2)
    print("Finished scrolling.")

def main():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    print(f"Details:\n  URL: {TARGET_URL}\n  Download: {DOWNLOAD_DIR}\n  Profile: {PROFILE_DIR}")
    print(f"Targeting {len(TARGET_STUDENTS)} specific students.")

    try:
        driver = setup_driver(DOWNLOAD_DIR)
    except Exception as e:
        print(f"\n[ERROR] Failed to start Chrome: {e}")
        print("Make sure all other Chrome instances with this profile are closed.")
        return

    try:
        print(f"Navigating to {TARGET_URL}")
        driver.get(TARGET_URL)
        
        print("\n" + "="*60)
        print("ACTION REQUIRED: Log in to Google Drive if needed.")
        print("Wait for the page to fully load (List View recommended).")
        input("Press ENTER in this terminal when ready to start scraping...")
        print("="*60 + "\n")
        
        scroll_to_bottom(driver)
        
        print("Scanning files...")
        initial_rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
        total_rows = len(initial_rows)
        print(f"Found {total_rows} files (rows).")
        
        selected_count = 0
        processed_students = set()
        
        for index in range(total_rows):
            try:
                current_rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                if index >= len(current_rows):
                    break
                row = current_rows[index]

                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 3: continue
                
                try:
                    name_element = cols[2].find_element(By.XPATH, ".//div/div/div[2]/div/div/span[2]")
                    student_name = name_element.text.strip()
                except:
                    student_name = cols[2].text.strip()
                
                if not student_name: continue

                # Normalize for comparison
                clean_name = student_name.upper().strip()

                if clean_name in TARGET_STUDENTS:
                    # Check for duplicates
                    if clean_name in processed_students:
                        print(f"Skipping DUPLICATE for: {student_name}")
                        continue
                        
                    print(f"Selecting TARGET: {student_name}")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                    time.sleep(0.1)
                    ActionChains(driver).key_down(Keys.CONTROL).click(row).key_up(Keys.CONTROL).perform()
                    selected_count += 1
                    processed_students.add(clean_name)
                    time.sleep(0.1) 
                else:
                     # print(f"Skipping non-target: {student_name}")
                     pass

            except Exception as e:
                print(f"Error on row {index}: {e}")
        
        print(f"\nSelected {selected_count} files.")
        
        if selected_count > 0:
            print("Attempting to click Top Download button...")
            user_xpath = "/html/body/div[2]/div/div[5]/div[1]/div/div/div/div[2]/div/div[2]/div/div[2]/div/div[3]/div/div/div"
            try:
                download_btn = None
                try:
                    download_btn = driver.find_element(By.XPATH, user_xpath)
                except:
                    download_btn = driver.find_element(By.XPATH, "//div[@aria-label='Download']")
                
                if download_btn:
                    download_btn.click()
                    print("[SUCCESS] Clicked Download button. Files should be zipping/downloading.")
                else:
                    print("[ERROR] Could not find Global Download button.")
            except Exception as e:
                print(f"[ERROR] Click failed: {e}")
            
            print("Keeping browser open for 60 seconds to allow Zip/Download to start...")
            time.sleep(60)
        else:
            print("No matching files found to download.")

    except Exception as e:
        print(f"Global Error: {e}")
        
    finally:
        print("\nDone. Press Enter to close browser...")
        input()
        driver.quit()

if __name__ == "__main__":
    main()
