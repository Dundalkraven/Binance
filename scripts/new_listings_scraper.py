from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from chromedriver_py import binary_path
import os
import json
import time

from store_order import *
from load_config import *
from send_notification import *

chrome_options = Options()
chrome_options.add_argument("--headless")  # Headless mode for background execution
driver = webdriver.Chrome(executable_path=binary_path, options=chrome_options)
driver.get("https://www.binance.com/en/support/announcement/c-48")

def get_last_coin():
    """
    Scrapes the Binance new listings page and returns the symbol and name if a new coin is detected.
    """
    try:
        # Find the latest announcements
        announcements = driver.find_elements(By.CLASS_NAME, 'css-1ej4hfo')  # Adjust the class as needed

        for announcement in announcements:
            text = announcement.text

            # Check if one of the markers "Binance Will Add" or "Futures" is present
            if "Binance Will Add" in text or "Futures" in text:
                # Look for symbols in parentheses, e.g., (ACX) or (ORCA)
                symbols = []
                start = text.find("Binance Will") + len("Binance Will")
                parts = text[start:].split("and")  # Split the text at "and" for multiple coins
                for part in parts:
                    if '(' in part and ')' in part:
                        symbol_start = part.index('(') + 1
                        symbol_end = part.index(')')
                        symbols.append(part[symbol_start:symbol_end].strip())
                return text, symbols

        return None, None
    except Exception as e:
        print(f"Error during scraping: {e}")
        return None, None

def store_new_listing(listing, symbols):
    """
    Stores a new listing if it doesn't already exist.
    """
    if os.path.isfile('new_listing.json'):
        file = load_order('new_listing.json')
        new_symbols = [symbol for symbol in symbols if symbol not in file]
        if not new_symbols:
            print("No new listings detected...")
            return file
        else:
            for symbol in new_symbols:
                file[symbol] = listing
            store_order('new_listing.json', file)
            send_notification(f"New listings detected: {', '.join(new_symbols)}")
            return file
    else:
        new_listing = {symbol: listing for symbol in symbols}
        store_order('new_listing.json', new_listing)
        send_notification(f"New listings detected: {', '.join(symbols)}")
        return new_listing

def search_and_update():
    """
    Main function to periodically check for new coin listings.
    """
    while True:
        latest_listing, latest_symbols = get_last_coin()
        if latest_symbols:
            store_new_listing(latest_listing, latest_symbols)
        else:
            print("No new coin listings found...")

        print("Checking for coin announcements every 2 hours.")
        time.sleep(60 * 120)  # Wait for 2 hours

if __name__ == "__main__":
    search_and_update()

