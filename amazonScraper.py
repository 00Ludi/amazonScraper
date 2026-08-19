import os
import random
import playwright
from playwright.sync_api import sync_playwright
from dataBase import saveProduct

def startTheScraper(searchingWord):
    print(f"[INFO] Initializing Playwright for '{searchingWord}'...")
    
    is_ci = os.getenv("GITHUB_ACTIONS") == "true"
    
    with sync_playwright() as p:
        # 1. BROWSER SETUP
        browser = p.chromium.launch(headless=is_ci)
        
        # Setting up location (New York) to bypass regional blocks
        ID = browser.new_context(
            locale="en-US", 
            timezone_id="America/New_York",
            geolocation={"longitude": -74.0060, "latitude": 40.7128}, 
            permissions=["geolocation"]
        )
        
        page = ID.new_page()
        
        # 2. NAVIGATING TO AMAZON & CHANGING ZIP CODE
        print("[INFO] Navigating to Amazon.com...")
        page.goto("https://www.amazon.com")
        
        print("[INFO] Changing delivery location (Zip Code) to US (10001)...")
        try:
            page.click("#nav-global-location-popover-link", timeout=5000)
            page.wait_for_timeout(2000)
            page.fill("#GLUXZipUpdateInput", "10001", timeout=5000)
            page.click("#GLUXZipUpdate", timeout=5000)
            page.wait_for_timeout(2000) 
            page.reload()
            page.wait_for_timeout(2000)
        except Exception as e:
            print("\n[WARNING] Could not change Zip Code (Amazon UI changed or Captcha detected).")
            if not is_ci:
                print(">>> PLEASE MANUALLY SOLVE THE CAPTCHA OR SET ZIP TO 10001 IN THE BROWSER. <<<")
                input(">>> Press ENTER in this terminal when you are ready to continue... <<<")
            else:
                print("[WARNING] Running in Cloud/CI, skipping manual captcha override...")

        # 3. SEARCHING THE KEYWORD
        print(f"[INFO] Typing keyword '{searchingWord}' into search box...")
        page.fill("#twotabsearchtextbox", searchingWord)
        
        print("[INFO] Pressing Enter...")
        page.keyboard.press("Enter")

        # 4. PAGINATION & SCRAPING LOOP
        print("[INFO] Waiting for results to load...")
        currentPage = 1
        
        while True:
            print(f"\n[INFO] === SCANNING PAGE {currentPage} ===")
            
            # ANTI-BOT: Wait random amount of time between 4-8 seconds
            waitTime = random.randint(4000, 8000)
            page.wait_for_timeout(waitTime)
        
            products = page.locator('div[data-component-type="s-search-result"]')
            howMuchProduct = products.count()
            print(f"[INFO] Found {howMuchProduct} product cards on screen! Extracting data...\n")
            
            # 5. DATA EXTRACTION
            for i in range(howMuchProduct):
                oneProduct = products.nth(i)

                headerTag = oneProduct.locator('h2').first
                header = headerTag.inner_text() if headerTag.count() > 0 else "No Title"

                currentCountTag = oneProduct.locator('.a-price-whole').first
                currentTag = currentCountTag.inner_text() if currentCountTag.count() > 0 else "None"

                urlTag = oneProduct.locator('.a-link-normal').first
                halfURL = urlTag.get_attribute('href') if urlTag.count() > 0 else ""
                fullURL = f"https://www.amazon.com{halfURL}"

                picTag = oneProduct.locator('.s-image').first
                picURL = picTag.get_attribute('src') if picTag.count() > 0 else "No Image"

                # 6. DATA CLEANING & DATABASE INSERTION
                currentClear = currentTag.replace('$', '').replace(',', '').replace('\n', '').replace('.', '').strip()

                if currentClear.isdigit():
                    currentNumber = float(currentClear) 
                    
                    # Print to terminal
                    print(f"🔸 PRODUCT: {header[:50]}...")
                    print(f"   💸 Current Price: ${currentClear}")
                    print("-" * 70)
                    
                    # Save directly to SQLite Database!
                    saveProduct(header, currentNumber, fullURL, picURL)

            # 7. NEXT PAGE CHECK
            next_button = page.locator("a.s-pagination-next").first
            
            if next_button.count() > 0:
                print(f"[INFO] Page {currentPage} completed. Moving to the next page...")
                page.click("a.s-pagination-next")
                currentPage += 1
            else:
                print(f"[INFO] No more pages! Scanned a total of {currentPage} pages. Loop broken.")
                break 

        # 8. SHUTDOWN
        browser.close()
        print("[INFO] Browser closed successfully. Scraper Engine stopped.")

# ==== MAIN ====
if __name__ == "__main__":
    searchingWord = input("[QUESTION] What product do you want to search for? ")
    startTheScraper(searchingWord)
