import os
import sys
import subprocess

def main():
    profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile_scraper")

    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        print("Error: Could not find Google Chrome. Make sure Chrome is installed.")
        sys.exit(1)

    print("=" * 60)
    print(f"Creating/Opening SCRAPER Chrome profile at:\n  {profile_dir}")
    print("=" * 60)
    print("1. A new Chrome window will open.")
    print("2. Log in to the Google account that has access to the Drive folder.")
    print("3. Close the browser window when done.")
    print("=" * 60)

    command = [
        chrome_path,
        f"--user-data-dir={profile_dir}",
        "--profile-directory=Default",
        "--no-first-run",
        "--no-default-browser-check",
        "https://accounts.google.com/"
    ]

    try:
        process = subprocess.Popen(command)
        process.wait()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"Error: {e}")

    print("\n✅ Browser closed. Scraper profile saved!")
    print(f"Directory: {profile_dir}")

if __name__ == "__main__":
    main()
