from amazonScraper import startTheScraper
from aiEngine import startTheAiEngine
import os

def startSystem():
    print("🚀 [SYSTEM BOOTING] Amazon Price Tracker & AI Newsletter Engine")
    print("=" * 60)
    
    is_ci = os.getenv("GITHUB_ACTIONS") == "true"
    
    if is_ci:
        searchingWord = "gaming laptop"
        print(f"[INFO] CI detected. Defaulting search to '{searchingWord}'")
    else:
        searchingWord = input("[QUESTION] What product do you want to search for? (e.g. gaming laptop): ")
    
    # Phase 1: Run the Scraper (Backend Data Extraction)
    print("\n--- PHASE 1: SCRAPING STARTED ---")
    startTheScraper(searchingWord)
    
    # Phase 2: Artificial Intelligence and Emailing (Data Analysis & Distribution)
    print("\n--- PHASE 2: AI ANALYSIS AND EMAILING STARTED ---")
    startTheAiEngine()
    
    print("\n✅ [SYSTEM COMPLETED] All tasks finished successfully. Shutting down.")

if __name__ == "__main__":
    startSystem()