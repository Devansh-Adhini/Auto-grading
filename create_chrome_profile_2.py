import os
import time
import subprocess
import sys

def main():
    # Define the directory where the profile will be stored
    profile_dir = os.path.join(os.getcwd(), "chrome_profile_2")
    
    # Path to the actual Chrome browser executable on Windows
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        
    if not os.path.exists(chrome_path):
        print("Error: Could not find Google Chrome installation. Please make sure Chrome is installed.")
        sys.exit(1)
        
    print("==================================================")
    print(f"Creating/Opening Chrome profile 2 at: {profile_dir}")
    print("==================================================")
    print("1. A new REAL Chrome window will open (bypassing Google's bot detection).")
    print("2. Please log in to your Google account.")
    print("3. Once you are done logging in, simply CLOSE the browser window.")
    print("==================================================")
    
    command = [
        chrome_path,
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://accounts.google.com/"
    ]
    
    try:
        print("Launching browser... Waiting for you to finish logging in.")
        process = subprocess.Popen(command)
        process.wait()
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        
    print("\n✅ Browser closed. Your profile session has been saved successfully!")
    print(f"Directory: {profile_dir}")
    print("You can now use this same user-data-dir in your future automation scripts to bypass login.")

if __name__ == "__main__":
    main()
