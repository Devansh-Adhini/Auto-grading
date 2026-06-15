"""
KCEX Indicator Monitor (Windows Optimized)
Prints trading signals based on Long/Short ratios and sentiment.
"""

import time
import re
import requests
import sys
from datetime import datetime
try:
    from colorama import init, Fore, Style
except ImportError:
    import os
    os.system('pip install colorama')
    from colorama import init, Fore, Style

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Initialize colorama
init(autoreset=True)

# ================== CONFIG ==================
URL_KCEX_MAIN = "https://www.kcex.com/futures/exchange/PNUT_USDT?lang=en-US"
URL_KCEX_RATIO_API = "https://www.kcex.com/fapi/v1/contract/trading/overview/longShortRatio/PNUT_USDT"

FREQUENCY            = 0.5      # seconds
RATIO_FETCH_INTERVAL = 600
WINDOW_SIZE          = 10

HIGH_THRESHOLD = 60
LOW_THRESHOLD  = 40
# ============================================

def get_driver():
    """
    Sets up Chrome driver using webdriver-manager for Windows compatibility.
    Runs in headless mode to avoid popping up windows.
    """
    opts = webdriver.ChromeOptions()
    # opts.add_argument("--headless")  # Uncomment to run invisible
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--log-level=3") # Suppress logs
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        driver.set_page_load_timeout(60)
        return driver
    except Exception as e:
        print(f"{Fore.RED}Error initializing driver: {e}")
        sys.exit(1)

def parse_val(t):
    if t is None:
        return None
    if isinstance(t, (float, int)):
        return float(t)
    try:
        s = str(t).replace("%", "").replace("+", "").replace(",", "").strip()
        m = re.search(r"(\d+(\.\d+)?)", s)
        return float(m.group(1)) if m else None
    except:
        return None

def wait_for_main_page(driver, timeout=20):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(@class,'MarketProportion') or contains(@class,'market_wrapper') or contains(@class,'UpDownValue')]")
            )
        )
        time.sleep(1.0)
        return True
    except TimeoutException:
        return False

def scrape_price_and_sell(driver):
    price = None
    sell = None
    try:
        try:
            el = driver.find_element(By.XPATH, "//h3[contains(@class,'UpDownValue')]//span")
            price = parse_val(el.text.strip())
        except:
             # Try JS fallback first
            txt = driver.execute_script("let a=document.querySelector('h3[class*=UpDownValue]'); return a ? a.innerText.trim() : null;")
            price = parse_val(txt)
    except:
        price = None

    try:
        try:
            el = driver.find_element(By.XPATH, "//div[contains(@class,'MarketProportion_ask-text')]//span[contains(@class,'hasUnitDir')]")
            sell = parse_val(el.text.strip())
        except:
            spans = driver.find_elements(By.XPATH, "//span[contains(text(),'%')]")
            for s in spans:
                try:
                    parent = s.find_element(By.XPATH, "./parent::div")
                    txt = parent.text.strip()
                    if txt and txt.split("\\n")[0].strip().upper().startswith("S"):
                        sell = parse_val(s.text)
                        break
                except:
                    continue
    except:
        sell = None

    return price, sell

def fetch_ratio_via_api(timeout=8):
    try:
        resp = requests.get(URL_KCEX_RATIO_API, timeout=timeout)
        resp.raise_for_status()
        j = resp.json()
        short_side = j.get("data", {}).get("overview", {}).get("longPercent1h", {}).get("shortSide")
        if short_side is None:
            return None, None
        short_val = float(short_side)
        sentiment = "Bearish" if short_val >= 50.0 else "Bullish"
        return short_val, sentiment
    except Exception as e:
        print(f"{Fore.YELLOW}[RATIO/API] fetch failed: {e}")
        return None, None

def update_avg(window, value, max_len):
    window.append(value)
    if len(window) > max_len:
        window.pop(0)
    if not window: return 0.0
    return sum(window) / len(window)

def main():
    print(f"{Fore.CYAN}Starting KCEX Indicator Monitor...{Style.RESET_ALL}")
    
    driver = get_driver()
    print(f"{Fore.GREEN}Browser started. Navigating to {URL_KCEX_MAIN}...{Style.RESET_ALL}")

    try:
        driver.get(URL_KCEX_MAIN)
        if wait_for_main_page(driver):
             print(f"{Fore.GREEN}Page loaded! Monitoring...{Style.RESET_ALL}")
        else:
             print(f"{Fore.YELLOW}Warning: Page load check timed out, attempting to scrape anyway...{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Navigation failed: {e}{Style.RESET_ALL}")
        driver.quit()
        return

    sell_window = []
    current_sentiment = "Unknown"
    last_ratio_val = 0.0
    last_ratio_fetch = 0
    
    # Initial fetch
    val, sent = fetch_ratio_via_api()
    if sent:
        last_ratio_val = val
        current_sentiment = sent
        last_ratio_fetch = time.time()
    
    print(f"{Fore.CYAN}Starting loop...{Style.RESET_ALL}")
    try:
        while True:
            # 1. Update Sentiment periodically
            if time.time() - last_ratio_fetch >= RATIO_FETCH_INTERVAL:
                val, sent = fetch_ratio_via_api()
                if sent:
                    last_ratio_val = val
                    current_sentiment = sent
                    last_ratio_fetch = time.time()
            
            # 2. Scrape Data
            price, sell = scrape_price_and_sell(driver)
            
            ts = datetime.now().strftime("%H:%M:%S")
            
            if price is None or sell is None:
                print(f"[{ts}] {Fore.YELLOW}Scrape failed/incomplete (Price:{price}, Sell:{sell}), retrying...{Style.RESET_ALL}")
                time.sleep(FREQUENCY)
                continue
                
            avg_sell = update_avg(sell_window, sell, WINDOW_SIZE)
            
            # 3. Check Indicators
            signal = None
            if avg_sell >= HIGH_THRESHOLD and current_sentiment == "Bullish":
                signal = "LONG"
            elif avg_sell <= LOW_THRESHOLD and current_sentiment == "Bearish":
                signal = "SHORT"
            
            # 4. Output
            sent_color = Fore.GREEN if current_sentiment == "Bullish" else Fore.RED if current_sentiment == "Bearish" else Fore.WHITE
            
            if signal:
                sig_color = Fore.GREEN if signal == "LONG" else Fore.RED
                print(f"\n{sig_color}{Style.BRIGHT}" + "="*50)
                print(f"{sig_color}{Style.BRIGHT}   >>> {signal} SIGNAL DETECTED <<<")
                print(f"{sig_color}{Style.BRIGHT}   Price: {price} | Avg Sell: {avg_sell:.2f}")
                print(f"{sig_color}{Style.BRIGHT}   Sentiment: {current_sentiment}")
                print(f"{sig_color}{Style.BRIGHT}" + "="*50 + f"{Style.RESET_ALL}\n")
                time.sleep(1) 
            else:
                 status = (
                    f"{Style.DIM}[{ts}]{Style.RESET_ALL} "
                    f"Price: {Fore.CYAN}{price:<10}{Style.RESET_ALL} "
                    f"Sell%: {Fore.YELLOW}{sell:<6}{Style.RESET_ALL} "
                    f"Avg: {Fore.MAGENTA}{avg_sell:.2f}{Style.RESET_ALL} "
                    f"Sent: {sent_color}{current_sentiment} ({last_ratio_val}){Style.RESET_ALL}"
                )
                 print(status)

            time.sleep(FREQUENCY)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Stopping monitor...{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
    finally:
        driver.quit()
        print(f"{Fore.CYAN}Browser closed.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
